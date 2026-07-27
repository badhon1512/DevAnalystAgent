import argparse
import json
from collections import defaultdict
from pathlib import Path


def _format_cost(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.6f}"


def _read_observed_answer(run: dict) -> str:
    if run.get("answer"):
        return str(run["answer"])
    result_path = run.get("result_path")
    if not result_path:
        return "Not captured."
    try:
        result = json.loads(Path(result_path).read_text(encoding="utf-8"))
        return str(result["response"]["answer"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return "Unavailable; inspect the raw result path."


def build_batch_report(manifest: dict) -> str:
    configuration = manifest["configuration"]
    summary = manifest["summary"]
    runs = manifest["runs"]
    category_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"completed": 0, "passed": 0, "score_total": 0}
    )

    for run in runs:
        if run["status"] != "completed":
            continue
        stats = category_stats[run["category"]]
        stats["completed"] += 1
        stats["passed"] += int(bool(run["passed"]))
        stats["score_total"] += run["score_percent"]

    lines = [
        "# ProductAI Benchmark Report",
        "",
        f"- Started: `{manifest['started_at']}`",
        f"- Model: `{configuration['model']}`",
        f"- Analysis depth: `{configuration['analysis_depth']}`",
        f"- Answer detail: `{configuration['answer_detail']}`",
        f"- Pass rate: **{summary['pass_rate_percent']}%**",
        f"- Average score: **{summary['average_score_percent']}%**",
        f"- Completed: **{summary['completed']} / {summary['selected']}**",
        f"- Errors: **{summary['errors']}**",
        f"- Known trace cost: **{_format_cost(summary['known_actual_cost_usd'])}**",
        f"- Average agent latency: **{summary['average_agent_latency_ms']} ms**",
        "",
        "## Category Summary",
        "",
        "| Category | Completed | Passed | Average score |",
        "|---|---:|---:|---:|",
    ]

    for category, stats in sorted(category_stats.items()):
        average = stats["score_total"] / stats["completed"] if stats["completed"] else 0
        lines.append(
            f"| {category} | {int(stats['completed'])} | {int(stats['passed'])} | "
            f"{average:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Case | Category | Status | Score | Tools | Latency | Cost |",
            "|---|---|---|---:|---|---:|---:|",
        ]
    )

    for run in runs:
        if run["status"] == "completed":
            tools = ", ".join(run["tools_used"]) or "none"
            lines.append(
                f"| `{run['case_id']}` | {run['category']} | "
                f"{'PASS' if run['passed'] else 'FAIL'} | {run['score_percent']}% | "
                f"{tools} | {run['agent_latency_ms']} ms | {_format_cost(run['cost_usd'])} |"
            )
        else:
            lines.append(
                f"| `{run['case_id']}` | {run['category']} | ERROR ({run['stage']}) | "
                f"- | - | - | - |"
            )

    failed_runs = [
        run for run in runs if run["status"] == "completed" and not run["passed"]
    ]
    if failed_runs:
        lines.extend(["", "## Failed Checks", ""])
        for run in failed_runs:
            score = json.loads(Path(run["score_path"]).read_text(encoding="utf-8"))
            lines.append(f"### `{run['case_id']}`")
            lines.append("")
            lines.append(f"**Observed answer:** {_read_observed_answer(run)}")
            lines.append("")
            for check in score["checks"]:
                if not check["passed"]:
                    lines.append(f"- **{check['name']}**: {check['detail']}")
            lines.append(f"- Raw result: `{run['result_path']}`")
            lines.append(f"- Score details: `{run['score_path']}`")
            lines.append("")

    error_runs = [run for run in runs if run["status"] == "error"]
    if error_runs:
        lines.extend(["## Execution Errors", ""])
        for run in error_runs:
            lines.append(
                f"- `{run['case_id']}` at `{run['stage']}`: "
                f"`{run['error_type']}` - {run['error']}"
            )

    lines.extend(
        [
            "",
            "## Debugging Flow",
            "",
            "For each case, inspect artifacts in this order:",
            "",
            "1. Batch manifest entry",
            "2. Raw `.json` response and trace",
            "3. `.score.json` deterministic checks",
            "4. Tool input/output blocks in the trace",
            "",
        ]
    )
    return "\n".join(lines)


def write_batch_report(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_path = manifest_path.with_suffix(".md")
    report_path.write_text(build_batch_report(manifest), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a readable batch report.")
    parser.add_argument("manifest_path", type=Path)
    args = parser.parse_args()
    report_path = write_batch_report(args.manifest_path)
    print(f"Saved readable report: {report_path}")


if __name__ == "__main__":
    main()
