"""
CrackXNet AI package.

Entry point for model loading and inference. Import from here in
all backend services so there is exactly one integration boundary.
"""
from .inference import load_model, predict, preprocess_image, draw_results  # noqa: F401
