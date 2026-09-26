"""Physics-based shadow verification and dual-branch target verification engine.

Measures trailing acoustic shadow intensity, estimates target physical elevation
above seabed using acoustic ray geometry, and performs dual-branch micro-roughness analysis.
"""

from enum import Enum
import cv2
import numpy as np

from pipeline.constants import SHADOW_INTENSITY_THRESHOLD


class ShadowVerdict(str, Enum):
    """Result of acoustic shadow verification dual-branch decision tree."""

    PROTRUSION_CONFIRMED = "PROTRUSION_CONFIRMED"
    BENTHIC_DRAPED = "BENTHIC_DRAPED"
    DISCARDED_SEABED = "DISCARDED_SEABED"


def measure_trailing_shadow(
    channel: np.ndarray, contour: np.ndarray, ray_vector: tuple[float, float] = (1.0, 0.0)
) -> float:
    """Measure mean 8-bit acoustic intensity in trailing sampling window behind contour.

    Walks a sampling window along ray_vector (propagation direction from nadir line)
    starting at the outer boundary of contour.

    Args:
        channel: 2D uint8 channel image.
        contour: Object boundary contour as OpenCV point array shape (N, 1, 2) or (N, 2).
        ray_vector: Normalized vector (dx, dy) pointing away from nadir line.

    Returns:
        float: Mean intensity [0, 255] in trailing window. Returns 255.0 if window out of bounds.
    """
    if contour is None or len(contour) == 0 or channel.size == 0:
        return 255.0

    pts = contour.reshape(-1, 2)
    dx, dy = ray_vector
    norm = np.hypot(dx, dy)
    if norm > 0:
        dx, dy = dx / norm, dy / norm
    else:
        dx, dy = 1.0, 0.0

    # Project contour points along ray vector to find far edge
    projections = pts[:, 0] * dx + pts[:, 1] * dy
    far_idx = np.argmax(projections)
    far_pt = pts[far_idx]

    # Sample window 5 to 30 pixels behind the far edge along ray vector
    sample_intensities = []
    h, w = channel.shape[:2]

    for step in range(5, 30, 2):
        sx = int(round(far_pt[0] + step * dx))
        sy = int(round(far_pt[1] + step * dy))

        if 0 <= sx < w and 0 <= sy < h:
            sample_intensities.append(float(channel[sy, sx]))

    if not sample_intensities:
        return 255.0

    return float(np.mean(sample_intensities))


def verify_physical_protrusion(shadow_intensity: float) -> bool:
    """Verify physical target protrusion based on acoustic shadow intensity.

    According to acoustic backscatter physics, objects protruding above the seabed
    block acoustic wave propagation, producing a low-intensity shadow region behind them.

    Args:
        shadow_intensity: Mean intensity in trailing window [0, 255].

    Returns:
        bool: True if shadow intensity is below SHADOW_INTENSITY_THRESHOLD.
    """
    return shadow_intensity < SHADOW_INTENSITY_THRESHOLD


def estimate_elevation(
    shadow_length_px: float, slant_range_px: float, altitude_m: float, px_to_m_ratio: float = 0.1
) -> float:
    """Calculate physical target elevation h above seabed using shadow length formula.

    Formula:
        h = (H * L_s) / R_s
    where:
        H   = Towfish altitude above seabed (m)
        L_s = Shadow length (m) = shadow_length_px * px_to_m_ratio
        R_s = Slant range to target (m) = slant_range_px * px_to_m_ratio

    Args:
        shadow_length_px: Length of acoustic shadow in pixels.
        slant_range_px: Slant range distance from towfish to target in pixels.
        altitude_m: Towfish altitude H in meters above seabed.
        px_to_m_ratio: Spatial resolution ratio (meters per pixel).

    Returns:
        float: Estimated height h above seabed in meters.

    Raises:
        ValueError: If slant range or altitude is zero or negative.
    """
    if slant_range_px <= 0:
        raise ValueError("Slant range distance must be positive to calculate elevation.")
    if altitude_m <= 0:
        raise ValueError("Towfish altitude must be positive to calculate elevation.")

    shadow_length_m = max(0.0, shadow_length_px * px_to_m_ratio)
    slant_range_m = slant_range_px * px_to_m_ratio

    if slant_range_m <= 0:
        raise ValueError("Slant range in meters must be greater than zero.")

    h = (altitude_m * shadow_length_m) / slant_range_m
    return float(h)


def analyze_micro_roughness(channel: np.ndarray, contour: np.ndarray) -> float:
    """Calculate local high-frequency texture energy (Laplacian variance) inside contour.

    Used as the dual-branch fallback signal to differentiate planar/benthic debris
    (e.g., marine plastic sheet or draped ghost net) from flat background seabed.

    Args:
        channel: 2D uint8 channel image.
        contour: Target boundary contour points array.

    Returns:
        float: Laplacian variance texture energy score.
    """
    if contour is None or len(contour) < 3 or channel.size == 0:
        return 0.0

    mask = np.zeros(channel.shape[:2], dtype=np.uint8)
    cv2.drawContours(mask, [contour.astype(np.int32)], -1, 255, -1)

    pts = contour.reshape(-1, 2)
    x, y, w, h = cv2.boundingRect(pts)

    sub_channel = channel[y : y + h, x : x + w]
    sub_mask = mask[y : y + h, x : x + w]

    if sub_channel.size == 0 or np.count_nonzero(sub_mask) < 4:
        return 0.0

    laplacian = cv2.Laplacian(sub_channel, cv2.CV_64F)
    masked_laplacian = laplacian[sub_mask > 0]

    if masked_laplacian.size == 0:
        return 0.0

    return float(np.var(masked_laplacian))


def dual_branch_classification(
    shadow_intensity: float, roughness_score: float, geological_roughness_floor: float = 15.0
) -> ShadowVerdict:
    """Dual-branch target classification logic combining shadow and texture energy.

    Decision Tree:
        1. If shadow_intensity < SHADOW_INTENSITY_THRESHOLD -> PROTRUSION_CONFIRMED
        2. Else if roughness_score > geological_roughness_floor -> BENTHIC_DRAPED (shadowless target candidate)
        3. Else -> DISCARDED_SEABED (flat rock/uninteresting seabed feature)

    Args:
        shadow_intensity: Mean intensity in trailing window [0, 255].
        roughness_score: Micro-roughness score (Laplacian variance).
        geological_roughness_floor: Minimum roughness threshold above natural seabed noise.

    Returns:
        ShadowVerdict: Verification verdict enum.
    """
    if verify_physical_protrusion(shadow_intensity):
        return ShadowVerdict.PROTRUSION_CONFIRMED
    elif roughness_score > geological_roughness_floor:
        return ShadowVerdict.BENTHIC_DRAPED
    else:
        return ShadowVerdict.DISCARDED_SEABED
