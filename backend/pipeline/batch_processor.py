"""Real dataset batch processing engine for Project Atlantis.

Scans local dataset directories, ingests optional metadata, runs sequential/bounded-thread pool
image analysis across 500+ sonar waterfall images, and generates aggregate reports.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import time
from typing import Callable, Optional
import cv2

from api.exceptions import BatchReportNotFoundError, DatasetIngestionError
from api.schemas import BatchImageResultSchema, BatchReportSchema, DetectionSchema
from pipeline.constants import TOWFISH_ALTITUDE_H_M, YOLO_CONF_THRESHOLD
from pipeline.detector import get_detector
from pipeline.geospatial import simulate_dwithin_dedup
from pipeline.sonar_cv import preprocess_waterfall

logger = logging.getLogger("atlantis.batch_processor")

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "data" / "batch_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TowfishMetadata:
    """Optional per-image towfish navigation metadata."""

    lat: float = 25.7617
    lon: float = -80.1918
    heading_deg: float = 45.0
    altitude_m: float = TOWFISH_ALTITUDE_H_M


def discover_dataset_images(
    dataset_dir: str,
    extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tif", ".tiff"),
) -> list[Path]:
    """Recursively discover supported sonar images in dataset directory.

    Args:
        dataset_dir: Directory path string.
        extensions: Tuple of supported file extension strings.

    Returns:
        list[Path]: Sorted list of unique file paths.

    Raises:
        DatasetIngestionError: If directory does not exist or contains no supported images.
    """
    path = Path(dataset_dir).resolve()
    if not path.exists() or not path.is_dir():
        raise DatasetIngestionError(f"Dataset directory '{dataset_dir}' does not exist or is not a directory.")

    image_files: list[Path] = []
    for ext in extensions:
        image_files.extend(path.rglob(f"*{ext}"))
        image_files.extend(path.rglob(f"*{ext.upper()}"))

    # Deduplicate and sort
    sorted_files = sorted(list(set(image_files)))
    if not sorted_files:
        raise DatasetIngestionError(f"No supported sonar image files found in dataset directory '{dataset_dir}'.")

    return sorted_files


def load_optional_metadata(dataset_dir: str) -> dict[str, TowfishMetadata]:
    """Load optional metadata.json or metadata.csv from dataset directory if present.

    Args:
        dataset_dir: Dataset directory path string.

    Returns:
        dict[str, TowfishMetadata]: Map from filename string to TowfishMetadata instance.
    """
    path = Path(dataset_dir).resolve()
    meta_json = path / "metadata.json"
    meta_csv = path / "metadata.csv"

    res_map: dict[str, TowfishMetadata] = {}

    if meta_json.exists():
        try:
            with open(meta_json, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                for fname, m in raw_data.items():
                    res_map[fname] = TowfishMetadata(
                        lat=float(m.get("lat", 25.7617)),
                        lon=float(m.get("lon", -80.1918)),
                        heading_deg=float(m.get("heading_deg", 45.0)),
                        altitude_m=float(m.get("altitude_m", TOWFISH_ALTITUDE_H_M)),
                    )
            return res_map
        except Exception as exc:
            logger.warning(f"Failed to parse metadata.json in '{dataset_dir}': {exc}")

    return res_map


def process_single_image(
    img_path: Path,
    metadata: Optional[TowfishMetadata] = None,
    conf_threshold: float = YOLO_CONF_THRESHOLD,
    iou_threshold: float = 0.45,
) -> BatchImageResultSchema:
    """Process single sonar image through full Atlantis analysis pipeline.

    Wrapped in robust try/except so one corrupt image never aborts the entire batch run.

    Args:
        img_path: Path to sonar image file.
        metadata: Optional towfish navigation metadata.
        conf_threshold: Detection confidence threshold.
        iou_threshold: NMS IoU threshold.

    Returns:
        BatchImageResultSchema: Individual image processing result.
    """
    filename = img_path.name
    is_estimated_geo = metadata is None
    nav = metadata if metadata is not None else TowfishMetadata()

    try:
        raw_img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        if raw_img is None:
            return BatchImageResultSchema(
                filename=filename,
                status="failed",
                detection_count=0,
                geolocation_estimated=is_estimated_geo,
                detections=[],
                error=f"Unreadable image file '{filename}'.",
            )

        # 1. Acoustic Preprocessing
        prep_res = preprocess_waterfall(raw_img)
        detector = get_detector()

        # 2. Port & Starboard Detection
        port_dets = detector.run_full_pipeline(
            channel=prep_res.port_processed,
            channel_name="port",
            towfish_lat=nav.lat,
            towfish_lon=nav.lon,
            towfish_heading_deg=nav.heading_deg,
            altitude_m=nav.altitude_m,
            ray_vector=(-1.0, 0.0),
            conf_threshold=conf_threshold,
        )

        starboard_dets = detector.run_full_pipeline(
            channel=prep_res.starboard_processed,
            channel_name="starboard",
            towfish_lat=nav.lat,
            towfish_lon=nav.lon,
            towfish_heading_deg=nav.heading_deg,
            altitude_m=nav.altitude_m,
            ray_vector=(1.0, 0.0),
            conf_threshold=conf_threshold,
        )

        all_pipeline_dets = port_dets + starboard_dets
        det_dicts = [
            {
                "detection_id": f"{filename}_{d.detection_id}",
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "polygon": d.polygon,
                "shadow_verdict": d.shadow_verdict,
                "shadow_intensity": d.shadow_intensity,
                "estimated_elevation_m": d.estimated_elevation_m,
                "area_m2": d.area_m2,
                "span_m": d.span_m,
                "hpi_score": d.hpi_score,
                "hpi_tier": d.hpi_tier,
                "lat": d.lat,
                "lon": d.lon,
                "channel": d.channel,
                "components": d.components,
            }
            for d in all_pipeline_dets
        ]

        deduped = simulate_dwithin_dedup(det_dicts)
        final_schemas = [DetectionSchema(**d) for d in deduped]

        return BatchImageResultSchema(
            filename=filename,
            status="done",
            detection_count=len(final_schemas),
            geolocation_estimated=is_estimated_geo,
            detections=final_schemas,
            error=None,
        )
    except Exception as exc:
        logger.error(f"Error processing image '{filename}' in batch: {exc}")
        return BatchImageResultSchema(
            filename=filename,
            status="failed",
            detection_count=0,
            geolocation_estimated=is_estimated_geo,
            detections=[],
            error=str(exc),
        )


def run_batch(
    dataset_dir: str,
    batch_id: str,
    conf_threshold: float = YOLO_CONF_THRESHOLD,
    iou_threshold: float = 0.45,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    max_workers: int = 4,
) -> BatchReportSchema:
    """Execute batch processing over entire dataset directory using bounded thread pool.

    Args:
        dataset_dir: Target dataset directory path string.
        batch_id: Unique batch identification string.
        conf_threshold: Model confidence threshold.
        iou_threshold: IoU threshold.
        progress_callback: Callback function invoked as progress_callback(completed, total).
        max_workers: Maximum parallel thread worker count.

    Returns:
        BatchReportSchema: Summary report payload for entire batch run.
    """
    start_time = time.time()
    image_paths = discover_dataset_images(dataset_dir)
    metadata_map = load_optional_metadata(dataset_dir)

    total_images = len(image_paths)
    per_image_results: list[BatchImageResultSchema] = []
    completed_count = 0

    # Bounded ThreadPoolExecutor to prevent memory exhaustion on 500+ large sonar images
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(
                process_single_image,
                p,
                metadata_map.get(p.name),
                conf_threshold,
                iou_threshold,
            ): p
            for p in image_paths
        }

        for future in as_completed(future_to_path):
            res = future.result()
            per_image_results.append(res)
            completed_count += 1
            if progress_callback:
                progress_callback(completed_count, total_images)

    # Sort results by filename for consistent ordering
    per_image_results.sort(key=lambda r: r.filename)

    succeeded = sum(1 for r in per_image_results if r.status == "done")
    failed = sum(1 for r in per_image_results if r.status == "failed")
    flagged_est = sum(1 for r in per_image_results if r.geolocation_estimated)

    # Aggregate detection stats
    class_counts: dict[str, int] = {
        "ghost_net": 0,
        "metal_debris": 0,
        "chemical_container": 0,
        "pipeline": 0,
        "marine_plastic": 0,
        "shipwreck": 0,
    }

    tier_counts: dict[str, int] = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MODERATE": 0,
        "LOW": 0,
    }

    for img_res in per_image_results:
        for det in img_res.detections:
            cls_name = det.class_name
            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

            tier = det.hpi_tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

    elapsed = time.time() - start_time

    report = BatchReportSchema(
        batch_id=batch_id,
        total_images=total_images,
        succeeded=succeeded,
        failed=failed,
        processing_time_s=round(elapsed, 2),
        detections_by_class=class_counts,
        hpi_tier_breakdown=tier_counts,
        flagged_estimated_geolocation_count=flagged_est,
        per_image_results=per_image_results,
    )

    # Persist report to JSON file
    report_file = REPORTS_DIR / f"{batch_id}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    return report


def load_batch_report(batch_id: str) -> BatchReportSchema:
    """Load persisted BatchReport from JSON file.

    Args:
        batch_id: Unique batch identification string.

    Returns:
        BatchReportSchema: Batch report schema object.

    Raises:
        BatchReportNotFoundError: If report file does not exist.
    """
    report_file = REPORTS_DIR / f"{batch_id}.json"
    if not report_file.exists():
        raise BatchReportNotFoundError(f"Batch report for batch ID '{batch_id}' not found.")

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return BatchReportSchema(**data)
