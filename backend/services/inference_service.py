"""
services/inference_service.py
==============================
Singleton inference service.

The CrackXNet model is loaded EXACTLY ONCE when the FastAPI application
starts (via the lifespan event in main.py). All incoming inspection requests
share the same loaded model instance.

Public API:
    startup_load_model()    — call from lifespan startup
    shutdown_model()        — call from lifespan shutdown
    is_model_loaded()       — check status
    get_model_info()        — metadata dict
    run_inference(image_bytes, ...) → dict

No model loading happens inside request handlers.
"""

import logging
import os
from typing import Any, Dict, Optional

from PIL import Image
import io

from backend.config import get_settings
from ai.inference import load_model, predict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state — set during application startup
# ---------------------------------------------------------------------------
_model = None
_device: str = "cpu"
_weights_loaded: bool = False
_model_info: Dict[str, Any] = {}


async def startup_load_model() -> None:
    """
    Load the CrackXNet model at application startup.
    Called from the FastAPI lifespan context manager.
    """
    global _model, _device, _weights_loaded, _model_info

    settings = get_settings()
    settings.ensure_dirs()

    _device = settings.device
    logger.info("Selected device: %s", _device.upper())

    try:
        _model, _weights_loaded = load_model(
            model_path=settings.model_path,
            device=_device,
            confidence_thresh=settings.confidence_threshold,
            iou_thresh=settings.iou_threshold,
        )

        _model_info = {
            "model_name": "CrackXNet",
            "version": "1.0",
            "device": _device,
            "weights_loaded": _weights_loaded,
            "model_path": os.path.abspath(settings.model_path),
            "confidence_threshold": settings.confidence_threshold,
            "iou_threshold": settings.iou_threshold,
            "input_resolution": f"{settings.input_width}×{settings.input_height}",
            "num_classes": 6,
            "total_classes": 7,
            "class_names": [
                "open", "short", "mousebite",
                "spur", "spurious_copper", "pin_hole"
            ],
            "benchmark": {
                "dataset": "DeepPCB",
                "mAP50": "94.52%",
                "mAP50_95": "62.04%",
                "fps": "29.76",
                "gflops": "9.16",
            },
            "architecture": [
                "EfficientNet-B0 backbone",
                "CBAM attention (Channel + Spatial)",
                "Lightweight Transformer Encoder (2 layers)",
                "Dynamic Defect-Aware Feature Fusion (DDRM / AFFM)",
                "Feature Pyramid Network (FPN)",
                "Detection Head (Faster R-CNN style)",
                "Severity Head (DSI)",
                "Explainability Head (Learned Saliency + Post-hoc Grad-CAM)",
            ],
        }

        logger.info("CrackXNet inference service ready. weights_loaded=%s", _weights_loaded)

    except Exception as exc:  # noqa: BLE001
        logger.critical("CRITICAL: Could not initialise CrackXNet: %s", exc)
        _model = None
        _weights_loaded = False
        _model_info = {"error": str(exc)}


async def shutdown_model() -> None:
    """Release model resources at shutdown."""
    global _model
    _model = None
    logger.info("CrackXNet model released.")


def is_model_loaded() -> bool:
    """Return True if the model object is available (even with random weights)."""
    return _model is not None


def are_weights_loaded() -> bool:
    """Return True only if a real checkpoint was loaded successfully."""
    return _weights_loaded


def get_model_info() -> Dict[str, Any]:
    return _model_info


def get_device() -> str:
    return _device


def run_inference(
    image_bytes: bytes,
    confidence_thresh: Optional[float] = None,
    iou_thresh: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run CrackXNet inference on raw image bytes.

    Args:
        image_bytes:       Raw bytes of an uploaded image file.
        confidence_thresh: Override default confidence threshold.
        iou_thresh:        Override default NMS IoU threshold.

    Returns:
        dict from ai.inference.predict():
            "detections", "saliency_map", "processing_time_ms", "image_shape"

    Raises:
        RuntimeError: if the model is not loaded.
        ValueError: if the image cannot be decoded.
    """
    if _model is None:
        raise RuntimeError(
            "CrackXNet model is not loaded. "
            "Check MODEL_PATH and server logs for details."
        )

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc

    settings = get_settings()
    result = predict(
        model=_model,
        pil_image=pil_image,
        device=_device,
        confidence_thresh=confidence_thresh or settings.confidence_threshold,
        iou_thresh=iou_thresh or settings.iou_threshold,
    )

    return result, pil_image
