"""Number Detective — main Streamlit application."""
import logging
import random

import streamlit as st

from logic_utils import (
    check_guess,
    get_range_for_difficulty,
    parse_guess,
    update_score,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Number Detective", page_icon="🔍")
st.title("🔍 Number Detective")
st.caption("A number guessing game with an AI-powered coach")

# --- Sidebar settings ---
st.sidebar.header("⚙️ Settings")
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
enable_coach = st.sidebar.checkbox("🤖 Enable AI Coach", value=True)

ATTEMPT_LIMITS = {"Easy": 8, "Normal": 6, "Hard": 5}
attempt_limit = ATTEMPT_LIMITS[difficulty]
low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low}–{high} | Max attempts: {attempt_limit}")


# --- Session state initialisation ---
def _reset_game(difficulty: str, low: int, high: int) -> None:
    st.session_state.difficulty = difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.coaching = None
    logger.info("New game started — difficulty=%s range=[%d,%d]", difficulty, low, high)


# Reset when difficulty changes or on first load
if "difficulty" not in st.session_state or st.session_state.difficulty != difficulty:
    _reset_game(difficulty, low, high)

if st.sidebar.button("🔁 New Game"):
    _reset_game(difficulty, low, high)
    st.rerun()


# --- Main UI ---
attempts_used = st.session_state.attempts
attempts_left = attempt_limit - attempts_used

st.info(
    f"Guess a number between **{low}** and **{high}**. "
    f"Attempts left: **{attempts_left}**"
)

with st.expander("🔧 Developer Debug Info"):
    st.json(
        {
            "secret": st.session_state.secret,
            "attempts_used": attempts_used,
            "score": st.session_state.score,
            "status": st.session_state.status,
            "difficulty": difficulty,
            "history": st.session_state.history,
        }
    )

# --- Game over ---
if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success(
            f"🎉 You won! The secret was **{st.session_state.secret}**. "
            f"Final score: **{st.session_state.score}**"
        )
    else:
        st.error(
            f"💀 Out of attempts! The secret was **{st.session_state.secret}**. "
            f"Score: **{st.session_state.score}**"
        )
    st.stop()

# --- Guess input ---
raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_{difficulty}_{len(st.session_state.history)}",
)
submit = st.button("Submit Guess 🚀")

if submit:
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.error(err)
    else:
        st.session_state.attempts += 1
        outcome, message = check_guess(guess_int, st.session_state.secret)

        st.session_state.history.append({"guess": guess_int, "outcome": outcome})
        st.session_state.score = update_score(
            st.session_state.score, outcome, st.session_state.attempts
        )

        logger.info(
            "Attempt %d: guess=%d outcome=%s score=%d",
            st.session_state.attempts,
            guess_int,
            outcome,
            st.session_state.score,
        )

        if outcome == "Win":
            st.balloons()
            st.session_state.status = "won"
            st.success(
                f"🎉 Correct! The secret was **{st.session_state.secret}**. "
                f"Final score: **{st.session_state.score}**"
            )
            st.stop()
        else:
            st.warning(message)

            if st.session_state.attempts >= attempt_limit:
                st.session_state.status = "lost"
                st.error(
                    f"💀 No attempts left! The secret was **{st.session_state.secret}**. "
                    f"Score: **{st.session_state.score}**"
                )
                st.stop()

            # Request AI coaching after a wrong guess
            if enable_coach:
                try:
                    from ai_coach import get_coaching

                    past_wrong = [
                        h for h in st.session_state.history if h["outcome"] != "Win"
                    ]
                    with st.spinner("🤖 AI Coach is thinking…"):
                        coaching = get_coaching(
                            low=low,
                            high=high,
                            guess_history=past_wrong,
                            attempts_left=attempt_limit - st.session_state.attempts,
                        )
                    st.session_state.coaching = coaching
                except Exception as exc:
                    logger.error("AI coach failed: %s", exc)
                    st.session_state.coaching = None

# --- AI Coach panel ---
if st.session_state.coaching and enable_coach:
    c = st.session_state.coaching
    if c.available:
        st.markdown("---")
        st.markdown("### 🤖 AI Coach")
        st.info(c.message)

        col1, col2 = st.columns(2)
        col1.metric("Win Confidence", f"{c.confidence:.0%}")
        col2.metric("Strategy Efficiency", f"{c.efficiency_score}/100")

        if c.suggested_guess is not None:
            st.success(f"💡 Suggested next guess: **{c.suggested_guess}**")

        if c.reasoning_steps:
            with st.expander("🔍 AI Reasoning Steps (Agentic Workflow)"):
                for i, step in enumerate(c.reasoning_steps, 1):
                    st.text(f"{i}. {step}")

# --- Guess history ---
if st.session_state.history:
    st.markdown("---")
    st.subheader("📜 Guess History")
    for i, entry in enumerate(st.session_state.history, 1):
        icon = "✅" if entry["outcome"] == "Win" else (
            "🔴" if entry["outcome"] == "Too High" else "🔵"
        )
        st.text(f"{icon} Attempt {i}: {entry['guess']} → {entry['outcome']}")

st.markdown("---")
st.caption(f"Score: {st.session_state.score} | Built with Claude AI")
