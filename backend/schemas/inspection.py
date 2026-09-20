"""
schemas/inspection.py
=====================
Pydantic models for inspection request/response validation.

These schemas are the canonical data contract between the FastAPI backend
and the frontend. Every field is explicitly typed and documented.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ===========================================================================
# Sub-schemas
# ===========================================================================


class BBox(BaseModel):
    """Axis-aligned bounding box in pixel coordinates."""
    x1: int = Field(..., description="Left edge (pixels)")
    y1: int = Field(..., description="Top edge (pixels)")
    x2: int = Field(..., description="Right edge (pixels)")
    y2: int = Field(..., description="Bottom edge (pixels)")

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)


class DefectDetection(BaseModel):
    """A single detected PCB defect."""
    class_id: int = Field(..., description="Zero-based class index")
    class_name: str = Field(..., description="Defect class name (e.g. 'short')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence [0,1]")
    severity: str = Field(..., description="Severity level: LOW | MEDIUM | HIGH | CRITICAL")
    severity_score: float = Field(..., ge=0.0, le=1.0, description="Expert-defined severity score [0,1]")
    bbox: BBox


class InspectionRequest(BaseModel):
    """Optional metadata that can accompany an image upload."""
    pcb_id: Optional[str] = Field(None, description="Operator-assigned PCB identifier")
    operator_id: Optional[str] = Field(None, description="Operator ID for traceability")
    line_id: Optional[str] = Field(None, description="Production line identifier")
    notes: Optional[str] = Field(None, description="Free-text notes")


class InspectionResult(BaseModel):
    """Complete result returned from a single PCB inspection."""
    inspection_id: str = Field(..., description="Unique MongoDB document ID")
    pcb_id: str = Field(..., description="PCB identifier (auto-generated if not supplied)")
    timestamp: datetime = Field(..., description="ISO-8601 UTC timestamp")
    processing_time_ms: float = Field(..., description="Total wall-clock inference time (ms)")
    defect_count: int = Field(..., ge=0)
    defects: List[DefectDetection]
    decision: str = Field(..., description="Quality decision: PASS | REWORK | REJECT")
    image_url: Optional[str] = Field(None, description="URL to original uploaded image")
    result_image_url: Optional[str] = Field(None, description="URL to annotated result image")
    explainability_url: Optional[str] = Field(None, description="URL to saliency map overlay")
    # Optional provenance
    operator_id: Optional[str] = None
    line_id: Optional[str] = None
    notes: Optional[str] = None
    # DB availability flag
    persisted: bool = Field(True, description="False if MongoDB was unavailable during save")


class InspectionSummary(BaseModel):
    """Lightweight summary row used in history tables."""
    inspection_id: str
    pcb_id: str
    timestamp: datetime
    defect_count: int
    highest_severity: str
    decision: str
    processing_time_ms: float


class HistoryResponse(BaseModel):
    """Paginated inspection history."""
    total: int
    page: int
    limit: int
    items: List[InspectionSummary]


class DashboardSummary(BaseModel):
    """Aggregate statistics for the main dashboard."""
    total_inspections: int
    pass_count: int
    rework_count: int
    reject_count: int
    defect_count: int
    average_processing_time_ms: float


class DefectDistribution(BaseModel):
    """Count of detections per defect class."""
    class_name: str
    count: int


class TrendPoint(BaseModel):
    """Daily inspection count for trend charts."""
    date: str  # ISO date string YYYY-MM-DD
    total: int
    pass_count: int
    rework_count: int
    reject_count: int
