"""Tests for tools/paper_parser.py — SSRF protection and streaming size/type guards."""
from unittest.mock import MagicMock, patch

import pytest

from tools.paper_parser import MAX_PDF_BYTES, _validate_arxiv_url, parse_pdf


class TestUrlValidation:
    def test_non_arxiv_host_raises(self):
        with pytest.raises(ValueError, match="Blocked SSRF"):
            _validate_arxiv_url("https://evil.com/pdf/x")

    def test_http_scheme_raises(self):
        with pytest.raises(ValueError, match="scheme must be https"):
            _validate_arxiv_url("http://arxiv.org/pdf/1234")

    def test_userinfo_host_spoof_raises(self):
        # https://arxiv.org@evil.com/... → urlparse identifies host as evil.com
        with pytest.raises(ValueError, match="host must be arxiv.org"):
            _validate_arxiv_url("https://arxiv.org@evil.com/pdf/x")

    def test_wrong_path_raises(self):
        with pytest.raises(ValueError, match="path must start with /pdf/"):
            _validate_arxiv_url("https://arxiv.org/abs/1234")

    def test_valid_arxiv_url_accepted(self):
        _validate_arxiv_url("https://arxiv.org/pdf/2401.12345v1.pdf")


class TestParsePdfErrorHandling:
    """parse_pdf catches and returns errors in metadata rather than raising."""

    def test_non_arxiv_url_returns_error_paper(self):
        result = parse_pdf("https://evil.com/foo.pdf")
        assert "error" in result.metadata
        assert "Blocked SSRF" in result.metadata["error"]


class TestStreamingGuards:
    @staticmethod
    def _make_streaming_response(headers, chunks):
        """Build a context-manager mock that mimics httpx.stream() output."""
        response = MagicMock()
        response.headers = headers
        response.raise_for_status = MagicMock()
        response.iter_bytes = MagicMock(return_value=iter(chunks))
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=response)
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    def test_non_pdf_content_type_returns_error(self):
        bad_response = self._make_streaming_response(
            headers={"content-type": "text/html; charset=utf-8"},
            chunks=[b"<html>not a pdf</html>"],
        )
        with patch("tools.paper_parser.httpx.stream", return_value=bad_response):
            result = parse_pdf("https://arxiv.org/pdf/fake.pdf")
        assert "error" in result.metadata
        assert "not a PDF" in result.metadata["error"]

    def test_oversize_pdf_rejected_before_full_buffer(self):
        # Yield chunks that together exceed MAX_PDF_BYTES; the function must
        # bail mid-stream rather than buffering the whole payload.
        chunk_size = 1024 * 1024  # 1 MiB
        num_chunks = (MAX_PDF_BYTES // chunk_size) + 5  # ~5 MiB over the limit
        chunks = (b"\x00" * chunk_size for _ in range(num_chunks))
        big_response = self._make_streaming_response(
            headers={"content-type": "application/pdf"},
            chunks=chunks,
        )
        with patch("tools.paper_parser.httpx.stream", return_value=big_response):
            result = parse_pdf("https://arxiv.org/pdf/huge.pdf")
        assert "error" in result.metadata
        assert "50MB" in result.metadata["error"]
