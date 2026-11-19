"""Slide extraction: text and speaker notes (python-pptx / PyMuPDF) and PNG rendering.

- .pptx: text via python-pptx; images via PowerPoint itself (Windows, COM).
- .pdf:  text and images via PyMuPDF (works on any OS).
"""
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("meetingiq.slides")

RENDER_WIDTH, RENDER_HEIGHT = 1920, 1080


@dataclass
class SlideData:
    slide_number: int
    title: str | None
    body_text: str
    speaker_notes: str
    image_path: Path | None  # absolute path to the PNG, or None if rendering failed


def _extract_pptx_text(path: Path) -> list[dict]:
    from pptx import Presentation

    presentation = Presentation(str(path))
    slides = []
    for number, slide in enumerate(presentation.slides, start=1):
        title = None
        if slide.shapes.title is not None and slide.shapes.title.has_text_frame:
            title = slide.shapes.title.text.strip() or None

        body = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text.strip()
                if text and text != title:
                    body.append(text)

        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        slides.append({
            "slide_number": number,
            "title": title,
            "body_text": "\n".join(body),
            "speaker_notes": notes,
        })
    return slides


def _render_pptx_with_powerpoint(path: Path, out_dir: Path) -> list[Path]:
    """Export every slide as PNG using Microsoft PowerPoint (Windows only)."""
    import pythoncom
    import win32com.client

    out_dir.mkdir(parents=True, exist_ok=True)
    pythoncom.CoInitialize()  # required because this runs in a worker thread
    powerpoint = None
    presentation = None
    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        presentation = powerpoint.Presentations.Open(
            str(path.resolve()), ReadOnly=True, Untitled=True, WithWindow=False
        )
        images = []
        for number in range(1, presentation.Slides.Count + 1):
            out = (out_dir / f"slide_{number}.png").resolve()
            presentation.Slides(number).Export(str(out), "PNG", RENDER_WIDTH, RENDER_HEIGHT)
            images.append(out)
        return images
    finally:
        if presentation is not None:
            presentation.Close()
        if powerpoint is not None:
            powerpoint.Quit()
        pythoncom.CoUninitialize()


def _extract_pdf(path: Path, out_dir: Path) -> list[SlideData]:
    import fitz  # PyMuPDF

    out_dir.mkdir(parents=True, exist_ok=True)
    slides = []
    with fitz.open(str(path)) as doc:
        for index, page in enumerate(doc, start=1):
            lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
            image = out_dir / f"slide_{index}.png"
            page.get_pixmap(dpi=150).save(str(image))
            slides.append(SlideData(
                slide_number=index,
                title=lines[0] if lines else None,
                body_text="\n".join(lines[1:]) if len(lines) > 1 else "",
                speaker_notes="",
                image_path=image.resolve(),
            ))
    return slides


def extract(path: Path, out_dir: Path) -> list[SlideData]:
    """Extract all slides of a presentation and render them to PNG where possible."""
    if path.suffix.lower() == ".pdf":
        return _extract_pdf(path, out_dir)

    text_slides = _extract_pptx_text(path)
    try:
        images = _render_pptx_with_powerpoint(path, out_dir)
    except Exception as exc:  # no PowerPoint installed, COM error, etc.
        logger.warning("Could not render %s with PowerPoint, continuing without images: %s", path.name, exc)
        images = []

    result = []
    for item in text_slides:
        number = item["slide_number"]
        image = images[number - 1] if number <= len(images) else None
        result.append(SlideData(
            slide_number=number,
            title=item["title"],
            body_text=item["body_text"],
            speaker_notes=item["speaker_notes"],
            image_path=image,
        ))
    return result
