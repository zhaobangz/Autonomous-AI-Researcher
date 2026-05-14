# core/report_generator.py
import os
import logging
import markdown
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
except (ImportError, OSError) as exc:
    logger.warning("WeasyPrint is unavailable; PDF reports will use fallback placeholder: %s", exc)
    HTML = None

class ReportGenerator:
    def __init__(self, run_id: str):
        self.run_id = run_id
        base = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        self.run_dir = str(base / run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.md_path = os.path.join(self.run_dir, "report.md")
        self.pdf_path = os.path.join(self.run_dir, "report.pdf")

    def build(self, context: dict, critique: dict, debate_rebuttal: str = "") -> dict:
        question = context.get("question", "Unknown")
        plan = context.get("plan", [])
        literature = context.get("literature", [])
        code = context.get("code", "")
        results = context.get("results", {})
        
        md_content = f"# Autonomous Research Report\n\n"
        md_content += f"## 1. Research Question\n{question}\n\n"
        
        md_content += f"## 2. Research Plan\n"
        for i, step in enumerate(plan, 1):
            kind = getattr(step, 'kind', step.get('kind', 'unknown')) if hasattr(step, '__dict__') or isinstance(step, dict) else 'unknown'
            rationale = getattr(step, 'rationale', step.get('rationale', '')) if hasattr(step, '__dict__') or isinstance(step, dict) else ''
            md_content += f"{i}. **{kind.upper()}**: {rationale}\n"
        
        md_content += f"\n## 3. Literature Synthesis\n"
        for lit in literature:
            if isinstance(lit, str):
                md_content += f"- {lit}\n"
            else:
                md_content += f"- **{lit.get('title', 'Unknown')}**: {lit.get('summary', '')}\n"
        
        md_content += f"\n## 4. Code & Results\n"
        md_content += f"### Generated Code\n```python\n{code}\n```\n\n"
        md_content += f"### Execution Output\n```\n{results.get('stdout', '')}\n```\n\n"
        if results.get("stderr"):
            md_content += f"### Execution Errors\n```\n{results.get('stderr')}\n```\n\n"
            
        md_content += f"\n## 5. Critic Review\n"
        if hasattr(critique, "model_dump"):
            critique = critique.model_dump()
        
        md_content += f"- **Strengths**: {critique.get('strengths', '')}\n"
        md_content += f"- **Weaknesses**: {critique.get('weaknesses', '')}\n"
        md_content += f"- **Confidence Score**: {critique.get('confidence_score', 0)}\n"
        md_content += f"- **Verdict**: {critique.get('final_verdict', '')}\n"

        if debate_rebuttal:
            md_content += f"\n## 6. Adversarial Debate\n"
            md_content += f"**Debater Rebuttal:**\n{debate_rebuttal}\n"

        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        html_content = markdown.markdown(md_content)
        try:
            if HTML:
                HTML(string=html_content).write_pdf(self.pdf_path)
            else:
                raise RuntimeError("WeasyPrint is not available")
        except Exception as exc:
            logger.warning("PDF generation failed for run %s: %s", self.run_id, exc)
            with open(self.pdf_path, "wb") as f:
                f.write(
                    b"PDF generation unavailable on this host. "
                    b"Install WeasyPrint native dependencies or use the Markdown report."
                )
        
        return {
            "report_md": self.md_path,
            "report_pdf_path": self.pdf_path
        }
