"""FastAPI API endpoints for image upload, sonar processing, and data export."""

import base64
import csv
from io import StringIO
import logging
import os
from pathlib import Path
import uuid
import cv2
import geojson
import numpy as np

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from api.exceptions import ExportError, SonarPreprocessingError
from api.schemas import (
    DetectionSchema,
    ProcessSonarRequest,
    ProcessSonarResponse,
    UploadResponse,
)
from pipeline.constants import (
    SONAR_CONFIDENCE_THRESHOLD,
    TOWFISH_ALTITUDE_H_M,
    YOLO_CONF_THRESHOLD,
    YOLO_IOU_THRESHOLD,
)
from pipeline.detector import get_detector
from pipeline.geospatial import simulate_dwithin_dedup
from pipeline.sonar_cv import preprocess_waterfall
from pipeline.sss_validator import validate_sss_image

logger = logging.getLogger("atlantis.api.routes")
router = APIRouter(prefix="/api", tags=["sonar"])

# Base data paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory job store for hackathon simplicity
JOBS_STORE: dict[str, ProcessSonarResponse] = {}
UPLOADS_STORE: dict[str, Path] = {}

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024


def image_to_base64_uri(img: np.ndarray) -> str:
    """Encode OpenCV numpy image array to base64 PNG data URI string."""
    if img is None or img.size == 0:
        return ""
    success, buffer = cv2.imencode(".png", img)
    if not success:
        return ""
    b64_str = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


@router.post("/upload", response_model=UploadResponse)
async def upload_waterfall_image(file: UploadFile = File(...)) -> UploadResponse:
    """Upload multipart side-scan sonar waterfall image file."""
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg", "image/tiff"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Must be PNG, JPEG, or TIFF.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds maximum limit of {os.getenv('MAX_UPLOAD_MB', '50')} MB.",
        )

    upload_id = str(uuid.uuid4())[:8]
    safe_filename = f"{upload_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    UPLOADS_STORE[upload_id] = file_path

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename or safe_filename,
        file_path=str(file_path),
        size_bytes=len(content),
    )


@router.post("/process-sonar", response_model=ProcessSonarResponse)
def process_sonar_image(req: ProcessSonarRequest) -> Response:
    """Execute SSS image validation, acoustic preprocessing, YOLO detection, and geotagging."""
    file_path = UPLOADS_STORE.get(req.upload_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Upload ID '{req.upload_id}' not found.")

    raw_img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
    if raw_img is None:
        raise SonarPreprocessingError(f"Failed to read image file for upload ID '{req.upload_id}'.")

    # 1. SSS IMAGE VALIDATION BEFORE YOLO
    val_res = validate_sss_image(raw_img, threshold=SONAR_CONFIDENCE_THRESHOLD)
    if not val_res.is_sonar:
        logger.warning(
            f"Uploaded image '{req.upload_id}' failed SSS validation: "
            f"confidence {val_res.sonar_confidence:.2f} < {SONAR_CONFIDENCE_THRESHOLD:.2f}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "is_sonar": False,
                "sonar_confidence": val_res.sonar_confidence,
                "message": val_res.message,
            },
        )

    # 2. Acoustic preprocessing (runs only if valid SSS image)
    prep_res = preprocess_waterfall(raw_img)

    detector = get_detector()
    conf_thresh = req.conf_threshold if req.conf_threshold is not None else YOLO_CONF_THRESHOLD

    # 2. Run detector on Port & Starboard channels
    port_dets = detector.run_full_pipeline(
        channel=prep_res.port_processed,
        channel_name="port",
        towfish_lat=req.towfish_lat,
        towfish_lon=req.towfish_lon,
        towfish_heading_deg=req.towfish_heading_deg,
        altitude_m=req.altitude_m,
        ray_vector=(-1.0, 0.0),
        conf_threshold=conf_thresh,
    )

    starboard_dets = detector.run_full_pipeline(
        channel=prep_res.starboard_processed,
        channel_name="starboard",
        towfish_lat=req.towfish_lat,
        towfish_lon=req.towfish_lon,
        towfish_heading_deg=req.towfish_heading_deg,
        altitude_m=req.altitude_m,
        ray_vector=(1.0, 0.0),
        conf_threshold=conf_thresh,
    )

    all_pipeline_dets = port_dets + starboard_dets

    # Convert to dicts for spatial deduplication
    det_dicts = []
    for d in all_pipeline_dets:
        det_dicts.append(
            {
                "detection_id": d.detection_id,
                "class_name": d.class_name,
                "confidence": d.confidence,
                "bbox": d.bbox,
                "polygon": d.polygon,
                "shadow_verdict": d.shadow_verdict,
                "shadow_intensity": d.shadow_intensity,
                "estimated_elevation_m": d.estimated_elevation_m,
                "area_m2": d.area_m2,
                "span_m": d.span_m,
                "hpi_score": d.hpi_score,
                "hpi_tier": d.hpi_tier,
                "lat": d.lat,
                "lon": d.lon,
                "channel": d.channel,
                "components": d.components,
            }
        )

    deduped_dicts = simulate_dwithin_dedup(det_dicts)
    final_detections = [DetectionSchema(**d) for d in deduped_dicts]

    # Count tier distribution
    crit_count = sum(1 for d in final_detections if d.hpi_tier == "CRITICAL")
    high_count = sum(1 for d in final_detections if d.hpi_tier == "HIGH")
    mod_count = sum(1 for d in final_detections if d.hpi_tier == "MODERATE")
    low_count = sum(1 for d in final_detections if d.hpi_tier == "LOW")

    job_id = f"job_{uuid.uuid4().hex[:8]}"

    response = ProcessSonarResponse(
        success=True,
        is_sonar=True,
        sonar_confidence=val_res.sonar_confidence,
        message=val_res.message,
        job_id=job_id,
        upload_id=req.upload_id,
        preprocessed_port_b64=image_to_base64_uri(prep_res.port_processed),
        preprocessed_starboard_b64=image_to_base64_uri(prep_res.starboard_processed),
        raw_port_b64=image_to_base64_uri(prep_res.port_raw),
        raw_starboard_b64=image_to_base64_uri(prep_res.starboard_raw),
        detections=final_detections,
        total_detections=len(final_detections),
        critical_count=crit_count,
        high_count=high_count,
        moderate_count=mod_count,
        low_count=low_count,
        nadir_metadata=prep_res.metadata,
    )

    JOBS_STORE[job_id] = response
    return response


@router.post("/demo/run-synthetic", response_model=ProcessSonarResponse)
def run_synthetic_demo() -> ProcessSonarResponse:
    """Execute synthetic sonar generator and run end-to-end demo pipeline."""
    from pipeline.synthetic_generator import generate_synthetic_waterfall

    raw_synth_img, gt_targets = generate_synthetic_waterfall()

    upload_id = f"demo_synth_{uuid.uuid4().hex[:6]}"
    file_path = UPLOAD_DIR / f"{upload_id}.png"
    cv2.imwrite(str(file_path), raw_synth_img)
    UPLOADS_STORE[upload_id] = file_path

    req = ProcessSonarRequest(
        upload_id=upload_id,
        towfish_lat=25.7617,
        towfish_lon=-80.1918,
        towfish_heading_deg=45.0,
        altitude_m=TOWFISH_ALTITUDE_H_M,
    )

    return process_sonar_image(req)


@router.get("/export-geojson/{job_id}")
def export_job_geojson(job_id: str) -> Response:
    """Stream GeoJSON FeatureCollection of all detections for job_id."""
    job_res = JOBS_STORE.get(job_id)
    if not job_res:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")

    features = []
    for det in job_res.detections:
        pt = geojson.Point((det.lon, det.lat))
        props = {
            "detection_id": det.detection_id,
            "class_name": det.class_name,
            "confidence": det.confidence,
            "hpi_score": det.hpi_score,
            "hpi_tier": det.hpi_tier,
            "shadow_verdict": det.shadow_verdict,
            "estimated_elevation_m": det.estimated_elevation_m,
            "area_m2": det.area_m2,
            "span_m": det.span_m,
            "channel": det.channel,
        }
        features.append(geojson.Feature(geometry=pt, properties=props))

    fc = geojson.FeatureCollection(features)
    geojson_str = geojson.dumps(fc, indent=2)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=atlantis_mission_{job_id}.geojson"},
    )


@router.get("/export-csv/{job_id}")
def export_job_csv(job_id: str) -> StreamingResponse:
    """Stream CSV mission log of all detections for job_id."""
    job_res = JOBS_STORE.get(job_id)
    if not job_res:
        raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Detection ID",
            "Class",
            "Confidence",
            "HPI Score",
            "HPI Tier",
            "Shadow Verdict",
            "Elevation (m)",
            "Area (m2)",
            "Span (m)",
            "Latitude",
            "Longitude",
            "Channel",
        ]
    )

    for det in job_res.detections:
        writer.writerow(
            [
                det.detection_id,
                det.class_name,
                det.confidence,
                det.hpi_score,
                det.hpi_tier,
                det.shadow_verdict,
                det.estimated_elevation_m,
                det.area_m2,
                det.span_m,
                det.lat,
                det.lon,
                det.channel,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=atlantis_mission_{job_id}.csv"},
    )
