"""Acoustic image preprocessing engine for side-scan sonar (SSS) waterfall imagery.

Provides nadir water-column auto-detection, CLAHE contrast enhancement,
and bilateral filtering for noise reduction on dual-channel acoustic data.
"""

import logging
from dataclasses import dataclass
import cv2
import numpy as np

from api.exceptions import SonarPreprocessingError
from pipeline.constants import (
    BILATERAL_D,
    BILATERAL_SIGMA_COLOR,
    BILATERAL_SIGMA_SPACE,
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID,
)

logger = logging.getLogger("atlantis.sonar_cv")


@dataclass
class PreprocessResult:
    """Container for preprocessed sonar waterfall channel outputs."""

    raw_image: np.ndarray
    port_raw: np.ndarray
    starboard_raw: np.ndarray
    port_processed: np.ndarray
    starboard_processed: np.ndarray
    metadata: dict[str, int | float | bool]


def validate_sonar_image(image: np.ndarray) -> np.ndarray:
    """Validate sonar input image array and convert to single-channel uint8 grayscale.

    Args:
        image: Input image array.

    Returns:
        np.ndarray: 2D uint8 grayscale image.

    Raises:
        SonarPreprocessingError: If image shape or dtype is invalid or empty.
    """
    if not isinstance(image, np.ndarray) or image.size == 0:
        raise SonarPreprocessingError("Input sonar image must be a non-empty numpy array.")

    if image.ndim == 3:
        if image.shape[2] in (3, 4):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            raise SonarPreprocessingError(f"Unsupported 3D image channel depth: {image.shape[2]}")
    elif image.ndim == 2:
        gray = image.copy()
    else:
        raise SonarPreprocessingError(f"Unsupported image dimensions: {image.ndim}D.")

    if gray.dtype != np.uint8:
        if np.issubdtype(gray.dtype, np.floating):
            gray = np.clip(gray * 255.0 if gray.max() <= 1.0 else gray, 0, 255).astype(np.uint8)
        else:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

    return gray


def split_nadir(
    image: np.ndarray, nadir_threshold: int = 15
) -> tuple[np.ndarray, np.ndarray, dict[str, int | float | bool]]:
    """Auto-detect central low-intensity nadir water-column strip and split into channels.

    Calculates column-wise mean intensity profile across the central region of the image
    to locate the nadir gap where acoustic returns are minimal.

    Args:
        image: 2D uint8 grayscale image.
        nadir_threshold: Intensity threshold below which columns are marked as nadir.

    Returns:
        tuple[np.ndarray, np.ndarray, dict]: Port channel, Starboard channel, and nadir metadata.
    """
    height, width = image.shape
    if width < 4:
        raise SonarPreprocessingError("Image width too small to detect nadir water column.")

    col_means = np.mean(image, axis=0)
    center_start = int(width * 0.3)
    center_end = int(width * 0.7)
    central_profile = col_means[center_start:center_end]

    min_idx = center_start + int(np.argmin(central_profile))
    nadir_mask = col_means < max(float(nadir_threshold), float(col_means[min_idx]) * 1.5 + 5.0)

    # Search outward around min_idx for contiguous nadir bounds
    left_bound = min_idx
    while left_bound > center_start and nadir_mask[left_bound]:
        left_bound -= 1

    right_bound = min_idx
    while right_bound < center_end - 1 and nadir_mask[right_bound]:
        right_bound += 1

    nadir_width = right_bound - left_bound

    if nadir_width < 2:
        logger.warning(
            "Nadir strip auto-detection failed or too narrow. Falling back to 50/50 split."
        )
        mid = width // 2
        left_bound = mid
        right_bound = mid
        fallback = True
    else:
        fallback = False

    port_channel = image[:, :left_bound]
    starboard_channel = image[:, right_bound:]

    # Fallback safety if one channel is empty
    if port_channel.shape[1] == 0 or starboard_channel.shape[1] == 0:
        mid = width // 2
        port_channel = image[:, :mid]
        starboard_channel = image[:, mid:]
        left_bound = mid
        right_bound = mid
        fallback = True

    metadata: dict[str, int | float | bool] = {
        "nadir_start": left_bound,
        "nadir_end": right_bound,
        "nadir_width": right_bound - left_bound,
        "image_width": width,
        "image_height": height,
        "fallback_split": fallback,
    }

    return port_channel, starboard_channel, metadata


def apply_clahe(channel: np.ndarray) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) to acoustic channel.

    Args:
        channel: 2D uint8 channel image.

    Returns:
        np.ndarray: Enhanced 2D uint8 channel image.
    """
    if channel.size == 0:
        return channel
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    return clahe.apply(channel)


def denoise_bilateral(channel: np.ndarray) -> np.ndarray:
    """Apply bilateral filtering to smooth speckle noise while preserving acoustic shadow edges.

    Args:
        channel: 2D uint8 channel image.

    Returns:
        np.ndarray: Denoised 2D uint8 channel image.
    """
    if channel.size == 0:
        return channel
    return cv2.bilateralFilter(
        channel,
        d=BILATERAL_D,
        sigmaColor=BILATERAL_SIGMA_COLOR,
        sigmaSpace=BILATERAL_SIGMA_SPACE,
    )


def preprocess_waterfall(raw_image: np.ndarray) -> PreprocessResult:
    """Orchestrate waterfall splitting, CLAHE enhancement, and bilateral denoise.

    Args:
        raw_image: Input raw side-scan sonar image array.

    Returns:
        PreprocessResult: Object containing raw and enhanced port/starboard channels.

    Raises:
        SonarPreprocessingError: On invalid input or processing failure.
    """
    try:
        gray = validate_sonar_image(raw_image)
        port_raw, starboard_raw, metadata = split_nadir(gray)

        port_clahe = apply_clahe(port_raw)
        starboard_clahe = apply_clahe(starboard_raw)

        port_processed = denoise_bilateral(port_clahe)
        starboard_processed = denoise_bilateral(starboard_clahe)

        return PreprocessResult(
            raw_image=gray,
            port_raw=port_raw,
            starboard_raw=starboard_raw,
            port_processed=port_processed,
            starboard_processed=starboard_processed,
            metadata=metadata,
        )
    except Exception as exc:
        if isinstance(exc, SonarPreprocessingError):
            raise exc
        logger.error(f"Unexpected preprocessing failure: {exc}", exc_info=True)
        raise SonarPreprocessingError(f"Failed to preprocess sonar waterfall image: {exc}") from exc
