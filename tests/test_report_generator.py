"""Tests for report assembly and PDF fallback behavior."""


def test_report_generator_writes_markdown_and_pdf_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))

    import core.report_generator as rg_module
    from core.report_generator import ReportGenerator

    monkeypatch.setattr(rg_module, "HTML", None)

    generator = ReportGenerator("run-report-test")
    paths = generator.build(
        context={
            "question": "What is tested?",
            "plan": [{"kind": "search", "rationale": "Find sources"}],
            "literature": ["Synthetic summary"],
            "code": "print('ok')",
            "results": {"stdout": "ok"},
        },
        critique={
            "strengths": "Clear",
            "weaknesses": "Limited",
            "bias_check": "None",
            "confidence_score": 0.8,
            "recommendations": "Expand",
            "final_verdict": "Useful",
        },
    )

    md = tmp_path / "run-report-test" / "report.md"
    pdf = tmp_path / "run-report-test" / "report.pdf"
    assert paths["report_md"] == str(md)
    assert paths["report_pdf_path"] == str(pdf)
    assert "What is tested?" in md.read_text(encoding="utf-8")
    assert pdf.read_bytes()