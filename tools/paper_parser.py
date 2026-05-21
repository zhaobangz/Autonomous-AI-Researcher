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


def parse_pdf(url_or_path: str) -> ParsedPaper:
    try:
        if url_or_path.startswith("http"):
            f = io.BytesIO(_stream_arxiv_pdf(url_or_path))
        else:
            f = open(Path(url_or_path).resolve(), "rb")

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

        return ParsedPaper(
            text=text,
            chunks=[text[i:i + 1000] for i in range(0, len(text), 1000)],
            metadata={"source": url_or_path},
        )
    except Exception as e:
        return ParsedPaper(text=f"Error parsing PDF: {e}", chunks=[], metadata={"error": str(e)})
