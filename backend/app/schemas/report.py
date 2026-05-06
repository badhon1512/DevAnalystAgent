from typing import Literal

from pydantic import BaseModel, Field


class ReportAsset(BaseModel):
    type: Literal["html", "markdown", "json", "pdf", "chart", "csv", "other"]
    label: str
    filename: str
    relative_path: str
    content_type: str
    view_url: str | None = None
    download_url: str | None = None


class ReportSection(BaseModel):
    heading: str
    body: str


class GeneratedReport(BaseModel):
    report_id: str
    title: str
    question: str
    summary: str
    created_at: str
    trace_id: str | None = None
    sections: list[ReportSection] = Field(default_factory=list)
    assets: list[ReportAsset] = Field(default_factory=list)


class ReportSummary(BaseModel):
    report_id: str
    title: str
    summary: str
    created_at: str
    trace_id: str | None = None
    assets: list[ReportAsset] = Field(default_factory=list)
