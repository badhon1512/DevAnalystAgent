from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from app.tools import python_sandbox
from app.tools.python_sandbox import run_python_analytics


@pytest.fixture
def workspace_tmp_dir():
    root = Path(__file__).resolve().parents[1] / ".test_runtime" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_runs_basic_calculation():
    response = run_python_analytics("result = {'total': sum([1, 2, 3])}")

    assert response["error"] is None
    assert response["result"] == {"total": 6}
    assert response["charts"] == []


def test_blocks_open_and_preserves_existing_file(workspace_tmp_dir):
    target = workspace_tmp_dir / "do-not-delete.txt"
    target.write_text("keep me", encoding="utf-8")

    response = run_python_analytics(f"open({str(target)!r}, 'w')")

    assert "Use of 'open' is not allowed" in response["error"]
    assert target.read_text(encoding="utf-8") == "keep me"


def test_blocks_os_remove_and_preserves_existing_file(workspace_tmp_dir):
    target = workspace_tmp_dir / "do-not-delete.txt"
    target.write_text("keep me", encoding="utf-8")

    response = run_python_analytics(
        f"import os\nos.remove({str(target)!r})\nresult = 'deleted'"
    )

    assert response["error"] == "Import blocked: os"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "keep me"


def test_blocks_shutil_rmtree_and_preserves_directory(workspace_tmp_dir):
    target_dir = workspace_tmp_dir / "do-not-delete"
    target_dir.mkdir()
    target_file = target_dir / "data.txt"
    target_file.write_text("keep me", encoding="utf-8")

    response = run_python_analytics(
        f"import shutil\nshutil.rmtree({str(target_dir)!r})\nresult = 'deleted'"
    )

    assert response["error"] == "Import blocked: shutil"
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "keep me"


def test_blocks_pathlib_unlink_and_preserves_existing_file(workspace_tmp_dir):
    target = workspace_tmp_dir / "do-not-delete.txt"
    target.write_text("keep me", encoding="utf-8")

    response = run_python_analytics(
        f"from pathlib import Path\nPath({str(target)!r}).unlink()\nresult = 'deleted'"
    )

    assert response["error"] == "Import blocked: pathlib"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "keep me"


def test_blocks_relative_file_delete_inside_sandbox_runtime():
    runtime_file = python_sandbox._sandbox_runtime_dir() / "relative-delete-target.txt"
    runtime_file.write_text("keep me", encoding="utf-8")

    response = run_python_analytics(
        "import os\nos.remove('relative-delete-target.txt')\nresult = 'deleted'"
    )

    assert response["error"] == "Import blocked: os"
    assert runtime_file.exists()
    assert runtime_file.read_text(encoding="utf-8") == "keep me"

    runtime_file.unlink(missing_ok=True)


def test_stops_infinite_loop(monkeypatch):
    monkeypatch.setattr(python_sandbox, "SANDBOX_TIMEOUT_SECONDS", 1)

    response = run_python_analytics("while True:\n    pass")

    assert "exceeded 1 seconds" in response["error"]


def test_generates_chart_in_allowed_output(monkeypatch, workspace_tmp_dir):
    chart_output_dir = workspace_tmp_dir / "charts"
    chart_output_dir.mkdir()
    monkeypatch.setattr(python_sandbox, "CHART_OUTPUT_DIR", chart_output_dir)

    response = run_python_analytics(
        "plt.figure(figsize=(3, 2))\n"
        "plt.plot([1, 2, 3], [3, 1, 2])\n"
        "result = {'points': 3}",
        file_name="sandbox_chart.png",
    )

    assert response["error"] is None
    assert response["result"] == {"points": 3}
    assert len(response["charts"]) == 1

    chart_path = Path(response["charts"][0]["path"]).resolve()
    assert chart_path.exists()
    assert chart_path.suffix == ".png"
    assert chart_path.read_bytes().startswith(b"\x89PNG")
