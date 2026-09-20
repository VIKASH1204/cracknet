"""
utils/image_utils.py
=====================
Image utility functions used across the backend.

No Jupyter / notebook-only code anywhere in this file.
"""

import io
import logging
import os
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Supported MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/tiff",
    "image/webp",
}

# Maximum dimension to resize very large images before inference
MAX_SAFE_DIMENSION = 4096


def validate_image_bytes(data: bytes) -> bool:
    """
    Return True if the bytes appear to be a valid, openable image.
    Does NOT raise — caller decides error handling.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False


def load_image_from_bytes(data: bytes) -> Image.Image:
    """
    Safely open and return a PIL Image from raw bytes.
    Raises ValueError on failure.
    """
    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # Force full decode
        return img
    except Exception as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc


def safe_resize(img: Image.Image, max_dim: int = MAX_SAFE_DIMENSION) -> Image.Image:
    """
    If either dimension exceeds max_dim, scale down proportionally.
    Otherwise return the image unchanged.
    """
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    scale = max_dim / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    logger.debug("Resizing oversized image from %dx%d to %dx%d", w, h, new_w, new_h)
    return img.resize((new_w, new_h), Image.BILINEAR)


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """Convert a PIL image to raw bytes in the given format."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


def get_image_info(img: Image.Image) -> dict:
    """Return basic image metadata."""
    return {
        "width": img.width,
        "height": img.height,
        "mode": img.mode,
        "format": img.format,
    }
