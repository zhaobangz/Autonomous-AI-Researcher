"""
Robust PDF parser with size, SSRF, and content type protection.
"""
import io
import logging
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel
from pypdf import PdfReader

try:
    from pdfminer.high_level import extract_text as _pdfminer_extract
except ImportError:
    _pdfminer_extract = None

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 50 * 1024 * 1024
DOWNLOAD_TIMEOUT = 30
CHUNK_SIZE = 64 * 1024


class ParsedPaper(BaseModel):
    text: str
    chunks: List[str]
    metadata: Dict[str, Any]


def _validate_arxiv_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Blocked SSRF (scheme must be https): {url}")
    if parsed.hostname != "arxiv.org":
        raise ValueError(f"Blocked SSRF (host must be arxiv.org): {url}")
    if not parsed.path.startswith("/pdf/"):
        raise ValueError(f"Blocked SSRF (path must start with /pdf/): {url}")


def _stream_arxiv_pdf(url: str) -> bytes:
    _validate_arxiv_url(url)
    with httpx.stream(
        "GET",
        url,
        timeout=DOWNLOAD_TIMEOUT,
        follow_redirects=False,
    ) as response:
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type:
            raise ValueError(f"Response is not a PDF (content-type: {content_type!r})")

        buf = bytearray()
        for chunk in response.iter_bytes(CHUNK_SIZE):
            buf.extend(chunk)
            if len(buf) > MAX_PDF_BYTES:
                raise ValueError("PDF exceeds 50MB size limit")
        return bytes(buf)


def _validate_local_pdf_path(path_value: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Local PDF path does not exist: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Local file parsing is restricted to .pdf files")
    if path.stat().st_size > MAX_PDF_BYTES:
        raise ValueError("PDF exceeds 50MB size limit")
    return path


def parse_pdf(url_or_path: str, *, allow_local_file: bool = False) -> ParsedPaper:
    try:
        parsed = urlparse(url_or_path)
        if parsed.scheme in {"http", "https"}:
            f = io.BytesIO(_stream_arxiv_pdf(url_or_path))
        else:
            if not allow_local_file:
                raise ValueError("Local PDF paths are disabled for agent tool calls")
            local_path = _validate_local_pdf_path(url_or_path)
            f = local_path.open("rb")
            if f.read(5) != b"%PDF-":
                raise ValueError("Local file is not a PDF")
            f.seek(0)

        try:
            reader = PdfReader(f)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            if not text.strip():
                if _pdfminer_extract is None:
                    logger.warning("pdfminer not installed, skipping fallback extraction")
                else:
                    f.seek(0)
                    text = _pdfminer_extract(f)
        finally:
            f.close()

        return ParsedPaper(
            text=text,
            chunks=[text[i:i + 1000] for i in range(0, len(text), 1000)],
            metadata={"source": url_or_path},
        )
    except Exception as e:
        return ParsedPaper(text=f"Error parsing PDF: {e}", chunks=[], metadata={"error": str(e)})
