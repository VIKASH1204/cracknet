"""
routes/dashboard.py
====================
Dashboard aggregate statistics:
    GET /api/dashboard/summary             — KPI totals
    GET /api/dashboard/defect-distribution — Count per defect class
    GET /api/dashboard/trends              — Daily inspection counts (last 30 days)
"""

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.database import (
    get_dashboard_summary_data,
    get_defect_distribution_data,
    get_inspection_trends_data,
    get_severity_distribution_data,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary")
async def dashboard_summary():
    """
    Return KPI summary for the main dashboard.
    Works seamlessly with MongoDB or local storage fallback.
    """
    data = await get_dashboard_summary_data()
    return JSONResponse(content=data)


@router.get("/defect-distribution")
async def defect_distribution():
    """
    Return count of each defect class across all inspections.
    """
    data = await get_defect_distribution_data()
    return JSONResponse(content=data)


@router.get("/severity-distribution")
async def severity_distribution():
    """
    Return defect count grouped by severity level (LOW, MEDIUM, HIGH, CRITICAL).
    """
    data = await get_severity_distribution_data()
    return JSONResponse(content=data)


@router.get("/trends")
async def inspection_trends(days: int = 30):
    """
    Return daily inspection counts for the last N days.
    """
    data = await get_inspection_trends_data(days=days)
    return JSONResponse(content=data)

