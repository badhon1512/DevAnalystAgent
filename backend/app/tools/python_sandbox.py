import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_core.tools import tool

from app.tools.read_write import CHART_OUTPUT_DIR

SANDBOX_TIMEOUT_SECONDS = int(os.getenv("PYTHON_SANDBOX_TIMEOUT_SECONDS", "10"))
MAX_PAYLOAD_CHARS = int(os.getenv("PYTHON_SANDBOX_MAX_PAYLOAD_CHARS", "500000"))


def _error_response(message: str, stdout: str = "") -> Dict[str, Any]:
    return {
        "stdout": stdout,
        "result": None,
        "charts": [],
        "error": message,
    }


def _runner_working_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _sandbox_runtime_dir() -> Path:
    runtime_dir = (_runner_working_dir() / ".sandbox_runtime").resolve()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _sandbox_chart_dir(runtime_dir: Path) -> Path:
    chart_dir = (runtime_dir / "charts").resolve()
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


def run_python_analytics(
    code: str,
    file_name: str = "chart.png",
    input_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute restricted Python analytics code in a separate runner process.

    Contract for agent:
    - Put final outputs in a variable named `result` (dict recommended).
    - Use the preloaded `np`, `pd`, and `plt` objects instead of filesystem/network imports.
    - If creating a chart, leave the current matplotlib figure active.
    - The tool always returns `stdout`, `result`, `charts`, and `error`.
    """
    if not isinstance(code, str) or not code.strip():
        return _error_response("code must be a non-empty string")

    runtime_dir = _sandbox_runtime_dir()
    sandbox_chart_dir = _sandbox_chart_dir(runtime_dir)
    temp_dir = runtime_dir / "tmp"
    matplotlib_dir = runtime_dir / "matplotlib"
    temp_dir.mkdir(parents=True, exist_ok=True)
    matplotlib_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "code": code,
        "file_name": file_name or "chart.png",
        "input_data": input_data or {},
        "output_dir": str(sandbox_chart_dir),
    }
    payload_json = json.dumps(payload, default=str)
    if len(payload_json) > MAX_PAYLOAD_CHARS:
        return _error_response(f"Python sandbox payload exceeded {MAX_PAYLOAD_CHARS} characters")

    env = {
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(matplotlib_dir),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(_runner_working_dir()),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "WINDIR": os.environ.get("WINDIR", ""),
    }

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "app.sandbox.python_runner"],
            input=payload_json,
            text=True,
            capture_output=True,
            timeout=SANDBOX_TIMEOUT_SECONDS,
            cwd=runtime_dir,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _error_response(
            f"Python execution exceeded {SANDBOX_TIMEOUT_SECONDS} seconds and was stopped"
        )
    except Exception as exc:
        return _error_response(f"Python sandbox failed to start: {exc}")

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        return _error_response(stderr or f"Python sandbox exited with code {completed.returncode}")

    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _error_response(
            "Python sandbox returned invalid JSON",
            stdout=completed.stdout[-20000:],
        )

    if not isinstance(response, dict):
        return _error_response("Python sandbox returned an invalid response shape")

    return {
        "stdout": response.get("stdout", ""),
        "result": response.get("result"),
        "charts": _promote_charts(response.get("charts", []), sandbox_chart_dir),
        "error": response.get("error"),
    }


def _promote_charts(charts: Any, sandbox_chart_dir: Path) -> list[dict[str, str]]:
    if not isinstance(charts, list):
        return []

    promoted: list[dict[str, str]] = []
    for chart in charts:
        if not isinstance(chart, dict) or not chart.get("path"):
            continue

        source = Path(str(chart["path"])).resolve()
        try:
            source.relative_to(sandbox_chart_dir)
        except ValueError:
            continue

        destination = (CHART_OUTPUT_DIR / source.name).resolve()
        try:
            destination.relative_to(CHART_OUTPUT_DIR)
            shutil.copyfile(source, destination)
        except Exception:
            destination = source

        promoted.append(
            {
                "filename": destination.name,
                "path": str(destination),
                "relative_path": destination.name,
                "content_type": "image/png",
            }
        )

    return promoted


@tool
def execute_python_code_tool(
    code: str,
    file_name: Optional[str] = "chart.png",
    input_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run restricted Python code to extract insights, generate charts, or perform calculations.
    Return a structured response with `stdout`, `result`, `charts`, and `error`.
    If generating a matplotlib chart, leave the final figure active and it will be saved automatically.
    Prefer professional chart styling: clear title, labeled axes, readable legend, restrained colors,
    appropriate figure size, and tidy layout.
    """
    return run_python_analytics(code=code, input_data=input_data, file_name=file_name or "chart.png")
