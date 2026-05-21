"""Tests for report assembly and PDF fallback behavior."""

from pydantic import BaseModel


def _build(tmp_path, monkeypatch, *, run_id="run-report-test", html=None,
           context=None, critique=None, debate_rebuttal=""):
    """Helper that wires up RUNS_DIR + WeasyPrint and invokes ReportGenerator.build."""
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))

    import core.report_generator as rg_module
    from core.report_generator import ReportGenerator

    monkeypatch.setattr(rg_module, "HTML", html)

    generator = ReportGenerator(run_id)
    paths = generator.build(
        context=context or {},
        critique=critique or {},
        debate_rebuttal=debate_rebuttal,
    )
    return generator, paths


# ── Original happy-path / fallback test ──────────────────────────────────
def test_report_generator_writes_markdown_and_pdf_fallback(tmp_path, monkeypatch):
    _, paths = _build(
        tmp_path,
        monkeypatch,
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
    # PDF placeholder must be non-empty bytes when WeasyPrint is unavailable
    assert pdf.read_bytes()


# ── Filesystem layout ────────────────────────────────────────────────────
class TestRunDirectory:
    def test_creates_run_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        from core.report_generator import ReportGenerator

        ReportGenerator("brand-new-run")
        assert (tmp_path / "brand-new-run").is_dir()

    def test_idempotent_when_run_dir_exists(self, tmp_path, monkeypatch):
        """Reusing the same run_id must not raise."""
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        (tmp_path / "existing").mkdir()
        from core.report_generator import ReportGenerator

        gen = ReportGenerator("existing")
        assert gen.run_dir.endswith("existing")

    def test_uses_default_runs_dir_when_env_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("RUNS_DIR", raising=False)
        monkeypatch.chdir(tmp_path)
        from core.report_generator import ReportGenerator

        gen = ReportGenerator("default-dir-run")
        assert "runs" in gen.run_dir
        assert (tmp_path / "runs" / "default-dir-run").is_dir()


# ── Markdown content shape ───────────────────────────────────────────────
class TestMarkdownContent:
    def test_includes_all_section_headers(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="sections",
            context={"question": "Q?", "plan": [], "literature": [], "code": "", "results": {}},
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        for header in (
            "# Autonomous Research Report",
            "## 1. Research Question",
            "## 2. Research Plan",
            "## 3. Literature Synthesis",
            "## 4. Code & Results",
            "## 5. Critic Review",
        ):
            assert header in md

    def test_unknown_question_when_missing(self, tmp_path, monkeypatch):
        _, paths = _build(tmp_path, monkeypatch, run_id="missing-q", context={}, critique={})
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "Unknown" in md

    def test_renders_dict_plan_steps(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="dict-plan",
            context={
                "plan": [
                    {"kind": "search", "rationale": "Find papers"},
                    {"kind": "code", "rationale": "Run experiment"},
                ]
            },
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "1. **SEARCH**: Find papers" in md
        assert "2. **CODE**: Run experiment" in md

    def test_renders_pydantic_dumped_plan_steps(self, tmp_path, monkeypatch):
        """The agent loop passes `plan.model_dump()["steps"]` — a list of dicts."""
        class _PlanStep(BaseModel):
            kind: str
            rationale: str
            expected_output: str = ""

        steps = [
            _PlanStep(kind="exec", rationale="Spawn container").model_dump(),
            _PlanStep(kind="summarize", rationale="Distill literature").model_dump(),
        ]
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="dumped-plan",
            context={"plan": steps},
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "**EXEC**: Spawn container" in md
        assert "**SUMMARIZE**: Distill literature" in md

    def test_renders_string_literature(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="str-lit",
            context={"literature": ["Source A summary", "Source B summary"]},
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "- Source A summary" in md
        assert "- Source B summary" in md

    def test_renders_dict_literature(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="dict-lit",
            context={
                "literature": [
                    {"title": "Attention", "summary": "self-attention basics"},
                    {"title": "BERT"},  # missing summary
                ]
            },
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "**Attention**: self-attention basics" in md
        assert "**BERT**" in md

    def test_includes_stderr_section_when_present(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="with-stderr",
            context={"results": {"stdout": "out", "stderr": "boom"}},
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "### Execution Errors" in md
        assert "boom" in md

    def test_omits_stderr_section_when_absent_or_empty(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="no-stderr",
            context={"results": {"stdout": "out", "stderr": ""}},
            critique={},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "### Execution Errors" not in md

    def test_includes_debate_section_when_provided(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="with-debate",
            context={},
            critique={},
            debate_rebuttal="Counter-argument: confounders ignored.",
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "## 6. Adversarial Debate" in md
        assert "Counter-argument: confounders ignored." in md

    def test_omits_debate_section_when_blank(self, tmp_path, monkeypatch):
        _, paths = _build(tmp_path, monkeypatch, run_id="no-debate")
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "## 6. Adversarial Debate" not in md


# ── Critique shapes ─────────────────────────────────────────────────────
class _CritiqueModel(BaseModel):
    strengths: str = ""
    weaknesses: str = ""
    bias_check: str = ""
    confidence_score: float = 0.0
    recommendations: str = ""
    final_verdict: str = ""


class TestCritiqueRendering:
    def test_renders_pydantic_critique_via_model_dump(self, tmp_path, monkeypatch):
        critique = _CritiqueModel(
            strengths="solid setup",
            weaknesses="small N",
            confidence_score=0.42,
            final_verdict="promising",
        )
        _, paths = _build(
            tmp_path, monkeypatch, run_id="pyd-crit", context={}, critique=critique
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        assert "solid setup" in md
        assert "small N" in md
        assert "0.42" in md
        assert "promising" in md

    def test_renders_dict_critique_with_defaults_for_missing_keys(self, tmp_path, monkeypatch):
        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="partial-crit",
            critique={"strengths": "great"},
        )
        md = open(paths["report_md"], encoding="utf-8").read()
        # Defaults for missing fields render but contain no value
        assert "**Strengths**: great" in md
        assert "**Confidence Score**: 0" in md


# ── PDF generation paths ────────────────────────────────────────────────
class TestPdfGeneration:
    def test_pdf_fallback_writes_placeholder_bytes(self, tmp_path, monkeypatch):
        _, paths = _build(tmp_path, monkeypatch, run_id="pdf-fallback")
        pdf_bytes = open(paths["report_pdf_path"], "rb").read()
        assert b"PDF generation unavailable" in pdf_bytes

    def test_uses_weasyprint_when_available(self, tmp_path, monkeypatch):
        """If HTML is set, write_pdf is invoked and no fallback bytes are written."""
        calls = {}

        class _StubHTML:
            def __init__(self, string):
                calls["html_string"] = string

            def write_pdf(self, target):
                with open(target, "wb") as f:
                    f.write(b"%PDF-1.4 stub")

        _, paths = _build(
            tmp_path,
            monkeypatch,
            run_id="pdf-html",
            html=_StubHTML,
            context={"question": "Why?"},
            critique={},
        )
        pdf_bytes = open(paths["report_pdf_path"], "rb").read()
        assert pdf_bytes == b"%PDF-1.4 stub"
        # The HTML constructor received the rendered markup
        assert "Autonomous Research Report" in calls["html_string"]

    def test_fallback_when_weasyprint_raises(self, tmp_path, monkeypatch):
        class _BoomHTML:
            def __init__(self, string):
                self.string = string

            def write_pdf(self, target):
                raise RuntimeError(f"native lib missing: target={target}")

        _, paths = _build(
            tmp_path, monkeypatch, run_id="pdf-boom", html=_BoomHTML
        )
        pdf_bytes = open(paths["report_pdf_path"], "rb").read()
        assert b"PDF generation unavailable" in pdf_bytes


# ── Return contract ─────────────────────────────────────────────────────
class TestReturnContract:
    def test_returns_md_and_pdf_paths(self, tmp_path, monkeypatch):
        _, paths = _build(tmp_path, monkeypatch, run_id="contract")
        assert set(paths.keys()) == {"report_md", "report_pdf_path"}
        assert paths["report_md"].endswith("report.md")
        assert paths["report_pdf_path"].endswith("report.pdf")
 