"""
routes/inspection.py
=====================
Inspection endpoints:
    POST /api/inspection/upload   — Upload a PCB image, run CrackXNet inference
    POST /api/inspection/camera   — Same but from a browser camera capture
    GET  /api/inspection/{id}     — Retrieve a stored inspection result
"""

import io
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import save_inspection_record, get_inspection_record
from backend.services.inference_service import run_inference, is_model_loaded
from backend.services.severity_service import annotate_detections_with_severity, highest_severity
from backend.services.decision_service import make_decision
from backend.services.explainability_service import (
    generate_annotated_image,
    generate_explainability_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inspection", tags=["Inspection"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_upload(file: UploadFile, max_bytes: int, allowed_exts: set) -> None:
    """Raise HTTP 400 for invalid uploads."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(allowed_exts)}",
        )
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file.size / 1_048_576:.1f} MB). "
                   f"Maximum allowed: {max_bytes // 1_048_576} MB.",
        )


async def _run_full_pipeline(image_bytes: bytes, pcb_id: str, inspection_id: str) -> dict:
    """
    Core inspection pipeline — shared by /upload and /camera endpoints.

    Returns a complete result dict ready for JSON response and DB storage.
    Raises HTTPException on inference failure.
    """
    settings = get_settings()

    # ── 1. Inference ─────────────────────────────────────────────────────────
    try:
        inference_result, pil_image = run_inference(image_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected inference error")
        raise HTTPException(status_code=500, detail="Internal inference error. Check server logs.") from exc

    raw_detections = inference_result["detections"]
    saliency_map   = inference_result["saliency_map"]
    proc_time_ms   = inference_result["processing_time_ms"]

    # ── 2. Severity enrichment ────────────────────────────────────────────────
    detections = annotate_detections_with_severity(raw_detections)

    # ── 3. Quality decision ───────────────────────────────────────────────────
    decision = make_decision(detections)

    # ── 4. Save original image ────────────────────────────────────────────────
    upload_path: Optional[str] = None
    try:
        img_filename = f"upload_{inspection_id}.png"
        img_filepath = os.path.join(settings.upload_dir, img_filename)
        pil_image.save(img_filepath, format="PNG")
        upload_path = img_filepath
    except Exception as exc:
        logger.warning("Could not save uploaded image: %s", exc)

    # ── 5. Generate annotated result image ────────────────────────────────────
    result_image_path = generate_annotated_image(
        pil_image=pil_image,
        detections=detections,
        results_dir=settings.results_dir,
        inspection_id=inspection_id,
    )

    # ── 6. Generate explainability overlay ───────────────────────────────────
    explain_path = generate_explainability_image(
        pil_image=pil_image,
        saliency_map=saliency_map,
        results_dir=settings.results_dir,
        inspection_id=inspection_id,
    )

    # ── 7. Build response dict ────────────────────────────────────────────────
    timestamp = datetime.now(timezone.utc)

    result = {
        "inspection_id":    inspection_id,
        "pcb_id":           pcb_id,
        "board_id":         pcb_id,
        "timestamp":        timestamp.isoformat(),
        "processing_time_ms": proc_time_ms,
        "defect_count":     len(detections),
        "num_defects":      len(detections),
        "defects":          detections,
        "decision":         decision,
        "decision_reason":  inference_result.get("decision_reason"),
        "learned_decision": inference_result.get("learned_decision"),
        "learned_decision_probs": inference_result.get("learned_decision_probs"),
        "severity_counts":  inference_result.get("severity_counts"),
        "highest_severity": highest_severity(detections),
        "image_url":        f"/static/uploads/{os.path.basename(upload_path)}" if upload_path else None,
        "result_image_url": f"/static/results/{os.path.basename(result_image_path)}" if result_image_path else None,
        "explainability_url": f"/static/results/{os.path.basename(explain_path)}" if explain_path else None,
    }

    # ── 8. Persist to storage (MongoDB or local fallback) ─────────────────────
    doc = {
        "_id":               inspection_id,
        "pcb_id":            pcb_id,
        "board_id":         pcb_id,
        "timestamp":         timestamp.isoformat(),
        "image_path":        upload_path,
        "result_image_path": result_image_path,
        "explainability_path": explain_path,
        "defect_count":      len(detections),
        "num_defects":      len(detections),
        "defects":           detections,
        "decision":          decision,
        "decision_reason":  inference_result.get("decision_reason"),
        "learned_decision": inference_result.get("learned_decision"),
        "learned_decision_probs": inference_result.get("learned_decision_probs"),
        "severity_counts":  inference_result.get("severity_counts"),
        "highest_severity":  highest_severity(detections),
        "processing_time_ms": proc_time_ms,
    }
    persisted = await save_inspection_record(doc)
    result["persisted"] = persisted

    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_inspection(
    file: UploadFile = File(..., description="PCB image file (JPG / PNG)"),
    pcb_id: Optional[str] = Form(None, description="Optional PCB identifier"),
    operator_id: Optional[str] = Form(None),
    line_id: Optional[str] = Form(None),
):
    """
    Upload a PCB image and run CrackXNet defect inspection.

    Accepts multipart/form-data with an image file.
    Returns full inspection result including detected defects, severity,
    and PASS / REWORK / REJECT decision.
    """
    if not is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="CrackXNet model is not available. Check server logs.",
        )

    settings = get_settings()
    _validate_upload(file, settings.max_upload_size_bytes, settings.allowed_extensions)

    image_bytes = await file.read()
    inspection_id = str(uuid.uuid4())
    pcb_id = pcb_id or f"PCB-{inspection_id[:8].upper()}"

    result = await _run_full_pipeline(image_bytes, pcb_id, inspection_id)
    return JSONResponse(content=result)


@router.post("/camera")
async def camera_inspection(
    file: UploadFile = File(..., description="Frame captured from browser camera"),
    pcb_id: Optional[str] = Form(None),
    operator_id: Optional[str] = Form(None),
):
    """
    Submit a camera-captured frame for CrackXNet inspection.
    """
    if not is_model_loaded():
        raise HTTPException(
            status_code=503,
            detail="CrackXNet model is not available. Check server logs.",
        )

    settings = get_settings()
    _validate_upload(file, settings.max_upload_size_bytes, settings.allowed_extensions)

    image_bytes = await file.read()
    inspection_id = str(uuid.uuid4())
    pcb_id = pcb_id or f"CAM-{inspection_id[:8].upper()}"

    result = await _run_full_pipeline(image_bytes, pcb_id, inspection_id)
    return JSONResponse(content=result)


@router.get("/{inspection_id}")
async def get_inspection(inspection_id: str):
    """
    Retrieve a stored inspection result by its ID.
    """
    doc = await get_inspection_record(inspection_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")

    # Rebuild public URLs
    if doc.get("image_path") and not doc.get("image_url"):
        doc["image_url"] = f"/static/uploads/{os.path.basename(doc['image_path'])}"
    if doc.get("result_image_path") and not doc.get("result_image_url"):
        doc["result_image_url"] = f"/static/results/{os.path.basename(doc['result_image_path'])}"
    if doc.get("explainability_path") and not doc.get("explainability_url"):
        doc["explainability_url"] = f"/static/results/{os.path.basename(doc['explainability_path'])}"

    return JSONResponse(content=doc)
