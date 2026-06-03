"""Single source of truth for MCQ answer evaluation across all tracks.

``correct_option`` is a **0-indexed** integer into a question's ``options`` list:
``0 -> A, 1 -> B, 2 -> C, 3 -> D`` — matching what the frontend renders
(``String.fromCharCode(65 + i)`` in ``MCQPanel.js``).

This module is the ONLY place the platform decides whether a chosen option is
correct, and the ONLY place that maps the stored key to its canonical A/B/C/D
letter. Every MCQ track router, the sample router, and the mock evaluator route
through here so no track can re-implement the comparison and drift (e.g. a
1-indexed-vs-0-indexed mismatch). "Tag the correct answer by letter" — the
human-facing identity of a key — is realised by :func:`correct_letter`.
"""

from __future__ import annotations

from typing import Any, Optional


def is_mcq_correct(selected_option: Optional[int], question: dict[str, Any]) -> bool:
    """Return ``True`` iff the selected 0-indexed option is the keyed answer.

    A missing selection (``None``) is never correct. This is the canonical
    MCQ check used by every track — do not inline the comparison elsewhere.
    """
    if selected_option is None:
        return False
    return selected_option == question.get("correct_option")


def correct_letter(question: dict[str, Any]) -> str:
    """Return the keyed answer as its canonical letter (``A``/``B``/``C``/``D``).

    This is the authoritative, human-facing identity of an MCQ key — it matches
    the option label the user sees. Raises ``ValueError`` if ``correct_option``
    is not a valid non-negative index, so a malformed key fails loudly rather
    than silently mislabelling the answer.
    """
    correct_option = question.get("correct_option")
    if not isinstance(correct_option, int) or isinstance(correct_option, bool) or correct_option < 0:
        raise ValueError(
            f"correct_option must be a non-negative int index, got {correct_option!r}"
        )
    return chr(ord("A") + correct_option)
