"""Download operator-selected official source PDFs and index every text page."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.services.statutes import index_pdf

SOURCES = {
    "BNSS": "https://www.mha.gov.in/files/documents/250884_2english_01042024.pdf",
    "BNS": "https://www.mha.gov.in/files/documents/250883_english01042024.pdf",
    "BSA": "https://www.indiacode.nic.in/indiacode/bitstream/123456789/20063/1/aa202347.pdf",
    "IT Act": "https://www.indiacode.nic.in/bitstream/123456789/13116/1/it_act_2000_updated.pdf",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--act", choices=list(SOURCES), action="append")
    parser.add_argument("--directory", type=Path, default=Path("../data/law_sources"))
    parser.add_argument("--offline", action="store_true", help="Use previously reviewed PDFs in the directory")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    engine = make_engine(Settings().database_url)
    for act in args.act or SOURCES:
        target = args.directory / (act.replace(" ", "_") + ".pdf")
        manifest = target.with_suffix(".json")
        if not args.offline:
            with httpx.Client(timeout=60, follow_redirects=False) as client:
                with client.stream("GET", SOURCES[act]) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 30 * 1024 * 1024:
                            raise ValueError("Source exceeds the 30 MiB limit")
            if not content.startswith(b"%PDF-"):
                raise ValueError("Official source did not return a PDF; review its URL")
            target.write_bytes(content)
            manifest.write_text(json.dumps({"source_url": SOURCES[act], "sha256": sha256(content).hexdigest()}), encoding="utf-8")
        metadata = json.loads(manifest.read_text(encoding="utf-8"))
        if metadata["source_url"] != SOURCES[act] or metadata["sha256"] != sha256(target.read_bytes()).hexdigest():
            raise ValueError("Source manifest does not match the reviewed PDF; download again")
        with Session(engine) as db:
            pages = index_pdf(db, act, SOURCES[act], target.read_bytes())
        print(f"{act}: indexed {pages} original PDF pages")
    engine.dispose()


if __name__ == "__main__":
    main()
