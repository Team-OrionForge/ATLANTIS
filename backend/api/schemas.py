"""Pydantic v2 schemas and data validation models for Project Atlantis API."""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    """Liveness and readiness health response schema."""

    status: str = "ok"
    model_loaded: bool
    degraded_mode: bool
    version: str = "1.0.0"
    uptime_seconds: float


class UploadResponse(BaseModel):
    """Waterfall image upload response schema."""

    upload_id: str
    filename: str
    file_path: str
    size_bytes: int


class ProcessSonarRequest(BaseModel):
    """Sonar waterfall processing request parameters."""

    upload_id: str
    towfish_lat: float = Field(default=25.7617, description="Towfish origin latitude [-90, 90]")
    towfish_lon: float = Field(default=-80.1918, description="Towfish origin longitude [-180, 180]")
    towfish_heading_deg: float = Field(default=45.0, description="Towfish heading in degrees [0, 360)")
    altitude_m: float = Field(default=8.0, description="Towfish altitude above seabed in meters")
    conf_threshold: Optional[float] = Field(default=0.65, ge=0.0, le=1.0)
    iou_threshold: Optional[float] = Field(default=0.45, ge=0.0, le=1.0)

    @field_validator("towfish_lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        return v

    @field_validator("towfish_lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and 180 degrees.")
        return v

    @field_validator("towfish_heading_deg")
    @classmethod
    def validate_heading(cls, v: float) -> float:
        if not (0.0 <= v < 360.0):
            raise ValueError("Heading must be in degrees [0, 360).")
        return v


class DetectionSchema(BaseModel):
    """Target detection telemetry and geospatial payload schema."""

    detection_id: str
    class_name: str
    confidence: float
    bbox: list[int]
    polygon: list[list[int]]
    shadow_verdict: str
    shadow_intensity: float
    estimated_elevation_m: float
    area_m2: float
    span_m: float
    hpi_score: float
    hpi_tier: str
    lat: float
    lon: float
    channel: str
    components: dict[str, float] = Field(default_factory=dict)


class ProcessSonarResponse(BaseModel):
    """Comprehensive sonar analysis response payload."""

    success: bool = True
    is_sonar: bool = True
    sonar_confidence: float = 1.0
    message: Optional[str] = None
    job_id: str
    upload_id: str
    preprocessed_port_b64: str
    preprocessed_starboard_b64: str
    raw_port_b64: str
    raw_starboard_b64: str
    detections: list[DetectionSchema]
    total_detections: int
    critical_count: int
    high_count: int
    moderate_count: int
    low_count: int
    nadir_metadata: dict[str, Any]


class InvalidSonarImageResponse(BaseModel):
    """Response payload for rejected non-SSS uploaded images."""

    success: bool = False
    is_sonar: bool = False
    sonar_confidence: float
    message: str


class BatchUploadResponse(BaseModel):
    """Batch dataset ingestion upload response."""

    batch_id: str
    image_count: int
    dataset_path: str


class BatchStatusResponse(BaseModel):
    """Batch processing status response payload."""

    batch_id: str
    status: str  # "queued", "running", "done", "failed"
    completed: int
    total: int
    succeeded: int
    failed: int


class BatchImageResultSchema(BaseModel):
    """Per-image result summary inside a batch report."""

    filename: str
    status: str
    detection_count: int
    geolocation_estimated: bool
    detections: list[DetectionSchema]
    error: Optional[str] = None


class BatchReportSchema(BaseModel):
    """Aggregate batch report response payload."""

    batch_id: str
    total_images: int
    succeeded: int
    failed: int
    processing_time_s: float
    detections_by_class: dict[str, int]
    hpi_tier_breakdown: dict[str, int]
    flagged_estimated_geolocation_count: int
    per_image_results: list[BatchImageResultSchema]
