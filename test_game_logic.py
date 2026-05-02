"""Unit tests for game logic. Run with: pytest test_game_logic.py -v"""
import pytest
from logic_utils import check_guess, get_range_for_difficulty, parse_guess, update_score


# --- check_guess ---

def test_winning_guess():
    outcome, message = check_guess(50, 50)
    assert outcome == "Win"


def test_guess_too_high():
    outcome, message = check_guess(60, 50)
    assert outcome == "Too High"


def test_guess_too_low():
    outcome, message = check_guess(40, 50)
    assert outcome == "Too Low"


def test_check_guess_win_message():
    _, message = check_guess(7, 7)
    assert "Correct" in message or "🎉" in message


def test_check_guess_too_high_message():
    _, message = check_guess(99, 1)
    assert "LOWER" in message


def test_check_guess_too_low_message():
    _, message = check_guess(1, 99)
    assert "HIGHER" in message


# --- parse_guess ---

def test_parse_valid_integer():
    ok, value, err = parse_guess("42")
    assert ok is True
    assert value == 42
    assert err is None


def test_parse_empty_string():
    ok, value, err = parse_guess("")
    assert ok is False
    assert value is None
    assert err is not None


def test_parse_none():
    ok, value, err = parse_guess(None)
    assert ok is False


def test_parse_non_number():
    ok, value, err = parse_guess("abc")
    assert ok is False
    assert err is not None


def test_parse_decimal_truncates():
    ok, value, err = parse_guess("3.9")
    assert ok is True
    assert value == 3


def test_parse_negative():
    ok, value, err = parse_guess("-5")
    assert ok is True
    assert value == -5


# --- get_range_for_difficulty ---

def test_easy_range():
    low, high = get_range_for_difficulty("Easy")
    assert low == 1
    assert high == 20


def test_normal_range():
    low, high = get_range_for_difficulty("Normal")
    assert low == 1
    assert high == 100


def test_hard_range_larger_than_normal():
    _, normal_high = get_range_for_difficulty("Normal")
    _, hard_high = get_range_for_difficulty("Hard")
    assert hard_high > normal_high


def test_unknown_difficulty_defaults_to_normal():
    low, high = get_range_for_difficulty("Impossible")
    assert low == 1
    assert high == 100


# --- update_score ---

def test_win_on_first_attempt_gives_max_points():
    score = update_score(0, "Win", 1)
    assert score == 90  # 100 - 10*1


def test_win_early_beats_win_late():
    early = update_score(0, "Win", 2)
    late = update_score(0, "Win", 7)
    assert early > late


def test_win_score_floor_is_ten():
    # attempt_number=10: 100 - 100 = 0, clamped to 10
    score = update_score(0, "Win", 10)
    assert score == 10


def test_wrong_guess_subtracts():
    score = update_score(50, "Too High", 1)
    assert score == 45


def test_too_low_subtracts():
    score = update_score(50, "Too Low", 1)
    assert score == 45


def test_unknown_outcome_unchanged():
    score = update_score(42, "Unknown", 1)
    assert score == 42
