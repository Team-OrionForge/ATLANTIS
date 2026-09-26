"""YOLOv8-Seg wrapper, heuristic multi-class target classifier, and inference service.

Provides primary heuristic rule-based feature classification, fallback classical contour detection,
and full pipeline orchestration connecting acoustic preprocessing, shadow verification, and geospatial tagging.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Optional
import cv2
import numpy as np

from api.exceptions import DetectionError
from pipeline.constants import (
    S_CLASS_MAP,
    SHADOW_INTENSITY_THRESHOLD,
    TOWFISH_ALTITUDE_H_M,
    YOLO_CONF_THRESHOLD,
    YOLO_IOU_THRESHOLD,
)
from pipeline.geospatial import compute_hpi, pixel_to_geodetic, slant_to_ground_range
from pipeline.shadow_verifier import (
    ShadowVerdict,
    analyze_micro_roughness,
    dual_branch_classification,
    estimate_elevation,
    measure_trailing_shadow,
)

logger = logging.getLogger("atlantis.detector")

# Heuristic decision tree thresholds
ASPECT_RATIO_PIPELINE_MIN = 8.0
BOUNDARY_IRREGULARITY_NET_MIN = 25.0
INTENSITY_METAL_MIN = 190.0
CONTAINER_ASPECT_MAX = 2.5
SHIPWRECK_AREA_M2_MIN = 200.0


@dataclass
class RawDetection:
    """Raw bounding box and polygon detection from model or contour extractor."""

    bbox: list[int]  # [x, y, w, h]
    polygon: list[list[int]]  # [[x, y], ...]
    model_confidence: float
    contour: np.ndarray
    predicted_class: Optional[str] = None


@dataclass
class PipelineDetection:
    """Fully processed marine target detection with physics and geospatial telemetry."""

    detection_id: str
    class_name: str
    confidence: float
    bbox: list[int]
    polygon: list[list[int]]
    shadow_verdict: str
    shadow_intensity: float
    estimated_elevation_m: float
    area_m2: float
    span_m: float
    hpi_score: float
    hpi_tier: str
    lat: float
    lon: float
    channel: str
    components: dict[str, float] = field(default_factory=dict)


def heuristic_classify(
    contour: np.ndarray,
    bbox: list[int],
    mean_intensity: float,
    std_intensity: float,
    shadow_verdict: ShadowVerdict,
    px_to_m_ratio: float = 0.1,
) -> tuple[str, float]:
    """Classify acoustic target signature using domain physics and geometric decision tree.

    Decision Tree:
        - aspect_ratio > 8.0 -> pipeline
        - area_m2 > 200.0 and largest bounding geometry -> shipwreck
        - mean_intensity > 190.0 and compact perimeter -> metal_debris
        - aspect_ratio in [1.0, 2.5] and high internal uniformity -> chemical_container
        - boundary_irregularity > 25.0 and mid-range intensity -> ghost_net
        - shadowless / BENTHIC_DRAPED signature and lower intensity -> marine_plastic
        - Fallback default -> lowest-confidence marine_plastic / metal_debris candidate.

    Args:
        contour: Object contour OpenCV point array.
        bbox: Bounding box [x, y, w, h].
        mean_intensity: Mean pixel intensity [0, 255] inside contour.
        std_intensity: Standard deviation of pixel intensity inside contour.
        shadow_verdict: Dual-branch shadow verification verdict.
        px_to_m_ratio: Spatial resolution ratio (m/px).

    Returns:
        tuple[str, float]: Predicted taxonomy class name and heuristic confidence score.
    """
    x, y, w, h = bbox
    w_m = max(0.1, w * px_to_m_ratio)
    h_m = max(0.1, h * px_to_m_ratio)

    aspect_ratio = max(w_m, h_m) / min(w_m, h_m)
    area_px = cv2.contourArea(contour) if contour is not None and len(contour) >= 3 else float(w * h)
    area_m2 = area_px * (px_to_m_ratio**2)
    perimeter = cv2.arcLength(contour, True) if contour is not None and len(contour) >= 3 else float(2 * (w + h))

    # Boundary irregularity compactness proxy (P^2 / A)
    boundary_irregularity = (perimeter**2) / max(1.0, area_px)

    # 1. Pipeline check (extreme length-to-width corridor)
    if aspect_ratio >= ASPECT_RATIO_PIPELINE_MIN:
        confidence = min(0.98, 0.75 + (aspect_ratio - 8.0) * 0.02)
        return "pipeline", float(confidence)

    # 2. Shipwreck check (macro-scale area > 200 m^2)
    if area_m2 >= SHIPWRECK_AREA_M2_MIN:
        confidence = min(0.99, 0.80 + (area_m2 - 200.0) / 1000.0)
        return "shipwreck", float(confidence)

    # 3. Metal debris check (extreme acoustic impedance -> very high brightness)
    if mean_intensity >= INTENSITY_METAL_MIN and boundary_irregularity <= BOUNDARY_IRREGULARITY_NET_MIN:
        confidence = min(0.95, 0.70 + (mean_intensity - 190.0) / 100.0)
        return "metal_debris", float(confidence)

    # 4. Chemical container check (modular rectangular/box geometry, aspect 1 to 2.5, uniform return)
    if 1.0 <= aspect_ratio <= CONTAINER_ASPECT_MAX and std_intensity < 35.0 and mean_intensity > 120.0:
        confidence = 0.85
        return "chemical_container", float(confidence)

    # 5. Ghost net check (non-rigid irregular twisted boundary)
    if boundary_irregularity >= BOUNDARY_IRREGULARITY_NET_MIN:
        confidence = min(0.92, 0.70 + (boundary_irregularity - 25.0) / 100.0)
        return "ghost_net", float(confidence)

    # 6. Marine plastic check (flat, planar sheet, shadowless or BENTHIC_DRAPED)
    if shadow_verdict == ShadowVerdict.BENTHIC_DRAPED or mean_intensity < 140.0:
        confidence = 0.78
        return "marine_plastic", float(confidence)

    # Fallback classification candidate
    return "metal_debris", 0.65


class SonarDetector:
    """YOLOv8-Seg model wrapper with classical contour extraction fallback."""

    def __init__(self, weights_path: str = "yolov8n-seg.pt"):
        """Initialize detector and attempt loading YOLO model weights.

        Args:
            weights_path: Path to YOLO segmentation model weights.
        """
        self.weights_path = weights_path
        self.model: Optional[Any] = None
        self.is_degraded_mode: bool = False
        self._load_model()

    def _load_model(self) -> None:
        """Attempt to load YOLO model; fall back to degraded mode on failure or if weights absent."""
        try:
            from pathlib import Path
            if not Path(self.weights_path).exists():
                logger.info(
                    f"Model weights file '{self.weights_path}' not found locally. "
                    "Operating in degraded heuristic fallback mode (zero external downloads required)."
                )
                self.model = None
                self.is_degraded_mode = True
                return

            from ultralytics import YOLO
            self.model = YOLO(self.weights_path)
            self.is_degraded_mode = False
            logger.info("Successfully loaded YOLOv8-Seg model.")
        except Exception as exc:
            logger.warning(
                f"Failed to load YOLO model from '{self.weights_path}': {exc}. "
                "Enabling classical contour heuristic fallback mode."
            )
            self.model = None
            self.is_degraded_mode = True

    def infer(self, channel: np.ndarray, conf_threshold: float = YOLO_CONF_THRESHOLD) -> list[RawDetection]:
        """Run object detection/segmentation inference on single channel.

        Args:
            channel: 2D uint8 acoustic channel image.
            conf_threshold: Confidence filtering threshold.

        Returns:
            list[RawDetection]: Extracted raw detection candidates.
        """
        if channel is None or channel.size == 0:
            return []

        if not self.is_degraded_mode and self.model is not None:
            try:
                results = self.model.predict(
                    source=channel,
                    conf=conf_threshold,
                    iou=YOLO_IOU_THRESHOLD,
                    verbose=False,
                )
                raw_dets = []
                for res in results:
                    if res.masks is not None and res.boxes is not None:
                        for mask_xy, box in zip(res.masks.xy, res.boxes):
                            poly = mask_xy.astype(int).tolist()
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            bbox = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                            conf = float(box.conf[0].cpu().numpy())
                            contour = np.array(poly, dtype=np.int32).reshape(-1, 1, 2)
                            cls_id = int(box.cls[0].cpu().numpy()) if box.cls is not None else None
                            cls_name = res.names.get(cls_id, None) if (cls_id is not None and hasattr(res, 'names')) else None
                            raw_dets.append(
                                RawDetection(
                                    bbox=bbox,
                                    polygon=poly,
                                    model_confidence=conf,
                                    contour=contour,
                                    predicted_class=cls_name,
                                )
                            )
                if raw_dets:
                    return raw_dets
            except Exception as exc:
                logger.error(f"YOLO inference error: {exc}. Falling back to contour extraction.")

        # Classical contour extraction fallback path
        return self._extract_contours_fallback(channel)

    def _extract_contours_fallback(self, channel: np.ndarray) -> list[RawDetection]:
        """Extract target candidates using Otsu thresholding and contour analysis.

        Args:
            channel: 2D uint8 acoustic channel image.

        Returns:
            list[RawDetection]: Extracted raw detection candidates.
        """
        raw_dets = []
        try:
            # Otsu thresholding for bright acoustic returns
            _, thresh = cv2.threshold(channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 30:  # Noise threshold
                    continue

                x, y, w, h = cv2.boundingRect(cnt)
                poly = cnt.reshape(-1, 2).tolist()
                raw_dets.append(
                    RawDetection(
                        bbox=[x, y, w, h],
                        polygon=poly,
                        model_confidence=0.70,
                        contour=cnt,
                    )
                )
        except Exception as exc:
            logger.error(f"Contour extraction fallback error: {exc}")

        return raw_dets

    def run_full_pipeline(
        self,
        channel: np.ndarray,
        channel_name: str,
        towfish_lat: float,
        towfish_lon: float,
        towfish_heading_deg: float,
        altitude_m: float = TOWFISH_ALTITUDE_H_M,
        px_to_m_ratio: float = 0.1,
        ray_vector: tuple[float, float] = (1.0, 0.0),
        conf_threshold: float = YOLO_CONF_THRESHOLD,
    ) -> list[PipelineDetection]:
        """Orchestrate detection -> shadow verification -> heuristic classification -> geotagging.

        Args:
            channel: 2D uint8 preprocessed acoustic channel.
            channel_name: 'port' or 'starboard'.
            towfish_lat: Towfish origin latitude.
            towfish_lon: Towfish origin longitude.
            towfish_heading_deg: Towfish heading angle in degrees.
            altitude_m: Towfish altitude above seabed in meters.
            px_to_m_ratio: Meter scale per pixel.
            ray_vector: Normalized acoustic propagation vector.
            conf_threshold: Model confidence threshold.

        Returns:
            list[PipelineDetection]: Fully populated pipeline target detections.

        Raises:
            DetectionError: On unrecoverable pipeline failure.
        """
        try:
            raw_dets = self.infer(channel, conf_threshold=conf_threshold)
            pipeline_dets: list[PipelineDetection] = []

            for idx, raw_det in enumerate(raw_dets):
                contour = raw_det.contour
                bbox = raw_det.bbox
                x, y, w, h = bbox

                # Compute regional intensity statistics
                mask = np.zeros(channel.shape[:2], dtype=np.uint8)
                if contour is not None and len(contour) >= 3:
                    cv2.drawContours(mask, [contour.astype(np.int32)], -1, 255, -1)
                else:
                    mask[y : y + h, x : x + w] = 255

                pts = channel[mask > 0]
                mean_intensity = float(np.mean(pts)) if pts.size > 0 else 128.0
                std_intensity = float(np.std(pts)) if pts.size > 0 else 20.0

                # 1. Physics shadow verification & micro-roughness
                shadow_intensity = measure_trailing_shadow(channel, contour, ray_vector)
                roughness_score = analyze_micro_roughness(channel, contour)
                shadow_verdict = dual_branch_classification(shadow_intensity, roughness_score)

                # Filter out pure Seabed noise if non-target
                if shadow_verdict == ShadowVerdict.DISCARDED_SEABED and raw_det.model_confidence < 0.70:
                    continue

                # 2. Multi-class taxonomy classification (YOLO neural network with heuristic fallback)
                if raw_det.predicted_class and raw_det.predicted_class in S_CLASS_MAP:
                    class_name = raw_det.predicted_class
                    final_conf = raw_det.model_confidence
                else:
                    class_name, class_conf = heuristic_classify(
                        contour=contour,
                        bbox=bbox,
                        mean_intensity=mean_intensity,
                        std_intensity=std_intensity,
                        shadow_verdict=shadow_verdict,
                        px_to_m_ratio=px_to_m_ratio,
                    )
                    final_conf = max(raw_det.model_confidence, class_conf)

                # 3. Target dimension and elevation estimates
                area_px = cv2.contourArea(contour) if contour is not None and len(contour) >= 3 else float(w * h)
                area_m2 = area_px * (px_to_m_ratio**2)
                span_m = max(w, h) * px_to_m_ratio

                # Measure shadow length px along ray vector
                shadow_length_px = max(5.0, (255.0 - shadow_intensity) * 0.1)
                slant_range_px = max(10.0, np.hypot(x + w / 2, y + h / 2))

                try:
                    elevation_m = estimate_elevation(
                        shadow_length_px=shadow_length_px,
                        slant_range_px=slant_range_px,
                        altitude_m=altitude_m,
                        px_to_m_ratio=px_to_m_ratio,
                    )
                except ValueError:
                    elevation_m = 0.5

                # 4. Geospatial coordinate calculation & HPI calculation
                slant_range_m = slant_range_px * px_to_m_ratio
                try:
                    ground_range_m = slant_to_ground_range(max(altitude_m + 0.1, slant_range_m), altitude_m)
                except ValueError:
                    ground_range_m = slant_range_m

                target_lat, target_lon = pixel_to_geodetic(
                    pixel_x=x if channel_name == "starboard" else -x,
                    pixel_y=y,
                    towfish_lat=towfish_lat,
                    towfish_lon=towfish_lon,
                    towfish_heading_deg=towfish_heading_deg,
                    px_to_m_ratio=px_to_m_ratio,
                    ground_range_m=ground_range_m,
                )

                hpi_res = compute_hpi(class_name, span_m, elevation_m)

                detection_id = f"det_{channel_name}_{idx}_{int(x)}_{int(y)}"
                pipeline_dets.append(
                    PipelineDetection(
                        detection_id=detection_id,
                        class_name=class_name,
                        confidence=round(final_conf, 4),
                        bbox=bbox,
                        polygon=raw_det.polygon,
                        shadow_verdict=shadow_verdict.value,
                        shadow_intensity=round(shadow_intensity, 2),
                        estimated_elevation_m=round(elevation_m, 2),
                        area_m2=round(area_m2, 2),
                        span_m=round(span_m, 2),
                        hpi_score=hpi_res.score,
                        hpi_tier=hpi_res.tier,
                        lat=round(target_lat, 6),
                        lon=round(target_lon, 6),
                        channel=channel_name,
                        components=hpi_res.components,
                    )
                )

            return pipeline_dets
        except Exception as exc:
            logger.error(f"Detector pipeline failed: {exc}", exc_info=True)
            raise DetectionError(f"Failed to execute target detection pipeline: {exc}") from exc


_DETECTOR_SINGLETON: Optional[SonarDetector] = None


def get_detector(weights_path: str = "yolov8n-seg.pt") -> SonarDetector:
    """Module-level singleton accessor for SonarDetector instance.

    Args:
        weights_path: Path to model weights file.

    Returns:
        SonarDetector: Shared detector instance.
    """
    global _DETECTOR_SINGLETON
    if _DETECTOR_SINGLETON is None:
        _DETECTOR_SINGLETON = SonarDetector(weights_path=weights_path)
    return _DETECTOR_SINGLETON
