"""
services/severity_service.py
=============================
Severity scoring for detected PCB defects using authoritative CrackXNet logic.

Delegates directly to:
    crackxnet.compute_severity()
    crackxnet.severity_level()
"""

from typing import Dict, List, Optional
from ai.model.crackxnet import (
    compute_severity as crackxnet_compute_severity,
    severity_level as crackxnet_severity_level,
    SEVERITY_BINS,
    RISK_WEIGHT,
)


def compute_severity(
    class_name: str,
    bbox: Dict,
    confidence: float = 0.5,
    image_hw: tuple = (640, 640),
) -> Dict:
    """
    Compute severity for a single detected defect using CrackXNet's transparent formula.

    Returns:
        {
            "severity_score": float (0-100),
            "severity_level": str ("Low" | "Medium" | "High" | "Critical"),
            "severity":       str ("LOW" | "MEDIUM" | "HIGH" | "CRITICAL"),
        }
    """
    box_xyxy = [bbox.get("x1", 0), bbox.get("y1", 0), bbox.get("x2", 0), bbox.get("y2", 0)]
    dsi, level = crackxnet_compute_severity(class_name, box_xyxy, confidence, image_hw)
    return {
        "severity_score": round(dsi, 1),
        "severity_level": level,
        "severity": level.upper(),
    }


def annotate_detections_with_severity(detections: List[Dict], image_hw: tuple = (640, 640)) -> List[Dict]:
    """
    Ensures every detection dict contains standard severity attributes.
    Preserves existing severity calculated by inspect_board() or calculates if missing.
    """
    enriched = []
    for det in detections:
        cls_name = det.get("class_name") or det.get("class") or "unknown"
        conf = float(det.get("confidence", 0.5))

        if "severity_score" in det and "severity_level" in det:
            score = det["severity_score"]
            level = det["severity_level"]
        else:
            bbox = det.get("bbox") or {}
            box_xyxy = det.get("box") or [bbox.get("x1", 0), bbox.get("y1", 0), bbox.get("x2", 0), bbox.get("y2", 0)]
            score, level = crackxnet_compute_severity(cls_name, box_xyxy, conf, image_hw)

        enriched.append({
            **det,
            "class_name": cls_name,
            "class": cls_name,
            "confidence": conf,
            "severity_score": round(score, 1),
            "severity_level": level,
            "severity": level.upper(),
            "learned_severity_score": det.get("learned_severity_score"),
        })
    return enriched


def highest_severity(detections: List[Dict]) -> str:
    """Return the highest severity level across all detections (e.g. CRITICAL, HIGH, etc.)."""
    order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    if not detections:
        return "LOW"
    return max(
        ((det.get("severity") or det.get("severity_level") or "LOW").upper() for det in detections),
        key=lambda lvl: order.get(lvl, 0),
    )
