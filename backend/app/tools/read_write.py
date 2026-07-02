import base64
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

FRONTEND_PUBLIC_DIR = Path(__file__).resolve().parents[3] / "frontend" / "public"
CHART_OUTPUT_DIR = (FRONTEND_PUBLIC_DIR / "generated" / "charts").resolve()
CHART_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_chart_path(filename: str) -> Path:
    safe_name = os.path.basename(filename)
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"

    output_path = (CHART_OUTPUT_DIR / safe_name).resolve()
    output_path.relative_to(CHART_OUTPUT_DIR)
    return output_path


def get_chart_output_path(filename: str = "chart.png") -> Path:
    return _safe_chart_path(filename)


def build_chart_metadata(path: Path) -> dict[str, str]:
    resolved_path = path.resolve()
    return {
        "filename": resolved_path.name,
        "path": str(resolved_path),
        "relative_path": str(resolved_path.relative_to(CHART_OUTPUT_DIR)),
        "content_type": "image/png",
    }


@tool
def save_chart_tool(chart_png_base64: str, filename: str = "chart.png") -> dict[str, Any]:
    """Save a base64-encoded PNG chart into the allowed chart output folder."""
    if not isinstance(chart_png_base64, str) or not chart_png_base64:
        return {
            "saved": False,
            "error": "chart_png_base64 must be a non-empty base64 string",
        }

    try:
        output_path = _safe_chart_path(filename)
        image_bytes = base64.b64decode(chart_png_base64)
        with open(output_path, "wb") as file_handle:
            file_handle.write(image_bytes)
    except Exception as exc:
        return {"saved": False, "error": str(exc)}

    return {
        "saved": True,
        **build_chart_metadata(output_path),
    }
