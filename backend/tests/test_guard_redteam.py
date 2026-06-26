"""Red-team test suite for python_guard.py.

Every test in _ESCAPE_ATTEMPTS must be REJECTED by the guard.
Every snippet in _LEGIT_SNIPPETS must be ALLOWED (no false positives on real interview code).

Run with: pytest tests/test_guard_redteam.py -v
"""
import pytest
from python_guard import validate_code

# ---------------------------------------------------------------------------
# Escape attempts — all must be BLOCKED
# ---------------------------------------------------------------------------
_ESCAPE_ATTEMPTS = [
    # --- classic dunder chain ---
    ("dunder_subclasses",     "python", "().__class__.__bases__[0].__subclasses__()"),
    ("dunder_mro",            "python", "int.__mro__[0].__subclasses__()"),
    ("dunder_globals",        "python", "def solve(): return solve.__globals__"),
    ("dunder_builtins",       "python", "def solve(): return solve.__globals__['__builtins__']"),
    # --- str.format late binding (dunder hidden inside a string literal) ---
    ("format_globals",        "python", "def solve(): return '{0.__globals__}'.format(solve)"),
    ("format_builtins_index", "python", "def solve(): return '{0.__globals__[__builtins__]}'.format(solve)"),
    ("format_class_walk",     "python", "def solve(): return '{0.__class__.__bases__}'.format(solve)"),
    ("format_map_globals",    "python", "def solve(): return '{x.__globals__}'.format_map({'x': solve})"),
    ("format_split_literal",  "python", "def solve():\n    t = '{0.__globals__}'\n    return t.format(solve)"),
    ("format_globals_pandas", "pandas", "def solve(df):\n    return '{0.__globals__}'.format(solve)"),
    ("dunder_code",           "python", "def solve(): return solve.__code__.co_consts"),
    ("dunder_bases",          "python", "list.__bases__[0].__subclasses__()"),
    ("dunder_closure",        "python", "def solve(): return solve.__closure__"),
    ("dunder_reduce",         "python", "class E:\n    def __reduce__(self): return (eval,('1',))"),

    # --- globals / locals / vars ---
    ("bare_globals",          "python", "def solve(): return globals()"),
    ("bare_locals",           "python", "def solve(): return locals()"),
    ("bare_vars",             "python", "def solve(): return vars()"),

    # --- getattr bypass (dynamic key) ---
    ("getattr_literal",       "python", "def solve(): return getattr([], '__class__')"),
    ("getattr_dynamic",       "python", "k='__cla'+'ss__'\ndef solve(): return getattr([], k)"),
    ("getattr_name_blocked",  "python", "def solve(): return getattr"),

    # --- eval / exec ---
    ("bare_eval",             "python", "def solve(): eval('1+1')"),
    ("bare_exec",             "python", "def solve(): exec('import os')"),
    ("bare_compile",          "python", "def solve(): compile('1','<>','eval')"),

    # --- __import__ ---
    ("dunder_import",         "python", "def solve(): __import__('os')"),

    # --- open / input ---
    ("bare_open",             "python", "def solve(): return open('/etc/passwd').read()"),
    ("bare_input",            "python", "def solve(): return input('x')"),

    # --- import blocked (algorithm track) ---
    ("import_os",             "python", "import os\ndef solve(): return os.environ"),
    ("import_subprocess",     "python", "import subprocess\ndef solve(): pass"),
    ("from_os",               "python", "from os import environ\ndef solve(): pass"),
    ("from_sys",              "python", "from sys import path\ndef solve(): pass"),

    # --- traceback / frame walk ---
    ("traceback_walk",        "python",
     "def solve():\n    try:\n        1/0\n    except Exception as e:\n        return e.__traceback__"),
    ("frame_globals",         "python",
     "import sys\ndef solve(): return sys._getframe().f_globals"),

    # --- f-string subclasses gadget ---
    ("fstring_dunder",        "python",
     "def solve(): return f\"{().__class__.__bases__[0].__subclasses__()}\""),

    # --- pandas/data track: blocked imports ---
    ("import_os_pandas",      "pandas", "import os\ndef solve(df): return df"),
    ("import_subprocess_pd",  "pandas", "import subprocess\ndef solve(df): return df"),
    ("from_os_pandas",        "pandas", "from os.path import exists\ndef solve(df): return df"),

    # --- pandas read_csv / filesystem via attribute ---
    ("attr_read_csv",         "pandas",
     "import pandas as pd\ndef solve(df): return pd.read_csv('/etc/passwd')"),
    ("attr_to_csv",           "pandas",
     "import pandas as pd\ndef solve(df): df.to_csv('/tmp/x.csv')"),

    # --- breakpoint ---
    ("breakpoint_call",       "python", "def solve(): breakpoint()"),

    # --- statistics track: os still blocked ---
    ("import_os_stats",       "statistics", "import os\ndef solve(x): return x"),
]


@pytest.mark.parametrize("name,topic,code", _ESCAPE_ATTEMPTS, ids=[x[0] for x in _ESCAPE_ATTEMPTS])
def test_escape_is_blocked(name, topic, code):
    errs = validate_code(code, topic)
    assert errs, f"ESCAPE NOT BLOCKED [{name}]: guard passed the following code:\n{code}"


# ---------------------------------------------------------------------------
# Legitimate interview code — must NOT be blocked (no false positives)
# ---------------------------------------------------------------------------
_LEGIT_SNIPPETS = [
    ("two_sum", "python",
     "def solve(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target-n in seen: return [seen[target-n], i]\n        seen[n] = i"),

    ("bfs_graph", "python",
     "from collections import deque\ndef solve(graph, start):\n    q=deque([start]); v={start}\n    while q:\n        n=q.popleft()\n        for nb in graph.get(n,[]):\n            if nb not in v: v.add(nb); q.append(nb)\n    return v"),

    ("heapq_use", "python",
     "import heapq\ndef solve(nums, k):\n    return heapq.nlargest(k, nums)"),

    ("dataclass", "python",
     "from dataclasses import dataclass\n@dataclass\nclass Node:\n    val: int\n    left: 'Node' = None\n    right: 'Node' = None\ndef solve(v): return Node(v)"),

    ("enum_use", "python",
     "from enum import Enum\nclass Color(Enum):\n    RED = 1\ndef solve(): return Color.RED.value"),

    ("class_with_dunder_init", "python",
     "class MinStack:\n    def __init__(self):\n        self.stack = []\n    def push(self, v): self.stack.append(v)\ndef solve(): s=MinStack(); s.push(1); return s"),

    ("class_lt_eq", "python",
     "class Pair:\n    def __init__(self,a,b): self.a,self.b=a,b\n    def __lt__(self,o): return self.a<o.a\n    def __eq__(self,o): return self.a==o.a\ndef solve(a,b): return Pair(a,b)"),

    ("class_repr_str", "python",
     "class Point:\n    def __init__(self,x,y): self.x,self.y=x,y\n    def __repr__(self): return f'Point({self.x},{self.y})'\n    def __str__(self): return repr(self)\ndef solve(x,y): return str(Point(x,y))"),

    ("numpy_stats", "statistics",
     "import numpy as np\ndef solve(data):\n    return float(np.mean(data))"),

    ("math_use", "statistics",
     "import math\ndef solve(x): return math.sqrt(abs(x))"),

    ("pandas_groupby", "pandas",
     "import pandas as pd\ndef solve(df):\n    return df.groupby('a')['b'].sum().reset_index()"),

    ("try_except_value", "python",
     "def solve(s):\n    try:\n        return int(s)\n    except ValueError:\n        return -1"),

    ("type_hints", "python",
     "from typing import List, Optional\ndef solve(nums: List[int]) -> Optional[int]:\n    return nums[0] if nums else None"),
]


@pytest.mark.parametrize("name,topic,code", _LEGIT_SNIPPETS, ids=[x[0] for x in _LEGIT_SNIPPETS])
def test_legit_code_passes(name, topic, code):
    errs = validate_code(code, topic)
    assert not errs, f"FALSE POSITIVE [{name}]: legitimate code was rejected:\n{code}\nErrors: {errs}"


# ---------------------------------------------------------------------------
# GAP-1/2/3/4 vectors found in the 2026-06-26 sandbox audit.
# Each vector bypasses the *attribute*-level guard (no ast.Attribute node is
# produced) and must be caught by the string/bytes-literal token scan
# (_DANGEROUS_TOKEN_RE) or by the _BLOCKED_ATTRIBUTES addition of _os/_sys/
# modules/sys/os.
# ---------------------------------------------------------------------------
def test_runtime_string_and_reexport_reaches_are_blocked():
    """GAP-1/2/3/4 vectors from the 2026-06-26 sandbox audit.

    GAP-1: operator.attrgetter with a dunder string — no ast.Attribute node.
    GAP-2: random._os module re-export — bypasses import block via attribute hop.
    GAP-3: typing.sys module re-export — same attribute-hop pattern.
    GAP-4: bytes-literal format bypass — b'...'.decode().format() hides dunder
            in a bytes constant which the old str-only scan missed.
    """
    # GAP-1: operator.attrgetter('__globals__') — dunder hidden in a string arg
    errs = validate_code(
        "import operator\ndef solve():\n    return operator.attrgetter('__globals__')(solve)['__builtins__']\n",
        "python",
    )
    assert errs, "GAP-1 NOT BLOCKED: operator.attrgetter('__globals__') passed the guard"

    # GAP-2: random._os attribute hop — accesses real os via a private re-export
    errs = validate_code(
        "import random\ndef solve():\n    return random._os.getcwd()\n",
        "python",
    )
    assert errs, "GAP-2 NOT BLOCKED: random._os attribute hop passed the guard"

    # GAP-3: typing.sys module re-export — reaches sys.modules without importing sys
    errs = validate_code(
        "import typing\ndef solve():\n    return typing.sys.modules['os']\n",
        "python",
    )
    assert errs, "GAP-3 NOT BLOCKED: typing.sys attribute hop passed the guard"

    # GAP-4: bytes-literal format bypass — dunder hidden in a bytes constant
    errs = validate_code(
        "def solve():\n    return b'{0.__globals__}'.decode().format(solve)\n",
        "python",
    )
    assert errs, "GAP-4 NOT BLOCKED: bytes-literal dunder format bypass passed the guard"

    # GAP-1 (pandas track): same attrgetter vector must be blocked on the data track too
    errs = validate_code(
        "import operator\ndef solve(**k):\n    return operator.attrgetter('__globals__')(solve)['__builtins__']\n",
        "pandas",
    )
    assert errs, "GAP-1 (pandas) NOT BLOCKED: operator.attrgetter('__globals__') passed the guard on pandas track"
