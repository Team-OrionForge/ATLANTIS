"""Central physical, processing, and algorithm constants for Project Atlantis.

Defines towfish altitude, range parameters, image processing thresholds,
model confidence settings, and Hazard Priority Index (HPI) weights.
"""

TOWFISH_ALTITUDE_H_M: float = 8.0  # Default towfish height above seabed (m)
SLANT_RANGE_MAX_M: float = 75.0  # Max slant range per channel (m)
SHADOW_INTENSITY_THRESHOLD: float = 35.0  # 8-bit gray intensity threshold for shadows
CLAHE_CLIP_LIMIT: float = 2.8
CLAHE_TILE_GRID: tuple[int, int] = (8, 8)
BILATERAL_D: int = 7
BILATERAL_SIGMA_COLOR: float = 50.0
BILATERAL_SIGMA_SPACE: float = 50.0
YOLO_CONF_THRESHOLD: float = 0.65
YOLO_IOU_THRESHOLD: float = 0.45
SONAR_CONFIDENCE_THRESHOLD: float = 0.50  # Configurable initial SSS image validation threshold
DEDUP_BUFFER_M: float = 15.0  # Simulated ST_DWithin spatial dedup buffer (m)
RANDOM_SEED: int = 42

# Hazard Priority Index (HPI) taxonomy score lookups (S_class)
S_CLASS_MAP: dict[str, float] = {
    "shipwreck": 1.0,
    "ghost_net": 0.9,
    "chemical_container": 0.85,
    "metal_debris": 0.7,
    "pipeline": 0.6,
    "marine_plastic": 0.4,
}

# Static ecological risk weights per class (S_eco)
S_ECO_MAP: dict[str, float] = {
    "chemical_container": 1.0,
    "ghost_net": 0.95,
    "marine_plastic": 0.8,
    "metal_debris": 0.5,
    "shipwreck": 0.4,
    "pipeline": 0.3,
}
