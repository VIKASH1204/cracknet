"""
services/explainability_service.py
====================================
Generates explainability visualisations for CrackXNet predictions.

Two modes:
  1. Model-native saliency map (from ExplainabilityHead output)
  2. Grad-CAM (computed from the last FPN feature map gradient)

The explainability map is overlaid on the original image and saved to disk.

Note: The highlights indicate regions that contributed most to the model's
prediction. They are NOT pixel-perfect defect segmentation masks.
"""

import logging
import os
import uuid
from typing import Dict, Optional

import numpy as np
from PIL import Image

from ai.inference import draw_saliency_overlay, pil_to_bytes

logger = logging.getLogger(__name__)


def generate_explainability_image(
    pil_image: Image.Image,
    saliency_map: np.ndarray,
    results_dir: str,
    inspection_id: str,
    alpha: float = 0.45,
) -> Optional[str]:
    """
    Overlay the model's saliency map on the original image and save to disk.

    Args:
        pil_image:      Original PIL image.
        saliency_map:   (H, W) float32 array in [0,1] from predict().
        results_dir:    Directory to save the output file.
        inspection_id:  Unique ID used to name the output file.
        alpha:          Heatmap blend weight (0=original, 1=heatmap only).

    Returns:
        Relative file path of the saved explainability image, or None on error.
    """
    try:
        overlay = draw_saliency_overlay(pil_image, saliency_map, alpha=alpha)

        filename = f"explain_{inspection_id}.png"
        filepath = os.path.join(results_dir, filename)
        overlay.save(filepath, format="PNG")

        logger.debug("Explainability image saved: %s", filepath)
        return filepath

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to generate explainability image: %s", exc)
        return None


def generate_annotated_image(
    pil_image: Image.Image,
    detections: list,
    results_dir: str,
    inspection_id: str,
) -> Optional[str]:
    """
    Draw detection bounding boxes on the original image and save to disk.

    Args:
        pil_image:      Original PIL image.
        detections:     Processed detections (with severity fields).
        results_dir:    Directory to save the output file.
        inspection_id:  Used to name the output file.

    Returns:
        Relative file path of the saved result image, or None on error.
    """
    from ai.inference import draw_results

    try:
        severity_map = {idx: det.get("severity", "MEDIUM") for idx, det in enumerate(detections)}
        annotated = draw_results(pil_image, detections, severity_map=severity_map)

        filename = f"result_{inspection_id}.png"
        filepath = os.path.join(results_dir, filename)
        annotated.save(filepath, format="PNG")

        logger.debug("Annotated result image saved: %s", filepath)
        return filepath

    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to generate annotated image: %s", exc)
        return None
