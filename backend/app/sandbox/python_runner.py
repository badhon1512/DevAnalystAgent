import io
import json
import math
import os
import statistics
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

from app.sandbox.policy import UnsafeCodeError, restricted_import, validate_python_code

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MAX_STDOUT_CHARS = 20_000
MAX_RESULT_JSON_CHARS = 200_000


def main() -> None:
    try:
        payload = json.loads(sys_stdin())
        response = run_python_analytics(
            code=payload.get("code", ""),
            file_name=payload.get("file_name") or "chart.png",
            input_data=payload.get("input_data") or {},
            output_dir=payload.get("output_dir"),
        )
    except Exception as exc:
        response = _error_response(str(exc))

    print(json.dumps(response, default=str), flush=True)


def sys_stdin() -> str:
    import sys

    return sys.stdin.read()


def run_python_analytics(
    code: str,
    file_name: str,
    input_data: dict[str, Any],
    output_dir: str | None,
) -> dict[str, Any]:
    try:
        tree = validate_python_code(code)
    except UnsafeCodeError as exc:
        return _error_response(str(exc))

    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "filter": filter,
        "float": float,
        "int": int,
        "IndexError": IndexError,
        "KeyError": KeyError,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "pow": pow,
        "print": print,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "TypeError": TypeError,
        "ValueError": ValueError,
        "ZeroDivisionError": ZeroDivisionError,
        "zip": zip,
        "__import__": restricted_import,
    }

    env: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "datetime": datetime,
        "json": json,
        "math": math,
        "np": np,
        "pd": pd,
        "plt": plt,
        "statistics": statistics,
        "input_data": input_data,
        "result": None,
    }

    stdout_buf = io.StringIO()
    plt.close("all")

    try:
        with redirect_stdout(stdout_buf):
            exec(compile(tree, filename="<agent_python>", mode="exec"), env, env)
    except Exception as exc:
        return _error_response(str(exc), stdout=_limit_text(stdout_buf.getvalue()))

    charts: list[dict[str, str]] = []
    if plt.get_fignums():
        chart = _save_chart(output_dir=output_dir, file_name=file_name)
        if chart.get("error"):
            return _error_response(chart["error"], stdout=_limit_text(stdout_buf.getvalue()))
        charts.append(chart)

    return {
        "stdout": _limit_text(stdout_buf.getvalue()),
        "result": _safe_json(env.get("result")),
        "charts": charts,
        "error": None,
    }


def _save_chart(output_dir: str | None, file_name: str) -> dict[str, str]:
    if not output_dir:
        return {"error": "output_dir is required for chart saving"}

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    safe_name = os.path.basename(file_name or "chart.png")
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"

    output_path = (output_root / safe_name).resolve()
    try:
        output_path.relative_to(output_root)
    except ValueError:
        return {"error": "chart output path escaped the allowed directory"}

    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(
        output_path,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="white",
    )
    plt.close(fig)

    return {
        "filename": output_path.name,
        "path": str(output_path),
        "relative_path": output_path.name,
        "content_type": "image/png",
    }


def _safe_json(obj: Any) -> Any:
    try:
        encoded = json.dumps(obj, default=str)
    except Exception:
        return str(obj)

    if len(encoded) > MAX_RESULT_JSON_CHARS:
        return {
            "truncated": True,
            "message": f"result exceeded {MAX_RESULT_JSON_CHARS} JSON characters",
        }
    return json.loads(encoded)


def _limit_text(text: str) -> str:
    if len(text) <= MAX_STDOUT_CHARS:
        return text
    return text[:MAX_STDOUT_CHARS] + "\n...[stdout truncated]"


def _error_response(message: str, stdout: str = "") -> dict[str, Any]:
    return {
        "stdout": stdout,
        "result": None,
        "charts": [],
        "error": message,
    }


if __name__ == "__main__":
    main()
