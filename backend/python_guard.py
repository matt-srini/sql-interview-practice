"""
AST-based security guard for user-submitted Python code.

For Python (algorithms): blocks ALL imports and dangerous builtins.
For Pandas: allows a specific allowlist of safe imports.
"""
import ast

# Imports allowed for the Pandas track
_DATA_ALLOWLIST = {
    "pandas",
    "numpy",
    "math",
    "statistics",
    "collections",
    "itertools",
    "functools",
    "datetime",
    "re",
    "json",
    "decimal",
    "fractions",
    "operator",
    "string",
}

# Dangerous builtins to block in all tracks
_BLOCKED_BUILTINS = {
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "breakpoint",
    "memoryview",
}

# Dangerous attribute access patterns
_BLOCKED_ATTRIBUTES = {
    "__class__",
    "__bases__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__code__",
    "__reduce__",
    "__reduce_ex__",
    "mro",
    "system",
    "popen",
    "subprocess",
    # pandas / numpy filesystem and network I/O — blocked on all objects so
    # that pd.read_csv('/etc/passwd'), np.load('/etc/passwd'), etc. are caught
    # even though the user has not imported os/subprocess.
    "read_csv",
    "read_table",
    "read_fwf",
    "read_json",
    "read_html",
    "read_xml",
    "read_excel",
    "read_parquet",
    "read_feather",
    "read_orc",
    "read_sas",
    "read_spss",
    "read_stata",
    "read_hdf",
    "read_sql",
    "read_sql_table",
    "read_sql_query",
    "read_clipboard",
    "read_pickle",
    "to_csv",
    "to_json",
    "to_excel",
    "to_parquet",
    "to_feather",
    "to_orc",
    "to_stata",
    "to_hdf",
    "to_sql",
    "to_pickle",
    "to_clipboard",
    # numpy file I/O
    "load",
    "loadtxt",
    "genfromtxt",
    "fromfile",
    "save",
    "savez",
    "savez_compressed",
    "savetxt",
}


class _GuardVisitor(ast.NodeVisitor):
    def __init__(self, allowlist: set[str] | None = None):
        # None = block all imports; set = allow only listed top-level packages
        self.allowlist = allowlist
        self.errors: list[str] = []

    def _top_level(self, name: str) -> str:
        return name.split(".")[0]

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            top = self._top_level(alias.name)
            if self.allowlist is None:
                self.errors.append(f"import '{alias.name}' is not allowed")
            elif top not in self.allowlist:
                self.errors.append(f"import '{alias.name}' is not allowed (not in allowlist)")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        top = self._top_level(module)
        if self.allowlist is None:
            self.errors.append(f"from '{module}' import is not allowed")
        elif top not in self.allowlist:
            self.errors.append(f"from '{module}' import is not allowed (not in allowlist)")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Block dangerous builtin calls: eval(...), exec(...), open(...), __import__(...)
        if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_BUILTINS:
            self.errors.append(f"call to '{node.func.id}' is not allowed")
        # Block getattr(x, '__class__', ...) style access
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) >= 2:
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and arg.value in _BLOCKED_ATTRIBUTES:
                    self.errors.append(f"getattr access to '{arg.value}' is not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _BLOCKED_ATTRIBUTES:
            self.errors.append(f"access to attribute '{node.attr}' is not allowed")
        self.generic_visit(node)


def validate_code(code: str, topic: str = "python") -> list[str]:
    """
    Validate user code. Returns a list of error strings (empty = ok).

    topic: "python" (algorithm) → no imports allowed
           "python_data" → allowlist imports only
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    allowlist = _DATA_ALLOWLIST if topic == "python_data" else None
    visitor = _GuardVisitor(allowlist=allowlist)
    visitor.visit(tree)
    return visitor.errors
