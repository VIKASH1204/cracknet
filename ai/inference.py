"""
inference.py
============
CrackXNet Inference Interface.

Public API:
    load_model(model_path, device, ...) → Tuple[CrackXNet, bool]
    preprocess_image(pil_image)         → torch.Tensor
    predict(model, pil_image, ...)      → Dict (InferenceResult)
    draw_results(pil_image, detections) → PIL.Image
    draw_saliency_overlay(pil_image, saliency_map) → PIL.Image
    pil_to_bytes(pil_image)             → bytes
"""

import io
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont

from ai.model import crackxnet
from ai.model.crackxnet import (
    CLASS_NAMES,
    NUM_CLASSES,
    CrackXNetDetector as CrackXNet,
    inspect_board,
    preprocess_image as model_preprocess,
)

logger = logging.getLogger(__name__)

# Bounding-box colours per defect class
CLASS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "open":            (231, 76,  60),
    "short":           (230, 126, 34),
    "mousebite":       (241, 196, 15),
    "spur":            (46,  204, 113),
    "spurious_copper": (52,  152, 219),
    "pin_hole":        (155, 89,  182),
}
DEFAULT_COLOR = (255, 255, 255)

SEVERITY_COLORS: Dict[str, str] = {
    "LOW":      "#27ae60",
    "MEDIUM":   "#f39c12",
    "HIGH":     "#e67e22",
    "CRITICAL": "#c0392b",
}


def load_model(
    model_path: Optional[str] = None,
    device: str = "cpu",
    confidence_thresh: float = 0.50,
    iou_thresh: float = 0.45,
) -> Tuple[CrackXNet, bool]:
    """
    Load CrackXNet model from checkpoint.

    Returns:
        (model, weights_loaded): CrackXNet in eval mode and whether checkpoint loaded.
    """
    try:
        dev = torch.device(device if torch.cuda.is_available() and "cuda" in device else "cpu")
        model = crackxnet.load_model(weights_path=model_path, device=dev)
        logger.info("CrackXNet loaded successfully on device: %s", dev)
        return model, True
    except Exception as exc:
        logger.error("Error loading CrackXNet from %s: %s", model_path, exc)
        # Fallback to initialize architecture
        model = crackxnet.build_model(num_classes=NUM_CLASSES, pretrained_backbone=False).to(device)
        model.eval()
        return model, False


def preprocess_image(pil_img: Image.Image, img_size: int = 640) -> torch.Tensor:
    """Preprocess PIL image to normalized tensor (C, H, W) for CrackXNet."""
    return model_preprocess(pil_img, img_size=img_size)


def predict(
    model: CrackXNet,
    pil_image: Image.Image,
    device: str = "cpu",
    confidence_thresh: Optional[float] = None,
    iou_thresh: Optional[float] = None,
) -> Dict:
    """
    Run full CrackXNet inference pipeline on a PIL image.

    Returns:
        Dict with detections, saliency_map, decision, severity_counts, processing_time_ms.
    """
    t_start = time.perf_counter()
    orig_w, orig_h = pil_image.size
    thresh = confidence_thresh if confidence_thresh is not None else 0.50

    # 1. Preprocess
    tensor = preprocess_image(pil_image, img_size=640)

    # 2. CrackXNet inspect_board
    report = inspect_board(tensor, score_thresh=thresh, with_gradcam=True)

    # 3. Coordinate scaling (from 640×640 to original image dimensions)
    scale_x = orig_w / 640.0
    scale_y = orig_h / 640.0

    enriched_detections = []
    combined_cam = np.zeros((640, 640), dtype=np.float32)

    for i, d in enumerate(report["defects"]):
        box_640 = d["box"]
        x1 = max(0, int(round(box_640[0] * scale_x)))
        y1 = max(0, int(round(box_640[1] * scale_y)))
        x2 = min(orig_w, int(round(box_640[2] * scale_x)))
        y2 = min(orig_h, int(round(box_640[3] * scale_y)))

        # Accumulate Grad-CAM if available
        if d.get("heatmap") is not None:
            combined_cam = np.maximum(combined_cam, d["heatmap"])

        cls_name = d["class"]
        sev_level = d["severity_level"]
        sev_score = d["severity_score"]

        enriched_detections.append({
            "class_id": i + 1,
            "class": cls_name,
            "class_name": cls_name,
            "confidence": float(d["confidence"]),
            "box": [x1, y1, x2, y2],
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "severity_score": float(sev_score),
            "severity_level": sev_level,
            "severity": sev_level.upper(),
            "learned_severity_score": d.get("learned_severity_score"),
        })

    # 4. Saliency map: use learned saliency if available, augmented with Grad-CAM
    if report.get("learned_saliency") is not None:
        sal_base = report["learned_saliency"]
        if combined_cam.max() > 0:
            sal_final = np.maximum(sal_base, combined_cam)
        else:
            sal_final = sal_base
    elif combined_cam.max() > 0:
        sal_final = combined_cam
    else:
        sal_final = np.zeros((640, 640), dtype=np.float32)

    # Upscale saliency to original image size
    sal_resized = cv2.resize(sal_final, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)

    t_end = time.perf_counter()
    processing_ms = round((t_end - t_start) * 1000, 2)

    return {
        "detections": enriched_detections,
        "saliency_map": sal_resized,
        "decision": report["decision"],
        "decision_reason": report["decision_reason"],
        "learned_decision": report.get("learned_decision"),
        "learned_decision_probs": report.get("learned_decision_probs"),
        "severity_counts": report["severity_counts"],
        "processing_time_ms": processing_ms,
        "image_shape": (orig_h, orig_w),
    }


def draw_results(
    pil_image: Image.Image,
    detections: List[Dict],
    severity_map: Optional[Dict[str, str]] = None,
) -> Image.Image:
    """Draw bounding boxes, class labels, and severity tags on PCB image."""
    img = pil_image.convert("RGB").copy()
    draw = ImageDraw.Draw(img, "RGBA")

    try:
        font = ImageFont.truetype("arial.ttf", size=14)
        font_small = ImageFont.truetype("arial.ttf", size=11)
    except (IOError, OSError):
        font = ImageFont.load_default()
        font_small = font

    if severity_map is None:
        severity_map = {}

    for idx, det in enumerate(detections):
        cls_name = det.get("class_name") or det.get("class") or "defect"
        confidence = det.get("confidence", 0.0)
        bbox = det.get("bbox") or {}
        if bbox:
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
        elif "box" in det:
            x1, y1, x2, y2 = [int(v) for v in det["box"]]
        else:
            continue

        sev_level = (det.get("severity") or det.get("severity_level") or "MEDIUM").upper()
        box_width = {"LOW": 2, "MEDIUM": 3, "HIGH": 4, "CRITICAL": 5}.get(sev_level, 3)

        color_rgb = CLASS_COLORS.get(cls_name, DEFAULT_COLOR)
        color_rgba = (*color_rgb, 220)

        # Semi-transparent fill and bounding box outline
        draw.rectangle([x1, y1, x2, y2], fill=(*color_rgb, 40), outline=color_rgba, width=box_width)

        # Label background
        label = f"{cls_name.upper().replace('_', ' ')} {confidence * 100:.1f}%"
        try:
            bbox_text = font.getbbox(label)
            text_w = bbox_text[2] - bbox_text[0]
            text_h = bbox_text[3] - bbox_text[1]
        except AttributeError:
            text_w, text_h = len(label) * 7, 14

        label_x1 = x1
        label_y1 = max(0, y1 - text_h - 6)
        label_x2 = x1 + text_w + 8
        label_y2 = y1

        draw.rectangle([label_x1, label_y1, label_x2, label_y2], fill=(*color_rgb, 220))
        draw.text((label_x1 + 4, label_y1 + 2), label, fill=(255, 255, 255), font=font)

        # Severity tag badge
        badge_label = f"{sev_level} ({det.get('severity_score', 0):.0f})"
        badge_x = max(x1, x2 - 95)
        badge_y = max(y1, y2 - 20)
        draw.rectangle([badge_x, badge_y, x2, y2], fill=(*color_rgb, 180))
        draw.text((badge_x + 4, badge_y + 2), badge_label, fill=(255, 255, 255), font=font_small)

    return img


def draw_saliency_overlay(
    pil_image: Image.Image,
    saliency_map: np.ndarray,
    alpha: float = 0.5,
    colormap: str = "jet",
) -> Image.Image:
    """Overlay false-colour saliency/attention heatmap on original PCB image."""
    img_np = np.array(pil_image.convert("RGB"))
    H, W = img_np.shape[:2]

    # Resize if needed
    if saliency_map.shape[:2] != (H, W):
        sal_resized = cv2.resize(saliency_map, (W, H), interpolation=cv2.INTER_LINEAR)
    else:
        sal_resized = saliency_map

    sal_norm = (sal_resized - sal_resized.min()) / (sal_resized.max() - sal_resized.min() + 1e-8)
    sal_uint8 = np.uint8(sal_norm * 255)

    cmap_id = cv2.COLORMAP_JET if colormap == "jet" else cv2.COLORMAP_HOT
    heatmap_bgr = cv2.applyColorMap(sal_uint8, cmap_id)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    blended = cv2.addWeighted(img_np, 1.0 - alpha, heatmap_rgb, alpha, 0)
    return Image.fromarray(blended)


def pil_to_bytes(pil_image: Image.Image, fmt: str = "PNG") -> bytes:
    """Convert PIL image to byte stream."""
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()
