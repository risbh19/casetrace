import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.extraction import extract
from app.services.ocr import recognize


@pytest.mark.skipif(os.environ.get("RUN_OCR_TESTS") != "1", reason="Requires Tesseract eng+hin and Poppler")
@pytest.mark.parametrize("extension,media", [("png", "image/png"), ("pdf", "application/pdf")])
def test_scanned_hindi_evidence_with_live_tesseract(extension, media):
    image = Path(__file__).parents[2] / f"data/synthetic/scanned-hi.{extension}"
    settings = Settings(jwt_secret="isolated-ocr-test-key-with-at-least-32-characters", environment="training")
    text, method = recognize(image.read_bytes(), media, settings)
    assert method == "ocr", text
    values = {(kind, value) for kind, value, _ in extract(text)}
    assert {("date", "2024-02-29"), ("account", "9000012345"), ("amount", "19500.22")} <= values, text
