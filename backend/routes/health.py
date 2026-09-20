"""
routes/health.py
================
GET /api/health — System health check endpoint.

Returns model status, device, and MongoDB connectivity.
No authentication required — used by monitoring tools and the frontend.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.inference_service import (
    is_model_loaded,
    are_weights_loaded,
    get_device,
    get_model_info,
)
from backend.database import is_connected as db_is_connected

router = APIRouter(prefix="/api", tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    weights_loaded: bool
    device: str
    mongodb_connected: bool
    model_info: dict


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    System health check.

    Returns:
        status:            "online" always (if the server is responding).
        model_loaded:      True if CrackXNet architecture is initialised.
        weights_loaded:    True if a real checkpoint was found and loaded.
        device:            "cuda" or "cpu".
        mongodb_connected: True if MongoDB is reachable.
        model_info:        Metadata about the loaded model.
    """
    return HealthResponse(
        status="online",
        model_loaded=is_model_loaded(),
        weights_loaded=are_weights_loaded(),
        device=get_device(),
        mongodb_connected=db_is_connected(),
        model_info=get_model_info(),
    )
