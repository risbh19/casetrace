import re
import subprocess
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError:
    PdfReader = None

    class PdfReadError(Exception):
        pass

MAX_BYTES = 8 * 1024 * 1024
MAX_TEXT = 50_000
MAX_PAGES = 8
MAX_PIXELS = 18_000_000
MEDIA = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def classify(filename: str, content: bytes) -> str:
    media_type = MEDIA.get(Path(filename).suffix.lower())
    if media_type is None:
        raise ValueError("Choose a UTF-8 TXT/CSV, PDF, PNG, or JPEG file")
    signatures = {
        "application/pdf": b"%PDF-",
        "image/png": b"\x89PNG\r\n\x1a\n",
        "image/jpeg": b"\xff\xd8\xff",
    }
    signature = signatures.get(media_type)
    if signature and not content.startswith(signature):
        raise ValueError("File extension does not match the file contents")
    if not signature and b"\x00" in content:
        raise ValueError("Text files must be UTF-8 without binary content")
    return media_type


def scan(path: Path, settings: Settings, budget: float) -> str:
    output = subprocess.run(
        [settings.tesseract_binary, str(path), "stdout", "-l", "eng+hin", "--psm", "3"],
        check=True, capture_output=True, timeout=max(0.1, budget),
    )
    return output.stdout.decode("utf-8", errors="replace")


def recognize(content: bytes, media_type: str, settings: Settings) -> tuple[str, str]:
    if media_type.startswith("text/"):
        return content.decode("utf-8-sig").strip()[:MAX_TEXT], "text"
    try:
        if media_type == "application/pdf" and PdfReader is None:
            return "", "ocr-unavailable"
        if media_type == "application/pdf":
            pdf = PdfReader(BytesIO(content))
            if pdf.is_encrypted or len(pdf.pages) > MAX_PAGES:
                raise ValueError(f"Use unencrypted PDFs with at most {MAX_PAGES} pages")
            if not len(pdf.pages):
                raise ValueError("The PDF has no pages")
            pages = [page.extract_text() or "" for page in pdf.pages]
        else:
            pages = [""]
        blank = [
            i for i, text in enumerate(pages)
            if not re.search(r"[A-Za-z0-9\u0900-\u097F]{2}", text)
        ]
        if not blank:
            return "\n".join(pages).strip()[:MAX_TEXT], "pdf-text"
        with TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "evidence.pdf"
            expires = monotonic() + 30
            if media_type == "application/pdf":
                source.write_bytes(content)
                for index in blank:
                    remaining = expires - monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired("OCR", 30)
                    target = base / f"page-{index + 1}"
                    subprocess.run(
                        [settings.pdf_image_binary, "-f", str(index + 1), "-l", str(index + 1),
                         "-scale-to", "2200", "-png", "-singlefile", str(source), str(target)],
                        capture_output=True, check=True, timeout=remaining,
                    )
                    pages[index] = scan(target.with_suffix(".png"), settings, expires - monotonic())
            else:
                with Image.open(BytesIO(content)) as image:
                    if image.width * image.height > MAX_PIXELS:
                        raise ValueError("Image exceeds the pixel limit")
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.thumbnail((2600, 2600))
                    target = base / "evidence.png"
                    image.save(target)
                pages[0] = scan(target, settings, expires - monotonic())
        text = "\n".join(pages).strip()[:MAX_TEXT]
        return text, "ocr" if text else "no-text"
    except (PdfReadError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValueError("The PDF or image could not be opened") from None
    except (FileNotFoundError, subprocess.SubprocessError):
        return "\n".join(pages).strip()[:MAX_TEXT], "ocr-unavailable"
