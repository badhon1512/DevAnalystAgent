import ast


ALLOWED_IMPORT_ROOTS = {
    "datetime",
    "json",
    "math",
    "matplotlib",
    "numpy",
    "pandas",
    "statistics",
}

BANNED_NAMES = {
    "__import__",
    "compile",
    "dir",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "vars",
}

BANNED_IMPORT_ROOTS = {
    "asyncio",
    "builtins",
    "ctypes",
    "dbm",
    "fcntl",
    "glob",
    "http",
    "importlib",
    "inspect",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "requests",
    "shutil",
    "signal",
    "socket",
    "sqlite3",
    "sqlalchemy",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "urllib",
}

BANNED_ATTRIBUTES = {
    "fromfile",
    "genfromtxt",
    "load",
    "loadtxt",
    "read_clipboard",
    "read_csv",
    "read_excel",
    "read_feather",
    "read_fwf",
    "read_hdf",
    "read_html",
    "read_json",
    "read_orc",
    "read_parquet",
    "read_pickle",
    "read_sas",
    "read_spss",
    "read_sql",
    "read_sql_query",
    "read_sql_table",
    "read_stata",
    "read_table",
    "read_xml",
    "save",
    "savefig",
    "savetxt",
    "to_clipboard",
    "to_csv",
    "to_excel",
    "to_feather",
    "to_hdf",
    "to_json",
    "to_orc",
    "to_parquet",
    "to_pickle",
    "to_sql",
    "to_stata",
    "to_xml",
}


class UnsafeCodeError(Exception):
    pass


def validate_python_code(code: str) -> ast.AST:
    if not isinstance(code, str) or not code.strip():
        raise UnsafeCodeError("code must be a non-empty string")

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCodeError(str(exc)) from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _validate_import(alias.name)

        if isinstance(node, ast.ImportFrom):
            _validate_import(node.module or "")

        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise UnsafeCodeError(f"Use of '{node.id}' is not allowed")

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise UnsafeCodeError("Dunder attribute access is not allowed")
            if node.attr in BANNED_ATTRIBUTES:
                raise UnsafeCodeError(f"Attribute '{node.attr}' is not allowed")

    return tree


def _validate_import(module_name: str) -> None:
    root = module_name.split(".")[0]
    if root in BANNED_IMPORT_ROOTS:
        raise UnsafeCodeError(f"Import blocked: {module_name}")
    if root not in ALLOWED_IMPORT_ROOTS:
        raise UnsafeCodeError(f"Import is not allowed: {module_name}")


def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0:
        raise ImportError("Relative imports are not allowed")
    _validate_import(name)
    return __import__(name, globals, locals, fromlist, level)
