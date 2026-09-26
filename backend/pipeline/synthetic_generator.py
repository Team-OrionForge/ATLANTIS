"""Procedural synthetic side-scan sonar (SSS) waterfall image generator.

Generates dual-channel acoustic waterfall imagery containing background reverberation speckle noise,
central nadir water column, beam attenuation, and exact procedural target instances of all 6 target classes.
"""

from dataclasses import dataclass
import cv2
import numpy as np

from pipeline.constants import RANDOM_SEED


@dataclass
class GroundTruthTarget:
    """Ground truth synthetic target specification container."""

    class_name: str
    bbox: list[int]  # [x, y, w, h]
    polygon: list[list[int]]  # [[x, y], ...]
    shadow_rendered: bool
    channel: str  # "port" or "starboard"


def generate_synthetic_waterfall(
    width: int = 800, height: int = 600, seed: int = RANDOM_SEED
) -> tuple[np.ndarray, list[GroundTruthTarget]]:
    """Procedurally build dual-channel acoustic waterfall image with 6 target classes.

    Args:
        width: Image width in pixels (default 800).
        height: Image height in pixels (default 600).
        seed: Random seed for deterministic generation.

    Returns:
        tuple[np.ndarray, list[GroundTruthTarget]]: 2D uint8 waterfall image and ground-truth target list.
    """
    np.random.seed(seed)

    # 1. Base acoustic background reverberation speckle noise (Rayleigh/Gaussian noise model)
    background = np.random.gamma(shape=3.0, scale=25.0, size=(height, width)).astype(np.float32)
    background = np.clip(background, 30, 160)

    # Beam attenuation falloff (darker at outer edges)
    col_coords = np.linspace(-1.0, 1.0, width)
    attenuation = 1.0 - 0.35 * (col_coords**2)
    waterfall = background * attenuation

    # 2. Central Nadir water column strip (dark low-return zone)
    nadir_width = int(width * 0.10)
    nadir_center = width // 2
    nadir_start = nadir_center - nadir_width // 2
    nadir_end = nadir_center + nadir_width // 2

    # Draw low-intensity nadir column with slight boundary noise
    waterfall[:, nadir_start:nadir_end] = np.random.normal(8.0, 3.0, size=(height, nadir_width))

    # Bright seabed first-return line on nadir boundaries
    waterfall[:, nadir_start - 3 : nadir_start] = np.random.normal(190.0, 15.0, size=(height, 3))
    waterfall[:, nadir_end : nadir_end + 3] = np.random.normal(190.0, 15.0, size=(height, 3))

    waterfall = np.clip(waterfall, 0, 255).astype(np.uint8)

    gt_targets: list[GroundTruthTarget] = []

    # Helper function to draw bright target return and trailing acoustic shadow
    def embed_target(
        pts: np.ndarray,
        class_name: str,
        channel: str,
        intensity: int = 220,
        has_shadow: bool = True,
        shadow_len: int = 35,
    ) -> GroundTruthTarget:
        cv2.fillPoly(waterfall, [pts.astype(np.int32)], intensity)

        x, y, w, h = cv2.boundingRect(pts.astype(np.int32))

        if has_shadow:
            shadow_dir = -1 if channel == "port" else 1
            if shadow_dir == 1:
                sx_start = x + w
                sx_end = min(width - 1, sx_start + shadow_len)
                if sx_end > sx_start:
                    waterfall[y : y + h, sx_start:sx_end] = np.random.normal(10.0, 4.0, size=(h, sx_end - sx_start))
            else:
                sx_end = x
                sx_start = max(0, sx_end - shadow_len)
                if sx_end > sx_start:
                    waterfall[y : y + h, sx_start:sx_end] = np.random.normal(10.0, 4.0, size=(h, sx_end - sx_start))

        poly_list = pts.tolist()
        return GroundTruthTarget(
            class_name=class_name,
            bbox=[int(x), int(y), int(w), int(h)],
            polygon=poly_list,
            shadow_rendered=has_shadow,
            channel=channel,
        )

    # Target 1: ghost_net (Port channel, irregular polyline mesh blob)
    net_pts = np.array(
        [
            [120, 80],
            [150, 75],
            [175, 95],
            [160, 130],
            [125, 140],
            [105, 110],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(net_pts, "ghost_net", "port", intensity=175, shadow_len=20))

    # Target 2: metal_debris (Starboard channel, small bright rhombus, strong shadow)
    debris_pts = np.array(
        [
            [550, 120],
            [570, 110],
            [585, 130],
            [565, 140],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(debris_pts, "metal_debris", "starboard", intensity=245, shadow_len=40))

    # Target 3: chemical_container (Starboard channel, rounded regular box, ~1:1.5 aspect)
    container_pts = np.array(
        [
            [620, 240],
            [660, 240],
            [660, 268],
            [620, 268],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(container_pts, "chemical_container", "starboard", intensity=185, shadow_len=25))

    # Target 4: pipeline (Port channel, long thin continuous corridor)
    pipeline_pts = np.array(
        [
            [40, 320],
            [300, 320],
            [300, 332],
            [40, 332],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(pipeline_pts, "pipeline", "port", intensity=200, shadow_len=15))

    # Target 5: marine_plastic (Port channel, planar sheet, SHADOWLESS dual-branch test target)
    plastic_pts = np.array(
        [
            [180, 440],
            [225, 435],
            [235, 465],
            [190, 475],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(plastic_pts, "marine_plastic", "port", intensity=135, has_shadow=False))

    # Target 6: shipwreck (Starboard channel, large hull-shaped silhouette > 15 m span, longest shadow)
    shipwreck_pts = np.array(
        [
            [500, 450],
            [650, 440],
            [720, 470],
            [680, 520],
            [520, 510],
        ],
        dtype=np.int32,
    )
    gt_targets.append(embed_target(shipwreck_pts, "shipwreck", "starboard", intensity=220, shadow_len=60))

    # Smooth waterfall image with slight Gaussian blur for realistic sonar imagery texture
    waterfall_blurred = cv2.GaussianBlur(waterfall, (3, 3), 0.5)

    return waterfall_blurred, gt_targets
