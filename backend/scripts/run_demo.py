"""Convenience execution script for Project Atlantis end-to-end synthetic demo."""

import logging
from pathlib import Path
import sys

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.constants import TOWFISH_ALTITUDE_H_M
from pipeline.detector import get_detector
from pipeline.sonar_cv import preprocess_waterfall
from pipeline.synthetic_generator import generate_synthetic_waterfall

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("atlantis.run_demo")


def run_mock_demo() -> None:
    """Execute synthetic sonar pipeline and print detection summary."""
    logger.info("Generating procedural synthetic side-scan sonar waterfall image...")
    raw_img, gt_targets = generate_synthetic_waterfall()

    logger.info(f"Synthetic image generated with {len(gt_targets)} ground-truth targets.")
    for gt in gt_targets:
        logger.info(f"  - Ground Truth Target: {gt.class_name} ({gt.channel} channel, shadow={gt.shadow_rendered})")

    logger.info("Executing acoustic preprocessing (split nadir -> CLAHE -> bilateral filter)...")
    prep_res = preprocess_waterfall(raw_img)

    logger.info("Executing YOLOv8 / Heuristic detection, shadow verification & geospatial tagging...")
    detector = get_detector()

    port_dets = detector.run_full_pipeline(
        channel=prep_res.port_processed,
        channel_name="port",
        towfish_lat=25.7617,
        towfish_lon=-80.1918,
        towfish_heading_deg=45.0,
        altitude_m=TOWFISH_ALTITUDE_H_M,
        ray_vector=(-1.0, 0.0),
    )

    starboard_dets = detector.run_full_pipeline(
        channel=prep_res.starboard_processed,
        channel_name="starboard",
        towfish_lat=25.7617,
        towfish_lon=-80.1918,
        towfish_heading_deg=45.0,
        altitude_m=TOWFISH_ALTITUDE_H_M,
        ray_vector=(1.0, 0.0),
    )

    all_dets = port_dets + starboard_dets
    logger.info("==========================================================================")
    logger.info(f"DEMO COMPLETE: Discovered {len(all_dets)} detections across dual channels.")
    logger.info("==========================================================================")

    for d in all_dets:
        logger.info(
            f"  [ID: {d.detection_id}] Class: {d.class_name:<18} | Conf: {d.confidence:.2f} | "
            f"HPI: {d.hpi_score:.2f} ({d.hpi_tier:<8}) | Shadow: {d.shadow_verdict:<20} | "
            f"Elev: {d.estimated_elevation_m:.2f}m | Lat/Lon: ({d.lat:.6f}, {d.lon:.6f})"
        )


if __name__ == "__main__":
    run_mock_demo()
