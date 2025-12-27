"""Web адаптер FastAPI."""

from .router import projects_router, reports_router, system_router
from .schemas import (
    AddProjectRequest,
    AllTrackerProjectsResponse,
    DefaultProjectsResponse,
    ErrorResponse,
    HealthResponse,
    ProjectOperationResponse,
    RemoveProjectRequest,
    ReportRequestSchema,
    ReportStatusResponse,
    SetDefaultProjectsRequest,
    TrackerProjectInfo,
)

__all__ = [
    "reports_router",
    "projects_router",
    "system_router",
    "ReportRequestSchema",
    "ErrorResponse",
    "HealthResponse",
    "ReportStatusResponse",
    "TrackerProjectInfo",
    "AllTrackerProjectsResponse",
    "DefaultProjectsResponse",
    "SetDefaultProjectsRequest",
    "AddProjectRequest",
    "RemoveProjectRequest",
    "ProjectOperationResponse",
]
