"""
Robust PDF parser with size, SSRF, and content type protection.
"""
import io
import requests
from typing import Dict, Any, List
from pypdf import PdfReader
from pydantic import BaseModel

class ParsedPaper(BaseModel):
    text: str
    chunks: List[str]
    metadata: Dict[str, Any]

def parse_pdf(url_or_path: str) -> ParsedPaper:
    try:
        if url_or_path.startswith("http"):
            if not url_or_path.startswith("https://arxiv.org/pdf/"):
                raise ValueError(f"Blocked SSRF: {url_or_path}")
            response = requests.get(url_or_path, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type:
                raise ValueError("Response is not a PDF")
            if len(response.content) > 50 * 1024 * 1024:
                raise ValueError("PDF exceeds 50MB size limit")
                
            f = io.BytesIO(response.content)
        else:
            from pathlib import Path
            f = open(Path(url_or_path).resolve(), "rb")
            
        reader = PdfReader(f)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            
        if not text.strip():
            from pdfminer.high_level import extract_text
            f.seek(0)
            text = extract_text(f)
            
        return ParsedPaper(
            text=text,
            chunks=[text[i:i+1000] for i in range(0, len(text), 1000)],
            metadata={"source": url_or_path}
        )
    except Exception as e:
        return ParsedPaper(text=f"Error parsing PDF: {e}", chunks=[], metadata={"error": str(e)})
