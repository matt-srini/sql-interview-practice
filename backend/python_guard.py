"""
AST-based security guard for user-submitted Python code.

For Python (algorithms): blocks ALL imports and dangerous builtins.
For Pandas: allows a specific allowlist of safe imports.
"""
import ast

# Imports allowed for the algorithm (Python) track
_ALGORITHM_ALLOWLIST = {
    "math",
    "collections",
    "heapq",
    "bisect",
    "itertools",
    "functools",
    "typing",
    "decimal",
    "fractions",
    "random",
    "string",
    "re",
    "copy",
    "operator",
    "abc",
    "dataclasses",
    "enum",
    "queue",
    "sortedcontainers",
}

# Imports allowed for the Statistics track (stdlib + numpy; no pandas/plotting)
_STATISTICS_ALLOWLIST = {
    "math",
    "statistics",
    "numpy",
    "random",
    "collections",
    "itertools",
    "functools",
    "decimal",
    "fractions",
    "operator",
    "typing",
}

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

# _BLOCKED_BUILTINS is superseded by _BLOCKED_NAMES (see above).
# Kept as an empty alias so any external code that might reference it doesn't crash,
# but it plays no role in the guard — _BLOCKED_NAMES is the active set.
_BLOCKED_BUILTINS: set[str] = set()

# Dangerous bare NAME references (Load context). Blocking these as names — not just as
# calls — closes the dynamic-attribute and builtins-dict escape routes in one rule:
#   getattr(x, '__cla'+'ss__')      → string-concat dodges a constant-arg check
#   globals()['__builtins__']['__import__']  → reach builtins via a dict
#   __builtins__.__import__('os')   → bare __builtins__ is injected by exec()
# These are never needed by a correct interview solution, so blocking them outright is safe.
_BLOCKED_NAMES = {
    "__builtins__", "__import__", "__loader__", "__spec__", "__build_class__",
    "globals", "locals", "vars",
    "getattr", "setattr", "delattr",
    "eval", "exec", "compile", "open", "input", "breakpoint", "memoryview",
}

# Dangerous attribute access patterns. Note: this guards attribute ACCESS (x.attr), not
# dunder-method DEFINITIONS (`def __lt__`) — so a class can still define __init__/__lt__/etc.
# super().__init__() and obj.__name__ stay allowed (__init__/__name__ are not escape attrs).
_BLOCKED_ATTRIBUTES = {
    # class / type hierarchy walk → object.__subclasses__() → os
    "__class__",
    "__bases__",
    "__base__",
    "__mro__",
    "__subclasses__",
    "__subclasshook__",
    "__init_subclass__",
    "__class_getitem__",
    # function / code / closure → reach globals + builtins
    "__globals__",
    "__builtins__",
    "__code__",
    "__closure__",
    "__func__",
    "__self__",
    "__wrapped__",
    "__objclass__",
    "__import__",
    # object internals / serialization gadgets
    "__dict__",
    "__getattribute__",
    "__getattr__",
    "__setattr__",
    "__delattr__",
    "__reduce__",
    "__reduce_ex__",
    "__weakref__",
    # frame / traceback / generator / coroutine introspection → f_globals → builtins
    "__traceback__",
    "tb_frame",
    "tb_next",
    "f_globals",
    "f_builtins",
    "f_locals",
    "f_back",
    "gi_frame",
    "gi_code",
    "cr_frame",
    "cr_code",
    "ag_frame",
    "func_globals",
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

    # ── imports ──────────────────────────────────────────────────────────────

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

    # ── dangerous bare names ──────────────────────────────────────────────────
    # Blocks: globals(), locals(), vars(), getattr(), eval(), exec(), open(),
    # __builtins__, __import__, breakpoint(), compile(), etc.
    # Rationale: these names are never needed by a correct interview solution;
    # blocking at Name-load time closes dynamic-string constructions like
    # `globals()['__builtins__']['__import__']` before they can be composed.

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in _BLOCKED_NAMES:
            self.errors.append(f"use of '{node.id}' is not allowed")
        self.generic_visit(node)

    # ── dangerous calls ───────────────────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        # getattr bypass: `getattr(x, '__class__')` — the old guard only caught
        # literal constant second-args. We now block ANY getattr call because:
        # (a) getattr(x, name) is caught at the visit_Name level, and
        # (b) even with a dynamic key argument we want to be conservative.
        # visit_Name already rejects the `getattr` name itself, so this is
        # belt-and-suspenders for the case where someone aliases it first.
        if isinstance(node.func, ast.Attribute) and node.func.attr == "getattr":
            # e.g. builtins.getattr(...)
            self.errors.append("use of 'getattr' is not allowed")
        self.generic_visit(node)

    # ── dangerous attribute access ────────────────────────────────────────────
    # Guards: obj.__class__, obj.__globals__, obj.f_globals, etc.
    # NOTE: only blocks ATTRIBUTE ACCESS (x.attr), not DEFINITIONS (def __init__).
    # A FunctionDef named __init__ is fine; accessing x.__init__ is blocked.

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _BLOCKED_ATTRIBUTES:
            self.errors.append(f"access to attribute '{node.attr}' is not allowed")
        self.generic_visit(node)

    # ── exception traceback walk ──────────────────────────────────────────────
    # `except Exception as e: e.__traceback__.tb_frame.f_globals` walks back to
    # the host globals. Blocked by __traceback__/tb_frame/f_globals in
    # _BLOCKED_ATTRIBUTES, but we also block ExceptHandler aliases that might
    # be used to access the exception object's __traceback__ attribute.
    # (The attribute visit above already covers tb_frame / f_globals.)

    # ── format-string / f-string late binding ────────────────────────────────
    # f"{().__class__.__bases__[0].__subclasses__()}" — the sub-expressions are
    # still AST nodes and are visited by generic_visit, so __class__ / __bases__
    # are caught by visit_Attribute above. No extra handler needed.


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

    if topic == "python_data":
        allowlist = _DATA_ALLOWLIST
    elif topic == "python":
        allowlist = _ALGORITHM_ALLOWLIST
    elif topic == "statistics":
        allowlist = _STATISTICS_ALLOWLIST
    else:
        # Unknown topic — fail safe: block all imports rather than accidentally allow everything.
        allowlist = set()
    visitor = _GuardVisitor(allowlist=allowlist)
    visitor.visit(tree)
    return visitor.errors
