"""
services/decision_service.py
=============================
Quality decision engine using authoritative CrackXNet decision logic.

The rule-based decision logic is:
  - Any Critical defect  → REJECT
  - No Critical but any High → REWORK
  - 3 or more Medium defects → REWORK
  - Otherwise → PASS

Source of truth:
    crackxnet.decide_board_status()
    crackxnet.decide_board_status_learned()
"""

import logging
from typing import Dict, List, Tuple
from ai.model.crackxnet import (
    decide_board_status as crackxnet_decide_board_status,
    decide_board_status_learned as crackxnet_decide_board_status_learned,
)

logger = logging.getLogger(__name__)


def make_decision(detections: List[Dict]) -> str:
    """
    Apply authoritative CrackXNet rule-based quality decision logic.

    Args:
        detections: List of defect dicts with severity information.

    Returns:
        "PASS" | "REWORK" | "REJECT"
    """
    if not detections:
        return "PASS"

    severity_levels = [
        (d.get("severity_level") or d.get("severity") or "Low").capitalize()
        for d in detections
    ]

    decision, reason, counts = crackxnet_decide_board_status(severity_levels)
    logger.debug("CrackXNet decision=%s (reason=%s)", decision, reason)
    return decision


def make_decision_with_details(detections: List[Dict]) -> Dict:
    """
    Returns full decision details including rule-based decision, reason, severity counts,
    and optional learned decision network prediction.
    """
    severity_levels = [
        (d.get("severity_level") or d.get("severity") or "Low").capitalize()
        for d in detections
    ]
    severity_scores = [float(d.get("severity_score", 0.0)) for d in detections]

    decision, reason, counts = crackxnet_decide_board_status(severity_levels)
    learned_dec, learned_probs = crackxnet_decide_board_status_learned(severity_scores, severity_levels)

    return {
        "decision": decision,
        "decision_reason": reason,
        "severity_counts": counts,
        "learned_decision": learned_dec,
        "learned_decision_probs": learned_probs,
    }
