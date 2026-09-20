"""
routes/history.py
==================
GET /api/history — Paginated, filterable inspection history.

Query parameters:
    page      (int, default 1)
    limit     (int, default 20, max 100)
    decision  (str: PASS | REWORK | REJECT)
    defect    (str: defect class name)
    severity  (str: LOW | MEDIUM | HIGH | CRITICAL)
    pcb_id    (str: partial match)
    date_from (str: ISO date YYYY-MM-DD)
    date_to   (str: ISO date YYYY-MM-DD)
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.database import query_inspections

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["History"])


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    decision: Optional[str] = Query(None, description="Filter by PASS | REWORK | REJECT"),
    defect: Optional[str] = Query(None, description="Filter by defect class name"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    pcb_id: Optional[str] = Query(None, description="Partial PCB ID match"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """
    Return paginated inspection history with optional filters.
    Seamlessly queries MongoDB or local file fallback.
    """
    total, items = await query_inspections(
        page=page,
        limit=limit,
        decision=decision,
        defect=defect,
        severity=severity,
        pcb_id=pcb_id,
        date_from=date_from,
        date_to=date_to,
    )

    # Ensure public URLs exist on items
    for item in items:
        if item.get("image_path") and not item.get("image_url"):
            item["image_url"] = f"/static/uploads/{os.path.basename(item['image_path'])}"
        if item.get("result_image_path") and not item.get("result_image_url"):
            item["result_image_url"] = f"/static/results/{os.path.basename(item['result_image_path'])}"
        if item.get("explainability_path") and not item.get("explainability_url"):
            item["explainability_url"] = f"/static/results/{os.path.basename(item['explainability_path'])}"

    return JSONResponse(content={
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
    })


@router.get("/history/export")
async def export_history_csv(
    decision: Optional[str] = Query(None),
    defect: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    pcb_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """
    Export inspection history as a downloadable CSV audit report.
    """
    import csv
    import io
    from fastapi.responses import Response
    from backend.database import get_all_inspections_for_export

    records = await get_all_inspections_for_export(
        decision=decision,
        defect=defect,
        severity=severity,
        pcb_id=pcb_id,
        date_from=date_from,
        date_to=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Inspection ID",
        "PCB ID",
        "Timestamp",
        "Quality Decision",
        "Defect Count",
        "Highest Severity",
        "Processing Time (ms)",
        "Defects Itemized",
    ])

    for r in records:
        defects = r.get("defects", [])
        defect_summary = "; ".join([
            f"{d.get('class_name', '')} ({((d.get('confidence', 0))*100):.1f}%, {d.get('severity', '')})"
            for d in defects
        ])
        writer.writerow([
            r.get("inspection_id") or r.get("_id", ""),
            r.get("pcb_id", ""),
            r.get("timestamp", ""),
            r.get("decision", ""),
            r.get("defect_count", len(defects)),
            r.get("highest_severity", ""),
            r.get("processing_time_ms", ""),
            defect_summary,
        ])

    csv_data = output.getvalue()
    filename = f"crackxnet_inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

