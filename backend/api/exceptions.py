"""Custom exception classes for Project Atlantis backend."""


class AtlantisBaseException(Exception):
    """Base exception for Project Atlantis errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class SonarPreprocessingError(AtlantisBaseException):
    """Raised when sonar image preprocessing fails."""

    def __init__(self, message: str):
        super().__init__(message, code="PREPROCESSING_ERROR", status_code=422)


class DetectionError(AtlantisBaseException):
    """Raised when object detection fails."""

    def __init__(self, message: str):
        super().__init__(message, code="DETECTION_ERROR", status_code=422)


class GeospatialError(AtlantisBaseException):
    """Raised when geospatial calculations fail."""

    def __init__(self, message: str):
        super().__init__(message, code="GEOSPATIAL_ERROR", status_code=422)


class ExportError(AtlantisBaseException):
    """Raised when exporting GeoJSON or CSV fails."""

    def __init__(self, message: str):
        super().__init__(message, code="EXPORT_ERROR", status_code=500)


class DatasetIngestionError(AtlantisBaseException):
    """Raised when dataset loading or discovery fails."""

    def __init__(self, message: str):
        super().__init__(message, code="DATASET_INGESTION_ERROR", status_code=400)


class BatchReportNotFoundError(AtlantisBaseException):
    """Raised when a requested batch report does not exist."""

    def __init__(self, message: str):
        super().__init__(message, code="BATCH_REPORT_NOT_FOUND", status_code=404)
