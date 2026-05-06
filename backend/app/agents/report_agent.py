import json
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.reports.storage import (
    build_asset,
    new_report_id,
    save_report_bundle,
    write_report_bytes,
    write_report_file,
    write_report_json,
)
from app.schemas.report import GeneratedReport, ReportSection, ReportSummary


class ReportDraft(BaseModel):
    title: str
    summary: str
    sections: list[ReportSection] = Field(default_factory=list)


class ReportAgent:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(model="gpt-5.4-nano").with_structured_output(ReportDraft)

    def generate(
        self,
        *,
        question: str,
        answer: str,
        trace_id: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> ReportSummary:
        prompt = self._build_prompt(
            question=question,
            answer=answer,
            trace_id=trace_id,
            tool_calls=tool_calls or [],
        )
        draft = self.llm.invoke(prompt)
        report_id = new_report_id()
        created_at = datetime.now(timezone.utc).isoformat()

        markdown = self._render_markdown(
            title=draft.title,
            question=question,
            summary=draft.summary,
            created_at=created_at,
            sections=draft.sections,
        )
        html = self._render_html_from_markdown(markdown)
        pdf_bytes = self._render_pdf_from_markdown(markdown)

        markdown_path = write_report_file(report_id, "report.md", markdown)
        html_path = write_report_file(report_id, "report.html", html)
        pdf_path = write_report_bytes(report_id, "report.pdf", pdf_bytes)
        bundle_payload = {
            "question": question,
            "answer": answer,
            "trace_id": trace_id,
            "tool_calls": tool_calls or [],
            "draft": draft.model_dump(mode="json"),
        }
        json_path = write_report_json(report_id, "report_data.json", bundle_payload)

        report = GeneratedReport(
            report_id=report_id,
            title=draft.title,
            question=question,
            summary=draft.summary,
            created_at=created_at,
            trace_id=trace_id,
            sections=draft.sections,
            assets=[
                build_asset(
                    asset_type="html",
                    label="HTML report",
                    path=html_path,
                    content_type="text/html; charset=utf-8",
                ),
                build_asset(
                    asset_type="pdf",
                    label="PDF report",
                    path=pdf_path,
                    content_type="application/pdf",
                ),
                build_asset(
                    asset_type="markdown",
                    label="Markdown report",
                    path=markdown_path,
                    content_type="text/markdown; charset=utf-8",
                ),
                build_asset(
                    asset_type="json",
                    label="Report data",
                    path=json_path,
                    content_type="application/json",
                ),
            ],
        )
        return save_report_bundle(report)

    def _build_prompt(
        self,
        *,
        question: str,
        answer: str,
        trace_id: str | None,
        tool_calls: list[dict],
    ) -> str:
        tool_json = json.dumps(tool_calls, indent=2)
        return f"""
You are a report-generation agent for ProductAI.

Create a concise business report from the grounded answer below.
Do not invent facts beyond the provided answer and tool-call evidence.
Keep the tone executive-friendly and factual.

Return:
- a clear title
- a short summary
- 3 to 5 sections with specific headings and useful content

Question:
{question}

Grounded answer:
{answer}

Trace ID:
{trace_id or "n/a"}

Tool evidence:
{tool_json}
""".strip()

    def _render_markdown(
        self,
        *,
        title: str,
        question: str,
        summary: str,
        created_at: str,
        sections: list[ReportSection],
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"Generated: {created_at}",
            "",
            f"Question: {question}",
            "",
            "## Executive Summary",
            "",
            summary.strip(),
        ]

        for section in sections:
            lines.extend(
                [
                    "",
                    f"## {section.heading}",
                    "",
                    section.body.strip(),
                ]
            )

        return "\n".join(lines).strip() + "\n"

    def _render_html_from_markdown(self, markdown: str) -> str:
        blocks = self._markdown_to_html_blocks(markdown)
        title = self._extract_markdown_title(markdown)
        return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <style>
      :root {{
        color-scheme: dark;
        --bg: #0f172a;
        --panel: #111827;
        --panel-2: #172033;
        --border: rgba(148, 163, 184, 0.18);
        --text: #e5e7eb;
        --muted: #94a3b8;
        --accent: #93c5fd;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        background: linear-gradient(180deg, #0b1120 0%, var(--bg) 100%);
        color: var(--text);
        font: 15px/1.6 Inter, Arial, sans-serif;
      }}

      .page {{
        max-width: 920px;
        margin: 0 auto;
        padding: 32px 20px 56px;
      }}

      .hero {{
        border: 1px solid var(--border);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(17,24,39,0.96), rgba(15,23,42,0.92));
        padding: 28px;
      }}

      .eyebrow {{
        color: var(--accent);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}

      h1 {{
        margin: 0 0 12px;
        font-size: 32px;
        line-height: 1.1;
      }}

      .report-section {{
        margin-top: 18px;
        border: 1px solid var(--border);
        border-radius: 14px;
        background: rgba(17, 24, 39, 0.72);
        padding: 20px;
      }}

      h2 {{
        margin: 0 0 12px;
        font-size: 20px;
      }}

      h3 {{
        margin: 0 0 12px;
        font-size: 16px;
        color: #dbeafe;
      }}

      p {{
        margin: 0 0 10px;
        color: #dbe4f3;
        white-space: pre-wrap;
      }}

      @media (max-width: 720px) {{
        .hero-grid {{
          grid-template-columns: 1fr;
        }}

        h1 {{
          font-size: 26px;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <div class="eyebrow">ProductAI Report</div>
        <h1>{escape(title)}</h1>
      </section>
      {"".join(blocks)}
    </main>
  </body>
</html>
"""

    def _markdown_to_html_blocks(self, markdown: str) -> list[str]:
        blocks: list[str] = []
        lines = markdown.splitlines()
        paragraph_lines: list[str] = []

        def flush_paragraph() -> None:
            if paragraph_lines:
                text = " ".join(part.strip() for part in paragraph_lines if part.strip())
                if text:
                    blocks.append(f'<section class="report-section"><p>{escape(text)}</p></section>')
                paragraph_lines.clear()

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                flush_paragraph()
                continue

            if line.startswith("# "):
                flush_paragraph()
                continue

            if line.startswith("## "):
                flush_paragraph()
                blocks.append(
                    '<section class="report-section">'
                    f"<h2>{escape(line[3:].strip())}</h2>"
                    "</section>"
                )
                continue

            if line.startswith("### "):
                flush_paragraph()
                blocks.append(
                    '<section class="report-section">'
                    f"<h3>{escape(line[4:].strip())}</h3>"
                    "</section>"
                )
                continue

            paragraph_lines.append(line)

        flush_paragraph()
        return blocks

    def _extract_markdown_title(self, markdown: str) -> str:
        for line in markdown.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return "ProductAI Report"

    def _render_pdf_from_markdown(self, markdown: str) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=48,
            rightMargin=48,
            topMargin=48,
            bottomMargin=48,
            title=self._extract_markdown_title(markdown),
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=HexColor("#0f172a"),
            spaceAfter=14,
        )
        heading_style = ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=HexColor("#1e3a8a"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=HexColor("#1f2937"),
            spaceAfter=8,
        )

        story = []
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
            if line.startswith("# "):
                story.append(Paragraph(xml_escape(line[2:].strip()), title_style))
                continue
            if line.startswith("## "):
                story.append(Paragraph(xml_escape(line[3:].strip()), heading_style))
                continue
            story.append(Paragraph(xml_escape(line), body_style))

        doc.build(story)
        return buffer.getvalue()
