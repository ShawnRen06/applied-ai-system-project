"""
Automated test harness for Number Detective.

Run with:  python test_harness.py
Exits 0 when all tests pass, 1 otherwise.

Tests are self-contained — no API key required.
"""
import math
import sys
from dataclasses import dataclass, field
from typing import Callable, List

from logic_utils import check_guess, get_range_for_difficulty, parse_guess, update_score


@dataclass
class Case:
    name: str
    fn: Callable[[], bool]


@dataclass
class HarnessReport:
    passed: int = 0
    failed: int = 0
    failures: List[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed

    @property
    def confidence(self) -> float:
        return self.passed / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Helper: simulate a full game with a given guess strategy
# ---------------------------------------------------------------------------

def _simulate_game(low: int, high: int, secret: int, use_binary_search: bool) -> int:
    """Return the number of guesses needed to find secret."""
    cur_low, cur_high = low, high
    attempts = 0
    while cur_low <= cur_high and attempts < 200:
        guess = (cur_low + cur_high) // 2 if use_binary_search else cur_low
        attempts += 1
        outcome, _ = check_guess(guess, secret)
        if outcome == "Win":
            return attempts
        if outcome == "Too High":
            cur_high = guess - 1
        else:
            cur_low = guess + 1
    return attempts


# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------

CASES: List[Case] = [
    # check_guess correctness
    Case("check_guess_win",    lambda: check_guess(50, 50)[0] == "Win"),
    Case("check_guess_high",   lambda: check_guess(60, 50)[0] == "Too High"),
    Case("check_guess_low",    lambda: check_guess(40, 50)[0] == "Too Low"),
    Case("check_guess_boundary_low",  lambda: check_guess(1, 1)[0] == "Win"),
    Case("check_guess_boundary_high", lambda: check_guess(100, 100)[0] == "Win"),
    # check_guess messages
    Case("msg_win_contains_correct",  lambda: "Correct" in check_guess(5, 5)[1] or "🎉" in check_guess(5, 5)[1]),
    Case("msg_high_says_lower",       lambda: "LOWER" in check_guess(99, 1)[1]),
    Case("msg_low_says_higher",       lambda: "HIGHER" in check_guess(1, 99)[1]),
    # parse_guess
    Case("parse_valid_int",        lambda: parse_guess("42") == (True, 42, None)),
    Case("parse_empty_string",     lambda: parse_guess("")[0] is False),
    Case("parse_none",             lambda: parse_guess(None)[0] is False),
    Case("parse_letters",          lambda: parse_guess("abc")[0] is False),
    Case("parse_decimal_truncates",lambda: parse_guess("7.9")[1] == 7),
    Case("parse_negative",         lambda: parse_guess("-3")[1] == -3),
    # difficulty ranges — Hard must be harder (bigger range) than Normal
    Case("easy_range_correct",     lambda: get_range_for_difficulty("Easy") == (1, 20)),
    Case("normal_range_correct",   lambda: get_range_for_difficulty("Normal") == (1, 100)),
    Case("hard_bigger_than_normal",lambda: get_range_for_difficulty("Hard")[1] > get_range_for_difficulty("Normal")[1]),
    Case("unknown_defaults_normal",lambda: get_range_for_difficulty("Extreme") == (1, 100)),
    # update_score
    Case("win_adds_points",        lambda: update_score(0, "Win", 1) > 0),
    Case("win_floor_is_ten",       lambda: update_score(0, "Win", 100) == 10),
    Case("wrong_subtracts_five",   lambda: update_score(50, "Too High", 1) == 45),
    Case("too_low_subtracts_five", lambda: update_score(50, "Too Low", 3) == 45),
    Case("early_win_beats_late",   lambda: update_score(0, "Win", 1) > update_score(0, "Win", 8)),
    Case("unknown_outcome_no_change", lambda: update_score(42, "Other", 1) == 42),
    # game simulation — binary search on 1-100 should always finish in ≤7 guesses
    Case("binary_search_1_100_secret_1",   lambda: _simulate_game(1, 100, 1, True) <= 7),
    Case("binary_search_1_100_secret_50",  lambda: _simulate_game(1, 100, 50, True) <= 7),
    Case("binary_search_1_100_secret_100", lambda: _simulate_game(1, 100, 100, True) <= 7),
    Case("binary_search_1_200_secret_173", lambda: _simulate_game(1, 200, 173, True) <= 8),
    # confidence: binary search is strictly better than linear on large ranges
    Case("binary_better_than_linear",
         lambda: _simulate_game(1, 100, 99, True) < _simulate_game(1, 100, 99, False)),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run() -> HarnessReport:
    report = HarnessReport()
    for case in CASES:
        try:
            passed = bool(case.fn())
        except Exception as exc:
            passed = False
            report.failures.append(f"{case.name}: raised {exc}")

        if passed:
            report.passed += 1
            print(f"  ✅  PASS  {case.name}")
        else:
            report.failed += 1
            if case.name not in report.failures:
                report.failures.append(case.name)
            print(f"  ❌  FAIL  {case.name}")

    return report


if __name__ == "__main__":
    print("=" * 56)
    print("  Number Detective — Automated Test Harness")
    print("=" * 56)
    report = run()
    print("=" * 56)
    print(f"  Results     : {report.passed}/{report.total} passed")
    print(f"  Confidence  : {report.confidence:.1%}")
    if report.failures:
        print(f"  Failures    : {', '.join(report.failures)}")
    print("=" * 56)
    sys.exit(0 if report.failed == 0 else 1)
