import ast
import builtins
import io
import json
import math
import os
import statistics
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Dict, Optional

import matplotlib
import numpy as np
import pandas as pd
from langchain_core.tools import tool
from sqlalchemy import create_engine, text

from app.tools.read_write import build_chart_metadata, get_chart_output_path

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def run_readonly_sql(query: str):
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row._mapping) for row in result]


# Block these names even if user tries clever tricks
BANNED_NAMES = {
    "open", "eval", "exec", "compile",
    "input", "globals", "locals", "vars", "dir",
}

# Block risky modules
BANNED_IMPORT_PREFIXES = {
    "sys", "subprocess", "socket", "requests", "http", "urllib",
    "pathlib", "shutil", "pickle",
}


class UnsafeCodeError(Exception):
    pass


def _check_ast(tree: ast.AST) -> None:
    # 1) Validate imports
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            else:
                mod = node.module or ""
                names = [mod]

            for name in names:
                # ban prefixes like os, sys, etc.
                prefix = name.split(".")[0]
                if prefix in BANNED_IMPORT_PREFIXES:
                    raise UnsafeCodeError(f"Import blocked: {name}")

                # allowlist
                # if name not in ALLOWED_IMPORTS and prefix not in ALLOWED_IMPORTS:
                #     raise UnsafeCodeError(f"Import not allowed: {name}")

        # 2) Block dangerous builtins by name usage
        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise UnsafeCodeError(f"Use of '{node.id}' is not allowed")

        # 3) Block attribute access that commonly escapes sandbox
        # e.g., object.__class__, __dict__, __mro__, etc.
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise UnsafeCodeError("Dunder attribute access is not allowed")


def _safe_json(obj: Any) -> Any:
    """
    Ensure result is JSON serializable (best-effort).
    """
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def _error_response(message: str, stdout: str = "") -> Dict[str, Any]:
    return {
        "stdout": stdout,
        "result": None,
        "charts": [],
        "error": message,
    }


def run_python_analytics(
    code: str,
    file_name: str = "chart.png",
    input_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute restricted Python analytics code.

    Contract for agent:
    - Put final outputs in a variable named `result` (dict recommended).
    - If creating a chart, use matplotlib.pyplot and leave the current figure.
    - The tool always returns `stdout`, `result`, `charts`, and `error`.
    Args:
    - code: Python code to execute (string).  
    - file_name: Optional filename for saving charts (if generated).                                                  
    - input_data: Optional dict of input data to be used by the code.

    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code must be a non-empty string")

    try:
        tree = ast.parse(code, mode="exec")
        _check_ast(tree)
    except (SyntaxError, UnsafeCodeError, ValueError) as exc:
        return _error_response(str(exc))

    # Very small/controlled builtins
    safe_builtins = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "enumerate": enumerate,
        "range": range,
        "zip": zip,
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "sorted": sorted,
        "abs": abs,
        "round": round,
        "print": print,
        "Exception": Exception,
        "ValueError": ValueError,
        "TypeError": TypeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
        "ZeroDivisionError": ZeroDivisionError,
        "__import__": builtins.__import__,
    }

    # Execution globals/locals
    env: Dict[str, Any] = {
        "__builtins__": safe_builtins,
        "math": math,
        "statistics": statistics,
        "np": np,
        "pd": pd,
        "plt": plt,
        "input_data": input_data or {},
        "result": None,
        "datetime": datetime,
        "run_readonly_sql": run_readonly_sql,
    }

    stdout_buf = io.StringIO()
    plt.close("all")  # clear previous figures

    try:
        with redirect_stdout(stdout_buf):
            exec(compile(tree, filename="<agent_code>", mode="exec"), env, env)
    except Exception as exc:
        return _error_response(str(exc), stdout=stdout_buf.getvalue())

    stdout = stdout_buf.getvalue()
    charts: list[Dict[str, Any]] = []

    if plt.get_fignums():
        fig = plt.gcf()
        fig.tight_layout()
        output_path = get_chart_output_path(file_name or "chart.png")
        fig.savefig(
            output_path,
            format="png",
            dpi=150,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="white",
        )
        plt.close(fig)
        charts.append(build_chart_metadata(output_path))

    return {
        "stdout": stdout,
        "result": _safe_json(env.get("result")),
        "charts": charts,
        "error": None,
    }


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
    with open("python_sandbox.log", "a") as log_file:
        log_file.write(
            f"Executing code:\n{code}\nWith input_data:\n{json.dumps(input_data, default=str)}\n\n"
        )
    return run_python_analytics(code=code, input_data=input_data, file_name=file_name)
