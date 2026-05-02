# Number Detective 🔍

An AI-powered number guessing game with an agentic coaching system built on Claude.

---

## Original Project

**Module 2 — Glitchy Guesser / Game Glitch Investigator**

The original project was a Streamlit number-guessing game intentionally seeded with bugs: the `logic_utils.py` helper module contained only `NotImplementedError` stubs, the "New Game" button always reset the secret to `50` instead of a random number, the "Hard" difficulty range (`1–50`) was actually *easier* than Normal (`1–100`), and the unit tests asserted the wrong return type from `check_guess`. The original goal was to identify, explain, and fix these glitches as a debugging exercise.

---

## What This Project Does

Number Detective extends the original debugging exercise into a full applied-AI system. A player guesses a hidden number within a configurable range. After every wrong guess, a **Claude-powered AI Coach** analyses the guess history, runs a three-step agentic reasoning workflow using tool calls, and returns a personalised coaching message, a suggested next guess, a win-confidence score, and a strategy-efficiency rating.

---

## System Architecture

```
┌──────────────┐      guess       ┌──────────────────┐
│   Player     │ ──────────────▶  │   app.py         │
│  (Browser)   │ ◀──────────────  │  (Streamlit UI)  │
└──────────────┘    hint/score    └────────┬─────────┘
                                           │ calls
                              ┌────────────▼──────────────┐
                              │        logic_utils.py      │
                              │  parse_guess               │
                              │  check_guess               │
                              │  update_score              │
                              │  get_range_for_difficulty  │
                              └────────────┬───────────────┘
                                           │ wrong guess →
                              ┌────────────▼──────────────┐
                              │        ai_coach.py         │
                              │  (Agentic Workflow)        │
                              └─────────┬──────────────────┘
                                        │ tool calls
                    ┌───────────────────┼────────────────────┐
                    ▼                   ▼                    ▼
         calculate_optimal_    suggest_next_       evaluate_player_
         range (tool)          guess (tool)        efficiency (tool)
                    └───────────────────┼────────────────────┘
                                        │ results
                              ┌─────────▼──────────────┐
                              │   Claude Haiku API      │
                              │   (synthesises reply)   │
                              └────────────────────────┘

Testing layer (no API calls required)
  test_game_logic.py  ──▶  pytest (22 unit tests)
  test_harness.py     ──▶  standalone script (29 scenario tests)
```

**Data flow:**
1. Player submits a guess via the Streamlit UI.
2. `app.py` delegates validation and scoring to `logic_utils.py`.
3. On a wrong guess, `app.py` calls `ai_coach.get_coaching()`.
4. The coach sends the game state to Claude with three registered tools.
5. Claude calls the tools in sequence, then synthesises a final message.
6. The coaching panel (message, confidence, efficiency, suggested guess, reasoning steps) is rendered back in the UI.

---

## Setup Instructions

### 1 — Clone and enter the directory

```bash
git clone https://github.com/ShawnRen06/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2 — Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3 — Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

The app runs without a key — the AI coach panel simply shows an "unavailable" message, and all game logic still works normally.

### 4 — Run the app

```bash
streamlit run app.py
```

### 5 — Run the tests

```bash
# Unit tests (pytest)
python3 -m pytest test_game_logic.py -v

# Automated harness (standalone, no API key required)
python3 test_harness.py
```

---

## Sample Interactions

### Example 1 — Correct guess

```
Range: 1–100 | Attempts left: 6
Player types: 50  → ✅ Correct! Score: 90
```

### Example 2 — AI coach after a wrong guess

```
Range: 1–100 | Attempt 1: guess 30 → Too Low
──────────────────────────────────────────
🤖 AI Coach
  "Great start! Since 30 was too low, the number is between 31 and 100.
   Try the midpoint — it cuts your remaining possibilities in half."

  Win Confidence   : 83%
  Strategy Efficiency: 100/100
  💡 Suggested next guess: 65

  🔍 AI Reasoning Steps (Agentic Workflow)
    1. calculate_optimal_range({"low": 1, "high": 100, "guess_history": [...]})
    2. suggest_next_guess({"current_low": 31, "current_high": 100})
    3. evaluate_player_efficiency({"low": 1, "high": 100, "guess_history": [...]})
```

### Example 3 — Game lost

```
Range: 1–200 | All 5 attempts used
💀 Out of attempts! The secret was 147. Score: -15
```

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Agentic tool-use over a single prompt | Exposes observable intermediate steps; each tool can be unit-tested in isolation |
| Claude Haiku for the coach | Low latency and cost for interactive feedback; quality is sufficient for short coaching messages |
| Graceful degradation without API key | Game logic works fully offline; AI coach shows a clear "unavailable" notice |
| `logic_utils.py` as pure functions | Makes unit testing trivial — no Streamlit or API dependencies in game logic |
| Hard difficulty = range 1–200 | Fixed the original bug where Hard (1–50) was easier than Normal (1–100) |
| `update_score` floor of 10 | Ensures winning always earns points, even on the last attempt |

---

## Testing Summary

### Unit tests (`test_game_logic.py`) — 22 tests, 22 passed

Covers every branch of `check_guess`, `parse_guess`, `get_range_for_difficulty`, and `update_score`, including boundary values, decimal input truncation, and score floor clamping.

### Automated harness (`test_harness.py`) — 29 tests, 29 passed

Extends unit coverage with full-game simulations. Confirms that binary search always finds the secret in the allowed number of attempts across Easy, Normal, and Hard ranges, and that it is strictly faster than linear guessing on large ranges. Confidence score: **100%**.

**What worked:** separating game logic into pure functions made everything testable without mocking. The agentic tool calls are also unit-tested independently of the API.

**What didn't:** early versions of the AI coach occasionally skipped the `evaluate_player_efficiency` tool call when the history was empty; a guard in the system prompt resolved this.

---

## Reflection and Ethics

**Limitations and biases:**
The AI coach optimises purely for binary search efficiency. A player who uses intuition or pattern recognition may receive advice that conflicts with their style. The model has no memory across games, so coaching does not improve over time.

**Misuse potential:**
The coach reveals the optimal next guess, which trivialises the game if followed blindly. This is an intentional trade-off for a teaching context; a competitive version should hide the suggested guess behind an opt-in "hint" button.

**Surprises during testing:**
Claude occasionally expressed *more* confidence than warranted when only one attempt remained. Adding `attempts_left` explicitly to the prompt reduced over-optimism.

**Collaboration with AI:**
- *Helpful suggestion:* During development, Claude suggested structuring the agentic loop with an explicit iteration cap (`for _ in range(8)`) to prevent infinite tool-call loops — a subtle reliability issue I had not considered.
- *Flawed suggestion:* Claude initially suggested using `altair<5` as a hard pin in `requirements.txt` (copied from the original project). This was unnecessary since the newer `altair` version is compatible, and the pin would have caused install conflicts on some systems.

**What this project taught me about AI and problem-solving:**

The most important lesson was that AI reliability is not binary — it is a spectrum you actively design for. Wrapping Claude in a tool-use loop forced me to think about *when* the AI is acting vs. *when* it is reasoning, and to test each layer independently. I also learned that separating pure logic (game rules) from AI-dependent logic (coaching) made the whole system far easier to debug and verify: I could confirm the game worked correctly before introducing any API calls. More broadly, this project showed me that the hardest part of building an AI system is not getting the model to produce a good answer — it is structuring the inputs, outputs, and fallbacks so the system behaves predictably even when the model is slow, overconfident, or unavailable.

---

## File Structure

```
applied-ai-system-project/
├── app.py              # Streamlit UI — game loop and coach integration
├── logic_utils.py      # Pure game logic (no UI or API dependencies)
├── ai_coach.py         # Agentic coaching workflow using Claude tool use
├── test_game_logic.py  # pytest unit tests (22 tests)
├── test_harness.py     # Standalone scenario harness (29 tests)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```
