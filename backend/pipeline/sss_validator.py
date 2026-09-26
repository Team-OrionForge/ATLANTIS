"""Side-Scan Sonar (SSS) image validation engine.

Examines visual, acoustic, and geometric characteristics of uploaded images to verify
whether an image is a valid dual-channel Side-Scan Sonar waterfall image prior to model inference.
"""

from dataclasses import dataclass
import logging
import cv2
import numpy as np

from pipeline.constants import SONAR_CONFIDENCE_THRESHOLD

logger = logging.getLogger("atlantis.sss_validator")


@dataclass
class SSSValidationResult:
    """Container for Side-Scan Sonar image validation result."""

    is_sonar: bool
    sonar_confidence: float
    message: str
    metrics: dict[str, float]


def validate_sss_image(
    image: np.ndarray, threshold: float = SONAR_CONFIDENCE_THRESHOLD
) -> SSSValidationResult:
    """Validate whether an uploaded image possesses visual & acoustic SSS characteristics.

    Evaluates:
        1. Color Palette & Channel Monochromicity (monochromatic/sepia acoustic palette vs multi-color RGB).
        2. Swath Symmetry & Nadir Gap Profile (central low-intensity water-column & symmetric sweeps).
        3. Acoustic Texture & Speckle Shadow/Specular Co-occurrence (Rayleigh/Gamma acoustic distribution).

    Args:
        image: 2D or 3D numpy image array.
        threshold: SSS confidence threshold (default 0.80).

    Returns:
        SSSValidationResult: Validation verdict, confidence score [0.0, 1.0], and diagnostic message.
    """
    if not isinstance(image, np.ndarray) or image.size == 0:
        return SSSValidationResult(
            is_sonar=False,
            sonar_confidence=0.0,
            message="Invalid or empty image file.",
            metrics={},
        )

    # 1. Color Palette Monochromicity & 1D Pseudocolor Heatmap Score
    if image.ndim == 3 and image.shape[2] in (3, 4):
        b, g, r = cv2.split(image[:, :, :3])
        hsv = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2HSV)
        val = hsv[:, :, 2]
        sat = hsv[:, :, 1]

        # Consider non-dark active pixels to analyze sonar pseudocolor map
        active_mask = val > 15
        if np.any(active_mask):
            hue_active = hsv[:, :, 0][active_mask]
            sat_active = sat[active_mask]
            hue_std = float(np.std(hue_active))
            sat_mean = float(np.mean(sat_active))
        else:
            hue_std = 0.0
            sat_mean = float(np.mean(sat))

        diff_rg = float(np.mean(np.abs(r.astype(float) - g.astype(float))))
        diff_gb = float(np.mean(np.abs(g.astype(float) - b.astype(float))))
        channel_diff = (diff_rg + diff_gb) / 2.0

        # Monochromatic / Grayscale or 1D Pseudocolor heatmap (copper, amber, gold, sepia, cyan)
        if channel_diff < 25.0 and hue_std < 35.0:
            color_score = 1.0
        elif channel_diff < 40.0 and hue_std < 50.0:
            color_score = 0.85
        else:
            # High color variation or channel divergence (e.g. natural multi-color RGB photos)
            color_score = max(0.0, 1.0 - max(hue_std / 70.0, channel_diff / 80.0))

        gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy() if image.ndim == 2 else image[:, :, 0].copy()
        color_score = 1.0
        channel_diff = 0.0
        hue_std = 0.0

    h, w = gray.shape[:2]
    if h < 20 or w < 20:
        return SSSValidationResult(
            is_sonar=False,
            sonar_confidence=0.0,
            message="Image dimensions too small to be a valid SSS waterfall swath.",
            metrics={},
        )

    # 2. Swath & Central Nadir Gap Score (ignoring top/bottom telemetry text headers/footers)
    h_start = int(h * 0.05)
    h_end = int(h * 0.95)
    crop_gray = gray[h_start:h_end, :] if h > 40 else gray

    col_means = np.mean(crop_gray, axis=0)
    center_region = col_means[int(w * 0.35) : int(w * 0.65)]
    left_region = col_means[: int(w * 0.35)]
    right_region = col_means[int(w * 0.65) :]

    min_center = float(np.min(center_region)) if len(center_region) > 0 else float(np.min(col_means))
    mean_left = float(np.mean(left_region)) if len(left_region) > 0 else 1.0
    mean_right = float(np.mean(right_region)) if len(right_region) > 0 else 1.0

    # Symmetric port/starboard ratio
    sym_ratio = min(mean_left, mean_right) / max(1.0, max(mean_left, mean_right))

    # Check for central low-intensity nadir valley
    has_nadir = min_center < (min(mean_left, mean_right) * 0.85) or min_center < 45.0

    if has_nadir:
        swath_score = 1.0
    elif sym_ratio > 0.50:
        swath_score = 0.85
    else:
        swath_score = max(0.4, sym_ratio)

    # 3. Acoustic Speckle Texture & Shadow/Specular Co-occurrence Score
    shadow_ratio = float(np.count_nonzero(gray < 35)) / float(gray.size)
    bright_ratio = float(np.count_nonzero(gray > 160)) / float(gray.size)
    laplacian_var = float(np.var(cv2.Laplacian(gray, cv2.CV_64F)))

    # Acoustic waterfall images have speckle noise, dark shadows, and bright returns
    if shadow_ratio > 0.002 and bright_ratio > 0.005 and laplacian_var > 15.0:
        texture_score = 1.0
    elif laplacian_var > 10.0:
        texture_score = 0.80
    else:
        texture_score = 0.40

    # Overall SSS Confidence Score calculation
    confidence = 0.40 * color_score + 0.35 * swath_score + 0.25 * texture_score
    confidence = float(np.clip(confidence, 0.0, 1.0))

    is_sonar = confidence >= threshold

    if is_sonar:
        msg = f"✓ Valid Side-Scan Sonar (SSS) Image (Confidence: {confidence * 100:.0f}%)"
    else:
        msg = (
            "✕ Invalid Image: Uploaded image does not appear to be a valid Side-Scan Sonar (SSS) image. "
            "Supported input: Side-Scan Sonar imagery."
        )

    metrics = {
        "color_score": round(color_score, 4),
        "swath_score": round(swath_score, 4),
        "texture_score": round(texture_score, 4),
        "channel_diff": round(channel_diff, 2),
        "hue_std": round(hue_std, 2),
        "sym_ratio": round(sym_ratio, 4),
    }

    return SSSValidationResult(
        is_sonar=is_sonar,
        sonar_confidence=round(confidence, 4),
        message=msg,
        metrics=metrics,
    )
