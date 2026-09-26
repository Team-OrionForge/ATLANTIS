"""Unit tests for real dataset batch ingestion and report generation pipeline."""

import shutil
import tempfile
import cv2
import pytest
from pipeline.batch_processor import load_batch_report, run_batch
from pipeline.synthetic_generator import generate_synthetic_waterfall


@pytest.fixture
def temp_dataset_dir():
    """Create a temporary directory populated with 10 synthetic sonar images and 1 corrupt file."""
    temp_dir = tempfile.mkdtemp()
    synth_img, _ = generate_synthetic_waterfall()

    # Create 9 valid synthetic images
    for i in range(9):
        img_path = f"{temp_dir}/sonar_{i:04d}.png"
        cv2.imwrite(img_path, synth_img)

    # Create 1 deliberately corrupt image file
    corrupt_path = f"{temp_dir}/sonar_corrupt.png"
    with open(corrupt_path, "wb") as f:
        f.write(b"CORRUPT_NON_IMAGE_DATA_BYTES")

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_run_batch_end_to_end(temp_dataset_dir):
    """Test batch processing runner over 10 images with graceful error handling for 1 corrupt file."""
    batch_id = "test_batch_001"

    report = run_batch(
        dataset_dir=temp_dataset_dir,
        batch_id=batch_id,
        max_workers=2,
    )

    assert report.total_images == 10
    assert report.succeeded == 9
    assert report.failed == 1
    assert report.succeeded + report.failed == 10
    assert report.flagged_estimated_geolocation_count == 10
    assert len(report.per_image_results) == 10

    # Verify JSON report persistence & round-trip loading
    loaded_report = load_batch_report(batch_id)
    assert loaded_report.batch_id == batch_id
    assert loaded_report.total_images == 10
    assert loaded_report.succeeded == 9
    assert loaded_report.failed == 1
