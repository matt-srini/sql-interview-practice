"""
AST-based security guard for user-submitted Python code.

For Python (algorithms): blocks ALL imports and dangerous builtins.
For Pandas: allows a specific allowlist of safe imports.
"""
import ast
import re

# A {...} replacement field in a str.format / .format_map template. Used by the
# guard to catch dunder access hidden inside a format string (see visit_Constant).
_FORMAT_FIELD = re.compile(r"\{([^{}]*)\}")

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

    # ── format-string late binding (str.format / .format_map) ─────────────────
    # f-strings are safe: f"{x.__class__}" holds REAL ast.Attribute nodes that
    # visit_Attribute catches. But str.format() hides the accessor INSIDE a string
    # literal — `"{0.__globals__}".format(solve)` performs the attribute walk at
    # runtime, so the AST never sees __globals__. We therefore scan every string
    # constant for a replacement field whose NAME part (before any :spec / !conv)
    # contains a dunder, and block it. Legitimate fields ({0}, {name}, {0:.2f},
    # {x!r}, even {:_>10} fill) never contain "__" in the name part.

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            # Drop escaped braces so a {{literal}} isn't mistaken for a field.
            s = node.value.replace("{{", "").replace("}}", "")
            for field in _FORMAT_FIELD.findall(s):
                name = field.split(":", 1)[0].split("!", 1)[0]
                if "__" in name:
                    self.errors.append(
                        "format-string field accessing a dunder attribute is not allowed"
                    )
                    break
        self.generic_visit(node)


# ── User-facing message helpers ───────────────────────────────────────────────

_PANDAS_FS_READ = {
    "read_csv", "read_table", "read_fwf", "read_json", "read_html", "read_xml",
    "read_excel", "read_parquet", "read_feather", "read_orc", "read_sas",
    "read_spss", "read_stata", "read_hdf", "read_sql", "read_sql_table",
    "read_sql_query", "read_clipboard", "read_pickle",
}
_PANDAS_FS_WRITE = {
    "to_csv", "to_json", "to_excel", "to_parquet", "to_feather", "to_orc",
    "to_stata", "to_hdf", "to_sql", "to_pickle", "to_clipboard",
}
_NUMPY_IO_ATTRS = {"load", "loadtxt", "genfromtxt", "fromfile", "save", "savez", "savez_compressed", "savetxt"}
_NET_IMPORTS = {"requests", "urllib", "httpx", "aiohttp", "socket", "http"}
_OS_IMPORTS = {"os", "sys", "subprocess", "shutil", "pathlib", "tempfile", "glob", "signal"}

_ALLOWLIST_DISPLAY = {
    "python": "math, collections, heapq, bisect, itertools, functools, typing, re, copy, operator, sortedcontainers",
    "pandas": "pandas, numpy, math, statistics, collections, datetime, re, json",
    "statistics": "math, statistics, numpy, random, collections, itertools, functools",
}


def _one_friendly(error: str, topic: str) -> str:
    """Convert one raw guard-error string into a user-readable sentence."""
    if error == "format-string field accessing a dunder attribute is not allowed":
        return ("Template strings that reach internal (dunder) attributes are not "
                "allowed — use a plain format field like {0} or an f-string of a value.")
    m = re.match(r"access to attribute '(.+)' is not allowed", error)
    if m:
        attr = m.group(1)
        if attr in _PANDAS_FS_READ:
            return (
                f"pd.{attr}() is not available — DataFrames are already pre-loaded. "
                "Remove the read call and use the variable received by def solve()."
            )
        if attr in _PANDAS_FS_WRITE:
            return f"File output (.{attr}()) is not available in the sandbox."
        if attr in _NUMPY_IO_ATTRS:
            return f"NumPy file I/O (.{attr}()) is not available in the sandbox."
        if attr.startswith("__"):
            return f"Access to internal attribute '{attr}' is not allowed."
        return f"Attribute '.{attr}' is not available in the sandbox."

    m = re.match(r"import '([^']+)' is not allowed", error) or \
        re.match(r"from '([^']+)' import is not allowed", error)
    if m:
        pkg = m.group(1).split(".")[0]
        allowed = _ALLOWLIST_DISPLAY.get(topic, "the allowed set")
        if pkg in _NET_IMPORTS:
            return f"'{pkg}' is not available — network access is not allowed in the sandbox."
        return f"'{pkg}' is not available. Allowed imports: {allowed}."

    m = re.match(r"use of '(.+)' is not allowed", error)
    if m:
        name = m.group(1)
        if name in ("eval", "exec", "compile"):
            return f"{name}() is not allowed for security reasons."
        if name in ("open", "input"):
            return f"{name}() is not available — file and terminal I/O is blocked."
        if name in ("globals", "locals", "vars", "getattr", "setattr", "delattr"):
            return f"{name}() is not allowed."
        return f"'{name}' is not allowed."

    return error  # fallback: pass through unchanged


def user_messages(errors: list[str], topic: str) -> list[str]:
    """Map a list of raw guard errors to deduplicated user-facing explanations."""
    seen: set[str] = set()
    out: list[str] = []
    for e in errors:
        msg = _one_friendly(e, topic)
        if msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out


def check_solve_pattern(code: str, topic: str) -> list[str] | None:
    """Return a one-item list with a clear explanation if def solve() is missing,
    or None if the check passes or doesn't apply to this topic.

    Only fires when there is substantial code — a blank editor or a single
    placeholder comment shouldn't prompt the user about the pattern yet.
    """
    if topic not in ("python", "pandas", "statistics"):
        return None
    stripped = code.strip()
    if not stripped:
        return None
    if "def solve(" in code:
        return None
    if topic == "pandas":
        return [
            "Your code needs a solve() function — DataFrames are passed as keyword arguments, "
            "not global variables. Remove any pd.read_csv() calls and wrap your logic like this:\n\n"
            "def solve(df_name):  # df_name matches the variable shown in 'Available DataFrames'\n"
            "    ...\n"
            "    return result"
        ]
    return [
        "Your code needs a solve() function that returns the answer:\n\n"
        "def solve():\n"
        "    ...\n"
        "    return result"
    ]


def guard_detail(code: str, topic: str) -> dict | None:
    """Return the detail dict for a 400 HTTPException if the code fails validation,
    else None. Checks the solve() pattern first, then the AST guard.

    Usage in endpoints:
        if detail := python_guard.guard_detail(code, topic):
            raise HTTPException(status_code=400, detail=detail)
    """
    solve_errs = check_solve_pattern(code, topic)
    if solve_errs:
        return {"error": solve_errs[0], "user_messages": solve_errs}

    raw_errors = validate_code(code, topic)
    if raw_errors:
        return {
            "error": "Code contains disallowed constructs.",
            "guard_errors": raw_errors,
            "user_messages": user_messages(raw_errors, topic),
        }
    return None


def validate_code(code: str, topic: str = "python") -> list[str]:
    """
    Validate user code. Returns a list of error strings (empty = ok).

    topic: "python" (algorithm) → no imports allowed
           "pandas" → allowlist imports only
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    if topic == "pandas":
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
