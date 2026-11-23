from hashlib import sha256
from io import BytesIO

import pytest
from app.models import LawPage
from app.services.statutes import index_pdf
from conftest import bearer_for
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def statute_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 40 700 Td (94. Production of documents and search warrants. Original fictional statute text for ingestion verification. Officers must review the original source.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_full_pdf_ingestion_preserves_pages_provenance_and_is_repeatable(client):
    content = statute_pdf()
    source = "https://www.indiacode.nic.in/fixture.pdf"
    with Session(client.app.state.engine) as db:
        assert index_pdf(db, "BNSS", source, content) == 1
        assert index_pdf(db, "BNSS", source, content) == 1
        assert db.scalar(select(func.count()).select_from(LawPage)) == 1
        with pytest.raises(ValueError):
            index_pdf(db, "BNSS", source, b"invalid")
        assert db.scalar(select(func.count()).select_from(LawPage)) == 1
    answer = client.post("/api/law/ask", headers=bearer_for(client, "io"), json={"question": "BNSS 94"}).json()
    assert answer["passages"][0]["source_sha256"] == sha256(content).hexdigest()
    assert answer["passages"][0]["page"] == 1
    assert "Original fictional" in answer["passages"][0]["text"]
