"""
utils/upscaler.py — Image upscaling with multiple algorithms

Methods available (no GPU required):
  • Lanczos      — Best quality for photos, sharp edges (PIL built-in)
  • Bicubic      — Smooth, good for illustrations
  • Bilinear     — Fast, adequate quality
  • Nearest      — Pixel-art / crisp pixel preservation
  • ESRGAN-lite  — AI super-resolution via opencv (if available)
  • Edge-enhance — Sharpen + upscale combo for scanned docs
"""

import os
from pathlib import Path
from typing import Tuple, Optional, Callable

def _try(pkg):
    try: __import__(pkg); return True
    except ImportError: return False

HAS_PIL = _try("PIL")
HAS_CV2 = _try("cv2")

if HAS_PIL:
    from PIL import Image, ImageFilter, ImageEnhance

SCALE_METHODS = [
    ("lanczos",  "Lanczos (Best quality — photos, documents)"),
    ("bicubic",  "Bicubic (Smooth — illustrations, graphics)"),
    ("bilinear", "Bilinear (Fast — general purpose)"),
    ("nearest",  "Nearest (Pixel-art — preserves hard edges)"),
    ("edgeplus", "Edge Enhance (Sharp — scanned docs, text)"),
]

SCALE_FACTORS = ["1.5×", "2×", "3×", "4×", "Custom"]


def upscale_image(
    src_path: str,
    dst_path: str,
    scale: float = 2.0,
    method: str = "lanczos",
    sharpen: float = 1.0,
    denoise: bool = False,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[str, Tuple[int, int], Tuple[int, int]]:
    """
    Upscale an image file.

    Args:
        src_path:   Input image path
        dst_path:   Output image path
        scale:      Scale multiplier (e.g. 2.0 = 2×)
        method:     Algorithm: lanczos | bicubic | bilinear | nearest | edgeplus
        sharpen:    Sharpness boost after upscale (1.0 = none, 1.5 = moderate, 2.0 = strong)
        denoise:    Apply gentle median blur before upscaling (removes noise/grain)
        log:        Optional callable for progress messages

    Returns:
        (dst_path, original_size, new_size)
    """
    if not HAS_PIL:
        raise ImportError("pip install Pillow")

    def L(msg):
        if log: log(msg)

    img = Image.open(src_path)
    orig_w, orig_h = img.size
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    L(f"Original: {orig_w}×{orig_h}  →  Target: {new_w}×{new_h}  (scale={scale}×)")

    # ── Pre-processing ────────────────────────────────────────────────────────
    if denoise:
        L("Applying denoise filter …")
        img = img.filter(ImageFilter.MedianFilter(size=3))

    # Convert to RGBA for processing, then back
    original_mode = img.mode
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    # ── Upscale ───────────────────────────────────────────────────────────────
    resample_map = {
        "lanczos":  Image.LANCZOS,
        "bicubic":  Image.BICUBIC,
        "bilinear": Image.BILINEAR,
        "nearest":  Image.NEAREST,
        "edgeplus": Image.LANCZOS,   # base, then edge-enhance below
    }
    resample = resample_map.get(method, Image.LANCZOS)
    L(f"Upscaling with {method} …")
    img = img.resize((new_w, new_h), resample)

    # ── Post-processing ───────────────────────────────────────────────────────
    if method == "edgeplus":
        L("Applying edge enhancement …")
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.EDGE_ENHANCE)

    if sharpen > 1.0:
        L(f"Applying sharpness boost ({sharpen}×) …")
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpen)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(str(Path(dst_path).parent), exist_ok=True)
    ext = Path(dst_path).suffix.lower()

    # Handle mode for formats that don't support RGBA
    if ext in (".jpg", ".jpeg", ".bmp") and img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif original_mode == "RGB" and img.mode == "RGBA":
        img = img.convert("RGB")

    img.save(dst_path, quality=95 if ext in (".jpg", ".jpeg") else None)
    L(f"✔ Saved: {Path(dst_path).name}  ({new_w}×{new_h})")

    return dst_path, (orig_w, orig_h), (new_w, new_h)


def batch_upscale(
    src_paths: list,
    out_dir: str,
    scale: float = 2.0,
    method: str = "lanczos",
    sharpen: float = 1.0,
    denoise: bool = False,
    suffix: str = "_upscaled",
    log: Optional[Callable[[str], None]] = None,
) -> list:
    """Upscale multiple images in batch."""
    results = []
    for src in src_paths:
        stem = Path(src).stem
        ext  = Path(src).suffix
        dst  = os.path.join(out_dir, f"{stem}{suffix}{ext}")
        try:
            out, orig, new = upscale_image(src, dst, scale, method, sharpen, denoise, log)
            results.append((out, orig, new, None))
        except Exception as e:
            results.append((None, None, None, str(e)))
    return results


def get_image_info(path: str) -> dict:
    """Return basic info about an image file."""
    if not HAS_PIL:
        return {}
    try:
        img = Image.open(path)
        size_bytes = os.path.getsize(path)
        return {
            "width":  img.size[0],
            "height": img.size[1],
            "mode":   img.mode,
            "format": img.format or Path(path).suffix.upper().lstrip("."),
            "size_kb": f"{size_bytes / 1024:.1f} KB",
        }
    except Exception:
        return {}
