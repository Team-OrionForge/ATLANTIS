"""FastAPI batch dataset processing API routes."""

import csv
from io import StringIO
import logging
import os
from pathlib import Path
from typing import Optional
import uuid

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
import geojson
from pydantic import BaseModel

from api.schemas import BatchReportSchema, BatchStatusResponse, BatchUploadResponse
from pipeline.batch_processor import load_batch_report, run_batch

logger = logging.getLogger("atlantis.api.batch")
router = APIRouter(prefix="/api/batch", tags=["batch"])

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_BASE_DIR = BASE_DIR / "data" / "dataset"
DATASET_BASE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory status store for running background batches
BATCH_STATUS_STORE: dict[str, dict] = {}


class LocalBatchRunRequest(BaseModel):
    """Local dataset path run request model."""

    dataset_path: Optional[str] = None
    conf_threshold: Optional[float] = 0.65
    iou_threshold: Optional[float] = 0.45


@router.post("/upload-dataset", response_model=BatchUploadResponse)
async def upload_dataset_batch(
    dataset_path: Optional[str] = None,
    files: list[UploadFile] = File(default=[]),
) -> BatchUploadResponse:
    """Accept multi-file upload or server-side local dataset path."""
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    batch_dir = DATASET_BASE_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    if dataset_path:
        local_path = Path(dataset_path).resolve()
        # Security check: verify path exists
        if not local_path.exists():
            raise HTTPException(status_code=400, detail=f"Local dataset path '{dataset_path}' does not exist.")
        return BatchUploadResponse(
            batch_id=batch_id,
            image_count=len(list(local_path.glob("*.*"))),
            dataset_path=str(local_path),
        )

    if not files:
        # Check if root Dataset folder exists
        root_dataset = BASE_DIR.parent / "Dataset"
        if root_dataset.exists():
            return BatchUploadResponse(
                batch_id=batch_id,
                image_count=len(list(root_dataset.glob("*.*"))),
                dataset_path=str(root_dataset),
            )
        raise HTTPException(status_code=400, detail="No files uploaded and no local dataset_path provided.")

    saved_count = 0
    for file in files:
        if file.filename:
            target_file = batch_dir / file.filename
            content = await file.read()
            with open(target_file, "wb") as f:
                f.write(content)
            saved_count += 1

    return BatchUploadResponse(
        batch_id=batch_id,
        image_count=saved_count,
        dataset_path=str(batch_dir),
    )


def _execute_batch_job(batch_id: str, dataset_dir: str, conf: float, iou: float) -> None:
    """Execute batch runner in background task thread."""
    def progress_cb(completed: int, total: int) -> None:
        if batch_id in BATCH_STATUS_STORE:
            BATCH_STATUS_STORE[batch_id]["completed"] = completed
            BATCH_STATUS_STORE[batch_id]["total"] = total

    try:
        run_batch(
            dataset_dir=dataset_dir,
            batch_id=batch_id,
            conf_threshold=conf,
            iou_threshold=iou,
            progress_callback=progress_cb,
        )
        if batch_id in BATCH_STATUS_STORE:
            BATCH_STATUS_STORE[batch_id]["status"] = "done"
    except Exception as exc:
        logger.error(f"Batch execution failed for {batch_id}: {exc}", exc_info=True)
        if batch_id in BATCH_STATUS_STORE:
            BATCH_STATUS_STORE[batch_id]["status"] = "failed"
            BATCH_STATUS_STORE[batch_id]["error"] = str(exc)


@router.post("/{batch_id}/run", status_code=202)
def start_batch_processing(
    batch_id: str,
    req: LocalBatchRunRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Kick off run_batch as a non-blocking background job."""
    dataset_dir = req.dataset_path
    if not dataset_dir:
        batch_dir = DATASET_BASE_DIR / batch_id
        if batch_dir.exists():
            dataset_dir = str(batch_dir)
        else:
            root_dataset = BASE_DIR.parent / "Dataset"
            if root_dataset.exists():
                dataset_dir = str(root_dataset)
            else:
                raise HTTPException(status_code=404, detail=f"Dataset directory for batch '{batch_id}' not found.")

    BATCH_STATUS_STORE[batch_id] = {
        "status": "running",
        "completed": 0,
        "total": 0,
        "succeeded": 0,
        "failed": 0,
    }

    background_tasks.add_task(
        _execute_batch_job,
        batch_id,
        dataset_dir,
        req.conf_threshold or 0.65,
        req.iou_threshold or 0.45,
    )

    return {"batch_id": batch_id, "status": "running", "status_url": f"/api/batch/{batch_id}/status"}


@router.get("/{batch_id}/status", response_model=BatchStatusResponse)
def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """Poll current progress status of background batch run."""
    status_data = BATCH_STATUS_STORE.get(batch_id)
    if not status_data:
        try:
            report = load_batch_report(batch_id)
            return BatchStatusResponse(
                batch_id=batch_id,
                status="done",
                completed=report.total_images,
                total=report.total_images,
                succeeded=report.succeeded,
                failed=report.failed,
            )
        except Exception:
            raise HTTPException(status_code=404, detail=f"Batch ID '{batch_id}' not found.")

    return BatchStatusResponse(
        batch_id=batch_id,
        status=status_data.get("status", "running"),
        completed=status_data.get("completed", 0),
        total=status_data.get("total", 0),
        succeeded=status_data.get("succeeded", 0),
        failed=status_data.get("failed", 0),
    )


@router.get("/{batch_id}/report", response_model=BatchReportSchema)
def get_batch_report(batch_id: str) -> BatchReportSchema:
    """Return completed aggregate BatchReport payload."""
    report = load_batch_report(batch_id)
    return report  # Pydantic validates and returns


@router.get("/{batch_id}/export-geojson")
def export_batch_geojson(batch_id: str) -> Response:
    """Stream aggregate GeoJSON FeatureCollection across all batch images."""
    report = load_batch_report(batch_id)
    features = []

    for img_res in report.per_image_results:
        for det in img_res.detections:
            pt = geojson.Point((det.lon, det.lat))
            props = {
                "source_image": img_res.filename,
                "detection_id": det.detection_id,
                "class_name": det.class_name,
                "confidence": det.confidence,
                "hpi_score": det.hpi_score,
                "hpi_tier": det.hpi_tier,
                "estimated_elevation_m": det.estimated_elevation_m,
                "area_m2": det.area_m2,
                "span_m": det.span_m,
                "geolocation_estimated": img_res.geolocation_estimated,
            }
            features.append(geojson.Feature(geometry=pt, properties=props))

    fc = geojson.FeatureCollection(features)
    return Response(
        content=geojson.dumps(fc, indent=2),
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=atlantis_batch_{batch_id}.geojson"},
    )


@router.get("/{batch_id}/export-csv")
def export_batch_csv(batch_id: str) -> StreamingResponse:
    """Stream aggregate CSV mission log across all batch images."""
    report = load_batch_report(batch_id)
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Source Image",
            "Detection ID",
            "Class",
            "Confidence",
            "HPI Score",
            "HPI Tier",
            "Elevation (m)",
            "Area (m2)",
            "Span (m)",
            "Latitude",
            "Longitude",
            "Channel",
            "Geolocation Estimated",
        ]
    )

    for img_res in report.per_image_results:
        for det in img_res.detections:
            writer.writerow(
                [
                    img_res.filename,
                    det.detection_id,
                    det.class_name,
                    det.confidence,
                    det.hpi_score,
                    det.hpi_tier,
                    det.estimated_elevation_m,
                    det.area_m2,
                    det.span_m,
                    det.lat,
                    det.lon,
                    det.channel,
                    img_res.geolocation_estimated,
                ]
            )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=atlantis_batch_{batch_id}.csv"},
    )
