"""Unit tests for Project Atlantis sonar processing, physics, heuristic classification, SSS validation, and synthetic pipeline engine."""

import numpy as np
import pytest
from pipeline.constants import SONAR_CONFIDENCE_THRESHOLD, TOWFISH_ALTITUDE_H_M
from pipeline.detector import get_detector, heuristic_classify
from pipeline.geospatial import compute_hpi, slant_to_ground_range
from pipeline.shadow_verifier import (
    ShadowVerdict,
    dual_branch_classification,
    estimate_elevation,
    verify_physical_protrusion,
)
from pipeline.sonar_cv import preprocess_waterfall
from pipeline.sss_validator import validate_sss_image
from pipeline.synthetic_generator import generate_synthetic_waterfall


def test_physics_slant_to_ground_range():
    """Test Pythagorean slant-to-ground range calculation against hand-computed values."""
    ground_range = slant_to_ground_range(10.0, 6.0)
    assert pytest.approx(ground_range, 1e-4) == 8.0

    ground_range_2 = slant_to_ground_range(75.0, 8.0)
    assert pytest.approx(ground_range_2, 1e-3) == 74.572

    with pytest.raises(ValueError):
        slant_to_ground_range(5.0, 8.0)


def test_physics_estimate_elevation():
    """Test target elevation calculation from shadow geometry against hand-computed values."""
    h = estimate_elevation(shadow_length_px=20.0, slant_range_px=50.0, altitude_m=8.0, px_to_m_ratio=0.1)
    assert pytest.approx(h, 1e-4) == 3.2

    with pytest.raises(ValueError):
        estimate_elevation(shadow_length_px=10.0, slant_range_px=0.0, altitude_m=8.0)


def test_physics_compute_hpi():
    """Test Hazard Priority Index calculation and risk tier bands."""
    res = compute_hpi("shipwreck", span_m=10.0, depth_m=5.0)
    assert pytest.approx(res.score, 1e-3) == 0.655
    assert res.tier == "HIGH"

    res_crit = compute_hpi("chemical_container", span_m=20.0, depth_m=10.0)
    assert pytest.approx(res_crit.score, 1e-3) == 0.9475
    assert res_crit.tier == "CRITICAL"


def test_physics_shadow_verification():
    """Test dual-branch shadow verification tree."""
    assert verify_physical_protrusion(20.0) is True
    assert verify_physical_protrusion(50.0) is False

    verdict_prot = dual_branch_classification(shadow_intensity=20.0, roughness_score=10.0)
    assert verdict_prot == ShadowVerdict.PROTRUSION_CONFIRMED

    verdict_benthic = dual_branch_classification(shadow_intensity=50.0, roughness_score=25.0)
    assert verdict_benthic == ShadowVerdict.BENTHIC_DRAPED

    verdict_seabed = dual_branch_classification(shadow_intensity=50.0, roughness_score=5.0)
    assert verdict_seabed == ShadowVerdict.DISCARDED_SEABED


def test_heuristic_classify_pipeline():
    """Test heuristic classifier identifies elongated linear corridor as pipeline."""
    cnt = np.array([[0, 0], [10, 0], [10, 100], [0, 100]], dtype=np.int32).reshape(-1, 1, 2)
    bbox = [0, 0, 10, 100]

    cls_name, conf = heuristic_classify(
        contour=cnt,
        bbox=bbox,
        mean_intensity=150.0,
        std_intensity=20.0,
        shadow_verdict=ShadowVerdict.PROTRUSION_CONFIRMED,
        px_to_m_ratio=0.1,
    )
    assert cls_name == "pipeline"
    assert conf >= 0.75


def test_heuristic_classify_metal_debris():
    """Test heuristic classifier identifies bright compact rectangle as metal_debris."""
    cnt = np.array([[0, 0], [20, 0], [20, 20], [0, 20]], dtype=np.int32).reshape(-1, 1, 2)
    bbox = [0, 0, 20, 20]

    cls_name, conf = heuristic_classify(
        contour=cnt,
        bbox=bbox,
        mean_intensity=210.0,
        std_intensity=15.0,
        shadow_verdict=ShadowVerdict.PROTRUSION_CONFIRMED,
        px_to_m_ratio=0.1,
    )
    assert cls_name == "metal_debris"
    assert conf >= 0.70


def test_sss_validator_valid_and_invalid():
    """Test SSS Image Validator accepts real SSS imagery and rejects non-sonar RGB images."""
    # 1. Valid SSS Image (synthetic sonar waterfall)
    synth_sss, _ = generate_synthetic_waterfall()
    val_valid = validate_sss_image(synth_sss, threshold=SONAR_CONFIDENCE_THRESHOLD)
    assert val_valid.is_sonar is True
    assert val_valid.sonar_confidence >= SONAR_CONFIDENCE_THRESHOLD

    # 2. Invalid Non-Sonar Image (colorful RGB photo simulation)
    rgb_photo = np.zeros((300, 400, 3), dtype=np.uint8)
    rgb_photo[:, :130] = [255, 0, 0]  # Bright blue
    rgb_photo[:, 130:260] = [0, 255, 0]  # Bright green
    rgb_photo[:, 260:] = [0, 0, 255]  # Bright red

    val_invalid = validate_sss_image(rgb_photo, threshold=SONAR_CONFIDENCE_THRESHOLD)
    assert val_invalid.is_sonar is False
    assert val_invalid.sonar_confidence < SONAR_CONFIDENCE_THRESHOLD


def test_synthetic_full_pipeline():
    """Test end-to-end processing of synthetic waterfall image with all 6 target classes."""
    raw_synth, gt_targets = generate_synthetic_waterfall()
    assert raw_synth.shape == (600, 800)
    assert len(gt_targets) == 6

    prep_res = preprocess_waterfall(raw_synth)
    assert prep_res.port_processed.shape[0] == 600
    assert prep_res.starboard_processed.shape[0] == 600

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
    assert len(all_dets) >= 4  # Recovers target candidates

    valid_tiers = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
    for d in all_dets:
        assert d.hpi_tier in valid_tiers
        assert 0.0 <= d.hpi_score <= 1.0
        assert d.estimated_elevation_m >= 0.0
