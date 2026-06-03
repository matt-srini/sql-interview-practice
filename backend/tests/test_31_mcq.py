"""Unit tests for the shared MCQ evaluation module (backend/mcq.py).

These are pure unit tests — no app, no HTTP client, no database required.
"""
import pytest

from mcq import correct_letter, is_mcq_correct


# ── is_mcq_correct ─────────────────────────────────────────────────────────────

def test_is_mcq_correct_matching_option():
    assert is_mcq_correct(2, {"correct_option": 2}) is True


def test_is_mcq_correct_wrong_option():
    assert is_mcq_correct(1, {"correct_option": 2}) is False


def test_is_mcq_correct_none_selection():
    assert is_mcq_correct(None, {"correct_option": 2}) is False


def test_is_mcq_correct_missing_correct_option():
    # question dict has no "correct_option" key → question.get("correct_option") is None
    # 0 != None → False
    assert is_mcq_correct(0, {}) is False


# ── correct_letter ─────────────────────────────────────────────────────────────

def test_correct_letter_a():
    assert correct_letter({"correct_option": 0}) == "A"


def test_correct_letter_b():
    assert correct_letter({"correct_option": 1}) == "B"


def test_correct_letter_c():
    assert correct_letter({"correct_option": 2}) == "C"


def test_correct_letter_d():
    assert correct_letter({"correct_option": 3}) == "D"


def test_correct_letter_raises_for_string_key():
    with pytest.raises(ValueError):
        correct_letter({"correct_option": "x"})


def test_correct_letter_raises_for_missing_key():
    with pytest.raises(ValueError):
        correct_letter({})


def test_correct_letter_raises_for_negative():
    with pytest.raises(ValueError):
        correct_letter({"correct_option": -1})
