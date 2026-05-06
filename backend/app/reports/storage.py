import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas.report import GeneratedReport, ReportAsset, ReportSummary

REPORTS_ROOT = Path("generated_reports").resolve()


def ensure_reports_root() -> Path:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    return REPORTS_ROOT


def new_report_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"report-{timestamp}-{uuid4().hex[:8]}"


def get_report_dir(report_id: str) -> Path:
    report_dir = ensure_reports_root() / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def write_report_file(report_id: str, filename: str, content: str, encoding: str = "utf-8") -> Path:
    report_dir = get_report_dir(report_id)
    path = (report_dir / filename).resolve()
    path.relative_to(report_dir.resolve())
    path.write_text(content, encoding=encoding)
    return path


def write_report_bytes(report_id: str, filename: str, content: bytes) -> Path:
    report_dir = get_report_dir(report_id)
    path = (report_dir / filename).resolve()
    path.relative_to(report_dir.resolve())
    path.write_bytes(content)
    return path


def write_report_json(report_id: str, filename: str, payload: dict[str, Any]) -> Path:
    report_dir = get_report_dir(report_id)
    path = (report_dir / filename).resolve()
    path.relative_to(report_dir.resolve())
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def relative_report_path(path: Path) -> str:
    return str(path.resolve().relative_to(ensure_reports_root()))


def build_asset(
    *,
    asset_type: str,
    label: str,
    path: Path,
    content_type: str,
) -> ReportAsset:
    return ReportAsset(
        type=asset_type,
        label=label,
        filename=path.name,
        relative_path=relative_report_path(path),
        content_type=content_type,
    )


def save_report_bundle(report: GeneratedReport) -> ReportSummary:
    report_dir = get_report_dir(report.report_id)
    metadata_path = report_dir / "report.json"
    metadata_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    return ReportSummary(
        report_id=report.report_id,
        title=report.title,
        summary=report.summary,
        created_at=report.created_at,
        trace_id=report.trace_id,
        assets=report.assets,
    )


def load_report(report_id: str) -> GeneratedReport:
    metadata_path = get_report_dir(report_id) / "report.json"
    return GeneratedReport.model_validate_json(metadata_path.read_text(encoding="utf-8"))


def resolve_asset_path(report_id: str, filename: str) -> Path:
    report_dir = get_report_dir(report_id).resolve()
    asset_path = (report_dir / filename).resolve()
    asset_path.relative_to(report_dir)
    return asset_path
