"""Landlock filesystem read-scoping for the sandbox subprocess (Linux >= 5.13).

Closes the arbitrary-file-read residual documented in
``docs/specs/sandbox-threat-model.md``: even after an in-process guard escape reaches the
``os`` module, this restricts the harness process so it can only READ the Python runtime,
system libraries, the harness file, the datasets dir, and ``/tmp`` — and NOT
``backend/content`` (the practice/mock answer keys) or app source. Writes are not handled
(``/tmp`` writes still work); the non-root + root-owned ``/app`` already contains writes.

Implemented with raw ``ctypes`` syscalls (no third-party dependency). Like the seccomp
filters, it is **unprivileged** (requires ``NO_NEW_PRIVS``) and **per-process**, applied
inside the harness before user code runs. It **fails OPEN**: if the kernel lacks Landlock,
``restrict_reads`` returns a status string instead of raising, and the app logs Landlock's
availability at boot (``main.py``) so we never believe we are protected when we are not.

References: Linux ``Documentation/userspace-api/landlock.rst``; syscalls
``landlock_create_ruleset`` (444), ``landlock_add_rule`` (445), ``landlock_restrict_self``
(446) — identical numbers on x86_64 and aarch64 (Railway is amd64; CI is amd64).
"""
from __future__ import annotations

import ctypes
import os
import platform
import sys

# Syscall numbers by arch. landlock_{create_ruleset, add_rule, restrict_self}.
_SYS_NRS = {
    "x86_64": (444, 445, 446),
    "aarch64": (444, 445, 446),
    "arm64": (444, 445, 446),
}

_PR_SET_NO_NEW_PRIVS = 38
_LANDLOCK_CREATE_RULESET_VERSION = 1  # flag: return the supported ABI version
_RULE_PATH_BENEATH = 1

# ABI v1 filesystem access-right bits (all we need: read + execute).
_FS_EXECUTE = 1 << 0
_FS_READ_FILE = 1 << 2
_FS_READ_DIR = 1 << 3
_HANDLED = _FS_EXECUTE | _FS_READ_FILE | _FS_READ_DIR


class _RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    # struct landlock_path_beneath_attr is __packed__ (u64 then s32, no padding).
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def _libc() -> "ctypes.CDLL":
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc


def _nrs():
    return _SYS_NRS.get(platform.machine())


def abi_version() -> "int | None":
    """The Landlock ABI version the running kernel supports, or None if unavailable.

    Used by the app at boot to log whether file-read scoping is actually active in this
    environment (it fails open, so this is the only way to know we are protected).
    """
    if sys.platform != "linux":
        return None
    nrs = _nrs()
    if not nrs:
        return None
    try:
        libc = _libc()
        v = libc.syscall(
            ctypes.c_long(nrs[0]),
            ctypes.c_void_p(0),  # attr = NULL
            ctypes.c_size_t(0),  # size = 0
            ctypes.c_uint32(_LANDLOCK_CREATE_RULESET_VERSION),
        )
        return int(v) if v > 0 else None
    except Exception:
        return None


def restrict_reads(allow_read_paths) -> str:
    """Restrict this process so read+execute is allowed ONLY beneath ``allow_read_paths``.

    Returns a human-readable status — ``"active (ABI vN; M/K paths)"``, ``"unsupported (...)"``,
    or ``"error: ..."`` — and never raises (fails open). Idempotent enough to be safe after
    the seccomp filters (which already set NO_NEW_PRIVS).
    """
    if sys.platform != "linux":
        return "unsupported (non-linux)"
    nrs = _nrs()
    if not nrs:
        return f"unsupported (arch {platform.machine()})"
    abi = abi_version()
    if not abi:
        return "unsupported (kernel lacks Landlock)"
    create_nr, add_nr, restrict_nr = nrs
    try:
        libc = _libc()
        libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                               ctypes.c_ulong, ctypes.c_ulong]
        libc.prctl.restype = ctypes.c_int

        attr = _RulesetAttr(handled_access_fs=_HANDLED)
        ruleset_fd = libc.syscall(
            ctypes.c_long(create_nr),
            ctypes.byref(attr),
            ctypes.c_size_t(ctypes.sizeof(attr)),
            ctypes.c_uint32(0),
        )
        if ruleset_fd < 0:
            return f"error: create_ruleset errno={ctypes.get_errno()}"

        try:
            allowed = considered = 0
            for path in allow_read_paths:
                considered += 1
                if not path or not os.path.exists(path):
                    continue
                try:
                    pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
                except OSError:
                    continue
                try:
                    pba = _PathBeneathAttr(allowed_access=_HANDLED, parent_fd=pfd)
                    # add_rule(ruleset_fd, rule_type, rule_attr, flags) — ruleset_fd is the
                    # FIRST argument; omitting it shifts every arg and the rule silently fails.
                    rc = libc.syscall(
                        ctypes.c_long(add_nr),
                        ctypes.c_int(ruleset_fd),
                        ctypes.c_uint32(_RULE_PATH_BENEATH),
                        ctypes.byref(pba),
                        ctypes.c_uint32(0),
                    )
                    if rc == 0:
                        allowed += 1
                finally:
                    os.close(pfd)

            # NO_NEW_PRIVS is mandatory before restrict_self (the seccomp filters
            # already set it; setting it again is harmless and keeps this self-contained).
            if libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
                return f"error: prctl(NO_NEW_PRIVS) errno={ctypes.get_errno()}"
            rc = libc.syscall(ctypes.c_long(restrict_nr), ctypes.c_int(ruleset_fd),
                              ctypes.c_uint32(0))
            if rc != 0:
                return f"error: restrict_self errno={ctypes.get_errno()}"
            return f"active (ABI v{abi}; {allowed}/{considered} paths)"
        finally:
            os.close(ruleset_fd)
    except Exception as exc:  # never let FS-scoping break execution
        return f"error: {type(exc).__name__}: {exc}"
