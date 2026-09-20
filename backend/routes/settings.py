"""
routes/settings.py
==================
Endpoints for viewing and configuring quality inspection parameters:
    GET  /api/settings — Retrieve active thresholds and station parameters
    POST /api/settings — Update configurable thresholds
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from backend.database import get_settings_record, save_settings_record

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsUpdateSchema(BaseModel):
    confidence_threshold: Optional[float] = Field(None, ge=0.05, le=0.99, description="Defect detection confidence threshold")
    iou_threshold: Optional[float] = Field(None, ge=0.05, le=0.95, description="Non-Maximum Suppression IoU threshold")
    station_id: Optional[str] = Field(None, max_length=50)
    line_id: Optional[str] = Field(None, max_length=50)
    alert_sound: Optional[bool] = None
    conveyor_interval_sec: Optional[int] = Field(None, ge=1, le=60)


@router.get("")
async def get_settings():
    """Retrieve active system parameters and detection thresholds."""
    data = await get_settings_record()
    return JSONResponse(content=data)


@router.post("")
async def update_settings(payload: SettingsUpdateSchema):
    """
    Update configurable inspection thresholds and store to MongoDB / local fallback.
    Architecture integrity is protected — model weights and layers cannot be modified.
    """
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid settings fields provided for update.",
        )

    updated = await save_settings_record(update_data)
    logger.info("Inspection thresholds updated: %s", update_data)
    return JSONResponse(content=updated)
