from app.schemas.report import GeneratedReport, ReportSummary


def with_report_urls(report: ReportSummary | GeneratedReport) -> ReportSummary | GeneratedReport:
    for asset in report.assets:
        asset.view_url = f"/reports/{report.report_id}/assets/{asset.filename}"
        asset.download_url = f"/reports/{report.report_id}/download/{asset.filename}"
    return report
