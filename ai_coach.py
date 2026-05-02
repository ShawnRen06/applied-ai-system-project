"""
AI Coach — agentic workflow powered by Claude with tool use.

The coach executes a multi-step reasoning loop:
  1. calculate_optimal_range  — narrow the valid range from guess history
  2. suggest_next_guess       — pick the binary-search midpoint
  3. evaluate_player_efficiency — score how close the player is to optimal

Claude orchestrates these tools, then synthesises a coaching message.
"""
import json
import logging
import math
import os
from dataclasses import dataclass, field
from typing import List, Optional

import anthropic

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> Optional[anthropic.Anthropic]:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — AI coach disabled")
            return None
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


@dataclass
class CoachingResult:
    message: str
    suggested_guess: Optional[int]
    confidence: float        # 0.0–1.0
    efficiency_score: int    # 0–100
    reasoning_steps: List[str] = field(default_factory=list)
    available: bool = True


# ---------------------------------------------------------------------------
# Tool implementations (pure Python, called by the agentic loop)
# ---------------------------------------------------------------------------

def _calculate_optimal_range(low: int, high: int, guess_history: list) -> dict:
    """Narrow the valid number range based on previous guesses."""
    cur_low, cur_high = low, high
    for entry in guess_history:
        guess = entry.get("guess")
        outcome = entry.get("outcome")
        if outcome == "Too High":
            cur_high = min(cur_high, guess - 1)
        elif outcome == "Too Low":
            cur_low = max(cur_low, guess + 1)
    remaining = max(0, cur_high - cur_low + 1)
    return {"current_low": cur_low, "current_high": cur_high, "remaining_numbers": remaining}


def _suggest_next_guess(current_low: int, current_high: int) -> dict:
    """Return the binary-search midpoint of the remaining range."""
    if current_low > current_high:
        return {"suggested_guess": None, "reason": "No valid numbers remain."}
    mid = (current_low + current_high) // 2
    return {
        "suggested_guess": mid,
        "reason": f"Binary-search midpoint of [{current_low}, {current_high}]",
    }


def _evaluate_player_efficiency(low: int, high: int, guess_history: list) -> dict:
    """Score the player's guesses vs the optimal binary-search path (0–100)."""
    if not guess_history:
        return {"efficiency_score": 100, "feedback": "No guesses yet — full marks!"}

    total_range = high - low + 1
    optimal_needed = math.ceil(math.log2(total_range)) if total_range > 1 else 1
    actual = len(guess_history)

    score = 100 if actual <= optimal_needed else max(0, int(100 * optimal_needed / actual))

    if score >= 80:
        feedback = "Excellent — very close to the optimal binary-search strategy!"
    elif score >= 60:
        feedback = "Good approach. Try picking the midpoint of the remaining range."
    else:
        feedback = "Tip: always guess the middle of what's still possible."

    return {
        "efficiency_score": score,
        "optimal_guesses_needed": optimal_needed,
        "actual_guesses": actual,
        "feedback": feedback,
    }


# ---------------------------------------------------------------------------
# Tool schemas (sent to Claude)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "calculate_optimal_range",
        "description": (
            "Narrow the valid range for the secret number by applying all "
            "previous guess outcomes. Returns current_low, current_high, "
            "and remaining_numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "low": {"type": "integer", "description": "Initial lower bound"},
                "high": {"type": "integer", "description": "Initial upper bound"},
                "guess_history": {
                    "type": "array",
                    "description": "List of {guess, outcome} objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "guess": {"type": "integer"},
                            "outcome": {
                                "type": "string",
                                "enum": ["Too High", "Too Low"],
                            },
                        },
                        "required": ["guess", "outcome"],
                    },
                },
            },
            "required": ["low", "high", "guess_history"],
        },
    },
    {
        "name": "suggest_next_guess",
        "description": "Return the optimal next guess using binary search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "current_low": {"type": "integer"},
                "current_high": {"type": "integer"},
            },
            "required": ["current_low", "current_high"],
        },
    },
    {
        "name": "evaluate_player_efficiency",
        "description": (
            "Score the player's guessing efficiency (0–100) compared to the "
            "optimal binary-search strategy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "low": {"type": "integer"},
                "high": {"type": "integer"},
                "guess_history": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "guess": {"type": "integer"},
                            "outcome": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["low", "high", "guess_history"],
        },
    },
]


def _dispatch_tool(name: str, inputs: dict) -> str:
    if name == "calculate_optimal_range":
        result = _calculate_optimal_range(**inputs)
    elif name == "suggest_next_guess":
        result = _suggest_next_guess(**inputs)
    elif name == "evaluate_player_efficiency":
        result = _evaluate_player_efficiency(**inputs)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a friendly, encouraging math coach for a number-guessing game.
Your job is to help the player win by analysing their strategy.

Steps you MUST follow:
1. Call calculate_optimal_range to find the remaining valid range.
2. Call suggest_next_guess using the narrowed range.
3. Call evaluate_player_efficiency to score the player.
4. Write a short, friendly coaching message (2–3 sentences).
5. End your final reply with exactly these two lines:
   COACHING: <your message>
   CONFIDENCE: <a number 0.0–1.0 representing the chance the player wins>
"""


def get_coaching(
    low: int,
    high: int,
    guess_history: list,
    attempts_left: int,
) -> CoachingResult:
    """
    Run the agentic coaching workflow.
    Returns a CoachingResult with message, suggested guess, confidence, and
    efficiency score.  Falls back gracefully when the API key is missing.
    """
    client = _get_client()
    if client is None:
        return CoachingResult(
            message="AI coach unavailable — set ANTHROPIC_API_KEY to enable.",
            suggested_guess=(low + high) // 2,
            confidence=0.5,
            efficiency_score=0,
            available=False,
        )

    history_lines = (
        "\n".join(
            f"  Guess {i + 1}: {e['guess']} → {e['outcome']}"
            for i, e in enumerate(guess_history)
        )
        or "  (no guesses yet)"
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"Game state:\n"
                f"- Original range: {low} to {high}\n"
                f"- Attempts left: {attempts_left}\n"
                f"- Guess history:\n{history_lines}\n\n"
                f"Please analyse and coach the player."
            ),
        }
    ]

    reasoning_steps: List[str] = []
    suggested_guess: Optional[int] = (low + high) // 2
    efficiency_score = 50
    confidence = 0.5

    try:
        for _ in range(8):  # safety cap on agentic iterations
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=_SYSTEM,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        step = f"{block.name}({json.dumps(block.input)})"
                        reasoning_steps.append(step)
                        logger.debug("Tool call: %s", step)

                        raw = _dispatch_tool(block.name, block.input)
                        data = json.loads(raw)

                        if block.name == "suggest_next_guess":
                            suggested_guess = data.get("suggested_guess", suggested_guess)
                        elif block.name == "evaluate_player_efficiency":
                            efficiency_score = data.get("efficiency_score", efficiency_score)

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": raw,
                            }
                        )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                final_text = "".join(
                    b.text for b in response.content if hasattr(b, "text")
                )
                coaching_msg = "Keep going — use the midpoint of the remaining range!"
                for line in final_text.splitlines():
                    line = line.strip()
                    if line.startswith("COACHING:"):
                        coaching_msg = line[len("COACHING:"):].strip()
                    elif line.startswith("CONFIDENCE:"):
                        try:
                            confidence = float(line[len("CONFIDENCE:"):].strip())
                            confidence = max(0.0, min(1.0, confidence))
                        except ValueError:
                            pass

                return CoachingResult(
                    message=coaching_msg,
                    suggested_guess=suggested_guess,
                    confidence=confidence,
                    efficiency_score=efficiency_score,
                    reasoning_steps=reasoning_steps,
                    available=True,
                )

    except Exception as exc:
        logger.error("AI coach error: %s", exc)

    return CoachingResult(
        message="AI coach hit an error — trust your instincts!",
        suggested_guess=(low + high) // 2,
        confidence=0.5,
        efficiency_score=efficiency_score,
        reasoning_steps=reasoning_steps,
        available=False,
    )
