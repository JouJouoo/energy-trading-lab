from __future__ import annotations

import base64
import os
import re
from typing import Dict, Tuple


TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".tex", ".csv"}


class DocumentExtractionError(ValueError):
    pass


def extract_document_from_base64(filename: str, data_base64: str) -> Dict[str, object]:
    raw = base64.b64decode(data_base64)
    text, method = extract_document_text(filename, raw)
    clean = normalize_extracted_text(text)
    if len(clean) < 80:
        raise DocumentExtractionError(
            "Document text extraction produced too little text. Please upload a text/Markdown file, "
            "or install PDF support with `python -m pip install pypdf` for searchable PDFs."
        )
    return {
        "filename": filename,
        "chars": len(clean),
        "method": method,
        "text": clean,
    }


def extract_document_text(filename: str, raw: bytes) -> Tuple[str, str]:
    ext = os.path.splitext(filename.lower())[1]
    if ext in TEXT_EXTENSIONS:
        return decode_text(raw), "text"
    if ext == ".pdf":
        return extract_pdf_text(raw), "pdf"
    try:
        return decode_text(raw), "text-fallback"
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("Unsupported document type: %s" % (ext or "unknown")) from exc


def decode_text(raw: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", raw, 0, 1, "unable to decode document")


def extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise DocumentExtractionError(
            "PDF upload is wired, but `pypdf` is not installed in this environment. "
            "Run `source .venv/bin/activate && python -m pip install pypdf`, "
            "or upload a Markdown/text export of the paper."
        ) from exc

    import io

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for index, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n\n".join(pages)
    if not text.strip():
        raise DocumentExtractionError(
            "No searchable text was found in this PDF. If it is a scanned paper, run OCR first or upload text/Markdown."
        )
    return text


def normalize_extracted_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

