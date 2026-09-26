"""API endpoint unit tests using httpx AsyncClient."""

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from pipeline.synthetic_generator import generate_synthetic_waterfall


@pytest.fixture
def test_image_bytes():
    """Create a synthetic test image PNG byte payload."""
    img, _ = generate_synthetic_waterfall()
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


@pytest.mark.anyio
async def test_api_health_endpoint():
    """Test /api/health endpoint returns 200 OK and valid health schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "model_loaded" in data
        assert "version" in data


@pytest.mark.anyio
async def test_api_upload_and_process(test_image_bytes):
    """Test full API workflow: upload synthetic image -> process sonar -> export."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Upload image
        files = {"file": ("synthetic_waterfall.png", test_image_bytes, "image/png")}
        up_res = await ac.post("/api/upload", files=files)
        assert up_res.status_code == 200
        up_data = up_res.json()
        assert "upload_id" in up_data
        upload_id = up_data["upload_id"]

        # 2. Process sonar image
        proc_payload = {
            "upload_id": upload_id,
            "towfish_lat": 25.7617,
            "towfish_lon": -80.1918,
            "towfish_heading_deg": 45.0,
            "altitude_m": 8.0,
        }
        proc_res = await ac.post("/api/process-sonar", json=proc_payload)
        assert proc_res.status_code == 200
        proc_data = proc_res.json()

        assert proc_data["success"] is True
        assert proc_data["is_sonar"] is True
        assert "job_id" in proc_data
        assert "detections" in proc_data
        assert proc_data["total_detections"] >= 1

        det = proc_data["detections"][0]
        assert "class_name" in det
        assert "hpi_score" in det
        assert "hpi_tier" in det
        assert "lat" in det
        assert "lon" in det
        assert "estimated_elevation_m" in det

        # 3. Export GeoJSON
        job_id = proc_data["job_id"]
        geojson_res = await ac.get(f"/api/export-geojson/{job_id}")
        assert geojson_res.status_code == 200
        assert geojson_res.headers["content-type"].startswith("application/geo+json")

        # 4. Export CSV
        csv_res = await ac.get(f"/api/export-csv/{job_id}")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]


@pytest.mark.anyio
async def test_api_rejects_non_sss_image():
    """Test that API rejects non-sonar RGB photo without running YOLO."""
    # Create multi-color RGB photo simulation
    rgb_photo = np.zeros((300, 400, 3), dtype=np.uint8)
    rgb_photo[:, :130] = [255, 0, 0]
    rgb_photo[:, 130:260] = [0, 255, 0]
    rgb_photo[:, 260:] = [0, 0, 255]
    _, buf = cv2.imencode(".png", rgb_photo)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("non_sonar_photo.png", buf.tobytes(), "image/png")}
        up_res = await ac.post("/api/upload", files=files)
        assert up_res.status_code == 200
        upload_id = up_res.json()["upload_id"]

        proc_res = await ac.post("/api/process-sonar", json={"upload_id": upload_id})
        assert proc_res.status_code == 422
        data = proc_res.json()
        assert data["success"] is False
        assert data["is_sonar"] is False
        assert data["sonar_confidence"] < 0.80
        assert "Invalid Image" in data["message"]


@pytest.mark.anyio
async def test_demo_run_synthetic_endpoint():
    """Test /api/demo/run-synthetic endpoint returns 200 OK with processed detections."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/demo/run-synthetic")
        assert res.status_code == 200
        data = res.json()
        assert "job_id" in data
        assert "detections" in data
        assert data["total_detections"] >= 1
