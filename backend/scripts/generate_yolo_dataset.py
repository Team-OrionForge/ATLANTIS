"""Synthetic Side-Scan Sonar (SSS) dataset generator for YOLOv8-Seg.

Procedurally synthesizes annotated acoustic waterfall images with realistic reverberation noise,
nadir gap water columns, beam attenuation, and target polygons for 6 ocean target classes.
Outputs YOLO segmentation dataset format (images/, labels/, and dataset.yaml).
"""

import math
import os
from pathlib import Path
import cv2
import numpy as np

CLASS_MAP = {
    "shipwreck": 0,
    "ghost_net": 1,
    "chemical_container": 2,
    "metal_debris": 3,
    "pipeline": 4,
    "marine_plastic": 5,
}

CLASS_NAMES = list(CLASS_MAP.keys())


def rotate_polygon(pts: np.ndarray, angle_deg: float, center: tuple[float, float]) -> np.ndarray:
    """Rotate 2D point array around center point."""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    cx, cy = center
    rotated = []
    for x, y in pts:
        tx, ty = x - cx, y - cy
        rx = tx * cos_a - ty * sin_a + cx
        ry = tx * sin_a + ty * cos_a + cy
        rotated.append([rx, ry])
    return np.array(rotated, dtype=np.float32)


def generate_target_shape(class_name: str, width: int, height: int, rng: np.random.Generator) -> tuple[np.ndarray, bool, int, int]:
    """Generate base polygon points, shadow flag, intensity, and shadow length for target class."""
    if class_name == "shipwreck":
        # Large hull shape
        w_t = rng.integers(90, 160)
        h_t = rng.integers(40, 75)
        base = np.array([
            [0, h_t * 0.3],
            [w_t * 0.4, 0],
            [w_t * 0.9, h_t * 0.2],
            [w_t, h_t * 0.6],
            [w_t * 0.7, h_t],
            [w_t * 0.2, h_t * 0.9],
        ], dtype=np.float32)
        intensity = int(rng.integers(200, 245))
        shadow_len = int(rng.integers(40, 75))
        has_shadow = True

    elif class_name == "ghost_net":
        # Irregular twisted mesh blob
        w_t = rng.integers(45, 80)
        h_t = rng.integers(35, 70)
        num_pts = rng.integers(6, 10)
        angles = np.sort(rng.uniform(0, 2 * math.pi, num_pts))
        radii = rng.uniform(min(w_t, h_t) * 0.3, max(w_t, h_t) * 0.5, num_pts)
        cx, cy = w_t / 2, h_t / 2
        base = np.column_stack([cx + radii * np.cos(angles), cy + radii * np.sin(angles)])
        intensity = int(rng.integers(160, 195))
        shadow_len = int(rng.integers(15, 30))
        has_shadow = True

    elif class_name == "chemical_container":
        # Box container (aspect ~1:1 to 1:2.5)
        w_t = rng.integers(35, 60)
        h_t = rng.integers(20, 35)
        base = np.array([[0, 0], [w_t, 0], [w_t, h_t], [0, h_t]], dtype=np.float32)
        intensity = int(rng.integers(180, 220))
        shadow_len = int(rng.integers(20, 35))
        has_shadow = True

    elif class_name == "metal_debris":
        # Small bright compact rhombus/square
        w_t = rng.integers(18, 32)
        h_t = rng.integers(18, 32)
        base = np.array([[w_t / 2, 0], [w_t, h_t / 2], [w_t / 2, h_t], [0, h_t / 2]], dtype=np.float32)
        intensity = int(rng.integers(220, 255))
        shadow_len = int(rng.integers(30, 50))
        has_shadow = True

    elif class_name == "pipeline":
        # Long narrow corridor (aspect ratio > 8.0)
        w_t = rng.integers(180, 320)
        h_t = rng.integers(10, 18)
        base = np.array([[0, 0], [w_t, 0], [w_t, h_t], [0, h_t]], dtype=np.float32)
        intensity = int(rng.integers(190, 230))
        shadow_len = int(rng.integers(12, 22))
        has_shadow = True

    else:  # marine_plastic
        # Flat planar sheet, shadowless or minimal shadow
        w_t = rng.integers(35, 65)
        h_t = rng.integers(25, 45)
        base = np.array([[0, 5], [w_t - 5, 0], [w_t, h_t - 5], [5, h_t]], dtype=np.float32)
        intensity = int(rng.integers(125, 160))
        shadow_len = 0
        has_shadow = False

    return base, has_shadow, intensity, shadow_len


def create_single_synthetic_image(
    width: int = 640, height: int = 640, rng: np.random.Generator = None
) -> tuple[np.ndarray, list[tuple[int, list[tuple[float, float]]]]]:
    """Build single synthetic sonar image with targets and return (image_bgr, label_records)."""
    if rng is None:
        rng = np.random.default_rng()

    # 1. Base acoustic background reverberation speckle noise
    bg_shape = rng.uniform(2.5, 3.5)
    bg_scale = rng.uniform(20.0, 30.0)
    background = rng.gamma(shape=bg_shape, scale=bg_scale, size=(height, width)).astype(np.float32)
    background = np.clip(background, 25, 165)

    # Beam attenuation falloff
    col_coords = np.linspace(-1.0, 1.0, width)
    attenuation = 1.0 - rng.uniform(0.25, 0.40) * (col_coords**2)
    waterfall = background * attenuation

    # 2. Central Nadir water column strip
    nadir_width = int(width * rng.uniform(0.08, 0.12))
    nadir_center = width // 2
    nadir_start = nadir_center - nadir_width // 2
    nadir_end = nadir_center + nadir_width // 2
    actual_nadir_w = nadir_end - nadir_start

    # Draw low-intensity nadir column
    waterfall[:, nadir_start:nadir_end] = rng.normal(8.0, 3.0, size=(height, actual_nadir_w))

    # Bright seabed first-return line on nadir boundaries
    waterfall[:, nadir_start - 3 : nadir_start] = rng.normal(195.0, 15.0, size=(height, 3))
    waterfall[:, nadir_end : nadir_end + 3] = rng.normal(195.0, 15.0, size=(height, 3))

    waterfall = np.clip(waterfall, 0, 255).astype(np.uint8)

    labels = []
    num_targets = rng.integers(1, 5)
    selected_classes = rng.choice(CLASS_NAMES, size=num_targets, replace=True)

    # Define port and starboard placement zones
    port_zone = (20, nadir_start - 40)
    starboard_zone = (nadir_end + 40, width - 40)

    for cls_name in selected_classes:
        class_id = CLASS_MAP[cls_name]
        base_poly, has_shadow, intensity, shadow_len = generate_target_shape(cls_name, width, height, rng)

        # Decide channel: port (0) or starboard (1)
        is_starboard = rng.choice([True, False])
        zone = starboard_zone if is_starboard else port_zone
        if zone[1] <= zone[0] + 30:
            continue

        pos_x = float(rng.uniform(zone[0], zone[1]))
        pos_y = float(rng.uniform(40, height - 100))

        # Random rotation angle
        angle = float(rng.uniform(-30, 30)) if cls_name == "pipeline" else float(rng.uniform(0, 360))

        # Shift to position and rotate
        shifted = base_poly + np.array([pos_x, pos_y], dtype=np.float32)
        cx = float(np.mean(shifted[:, 0]))
        cy = float(np.mean(shifted[:, 1]))
        rot_poly = rotate_polygon(shifted, angle, (cx, cy))

        # Clip polygon within image bounds
        rot_poly[:, 0] = np.clip(rot_poly[:, 0], 5, width - 5)
        rot_poly[:, 1] = np.clip(rot_poly[:, 1], 5, height - 5)

        # Draw target fill
        pts_int = rot_poly.astype(np.int32)
        cv2.fillPoly(waterfall, [pts_int], intensity)

        # Render acoustic shadow if applicable
        if has_shadow and shadow_len > 0:
            x, y, w, h = cv2.boundingRect(pts_int)
            shadow_dir = 1 if is_starboard else -1
            if shadow_dir == 1:
                sx_start = x + w
                sx_end = min(width - 1, sx_start + shadow_len)
                if sx_end > sx_start and y + h <= height:
                    waterfall[y : y + h, sx_start:sx_end] = rng.normal(10.0, 4.0, size=(h, sx_end - sx_start))
            else:
                sx_end = x
                sx_start = max(0, sx_end - shadow_len)
                if sx_end > sx_start and y + h <= height:
                    waterfall[y : y + h, sx_start:sx_end] = rng.normal(10.0, 4.0, size=(h, sx_end - sx_start))

        # Normalize polygon points for YOLO segmentation format [x1/W, y1/H, ...]
        norm_pts = [(float(px / width), float(py / height)) for px, py in rot_poly]
        labels.append((class_id, norm_pts))

    # Add Gaussian blur for realistic sonar imagery texture
    blurred = cv2.GaussianBlur(waterfall, (3, 3), 0.5)
    # Convert grayscale to BGR for standard YOLO image loading
    bgr_img = cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR)

    return bgr_img, labels


def generate_dataset(
    output_dir: str = "data/dataset",
    num_train: int = 250,
    num_val: int = 50,
    seed: int = 42,
):
    """Generate YOLOv8-Seg dataset structure with train and val splits."""
    out_path = Path(output_dir).resolve()
    images_train = out_path / "images" / "train"
    images_val = out_path / "images" / "val"
    labels_train = out_path / "labels" / "train"
    labels_val = out_path / "labels" / "val"

    for p in [images_train, images_val, labels_train, labels_val]:
        p.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    print(f"Generating synthetic YOLOv8-Seg dataset at {out_path}...")
    print(f"Train split: {num_train} samples, Val split: {num_val} samples.")

    # Generate Train Split
    for i in range(num_train):
        img_name = f"sss_train_{i:04d}"
        img, labels = create_single_synthetic_image(width=640, height=640, rng=rng)
        cv2.imwrite(str(images_train / f"{img_name}.jpg"), img)

        with open(labels_train / f"{img_name}.txt", "w") as f:
            for class_id, norm_pts in labels:
                pts_str = " ".join([f"{x:.6f} {y:.6f}" for x, y in norm_pts])
                f.write(f"{class_id} {pts_str}\n")

    # Generate Val Split
    for i in range(num_val):
        img_name = f"sss_val_{i:04d}"
        img, labels = create_single_synthetic_image(width=640, height=640, rng=rng)
        cv2.imwrite(str(images_val / f"{img_name}.jpg"), img)

        with open(labels_val / f"{img_name}.txt", "w") as f:
            for class_id, norm_pts in labels:
                pts_str = " ".join([f"{x:.6f} {y:.6f}" for x, y in norm_pts])
                f.write(f"{class_id} {pts_str}\n")

    # Write dataset.yaml
    yaml_content = f"""path: {out_path.as_posix()}
train: images/train
val: images/val

names:
  0: shipwreck
  1: ghost_net
  2: chemical_container
  3: metal_debris
  4: pipeline
  5: marine_plastic
"""
    yaml_path = out_path / "dataset.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"[OK] Dataset generation complete. Config written to {yaml_path}")


if __name__ == "__main__":
    generate_dataset()
