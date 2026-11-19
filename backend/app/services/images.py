"""Image helpers: shrink slide images before sending them to the vision model."""
from pathlib import Path

from PIL import Image


def shrink_image(path: Path, max_side: int) -> Path:
    """Return a smaller copy of the image (same folder) with its longest side at most max_side."""
    with Image.open(path) as img:
        if max(img.size) <= max_side:
            return path
        scale = max_side / max(img.size)
        small_size = (round(img.width * scale), round(img.height * scale))
        target = path.with_name(f"{path.stem}_{max_side}.png")
        img.convert("RGB").resize(small_size, Image.LANCZOS).save(target, optimize=True)
        return target
