"""
Sia Local Intelligence Test
────────────────────────────
Calls the AI directly — no server, no auth, no DB needed.
Just needs: venv activated + GEMINI_API_KEY in .env

Run:
    cd scholaxia
    venv\\Scripts\\activate
    python test_sia_local.py
"""

import asyncio
import sys
import os

# Make sure app imports work from the scholaxia folder
sys.path.insert(0, os.path.dirname(__file__))

# Load .env manually into os.environ before importing app modules
# Use last-value-wins (same as real dotenv parsers) to handle duplicate keys
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ[key.strip()] = val.strip()  # overwrite — last value wins

from app.ai.model_backend import run_inference
from app.ai.prompt_builder import build_prompt, build_explain_prompt, build_solve_prompt

# ── Helpers ───────────────────────────────────────────────────────────────────

def divider(title):
    print(f"\n{'═'*65}")
    print(f"  {title}")
    print(f"{'═'*65}")

def show(label, text):
    print(f"\n{label}:\n{'-'*50}")
    print(text.strip())
    print()

async def ask(prompt_text, label):
    try:
        result = await run_inference(prompt_text)
        show(label, result)
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        return ""

async def ask_with_delay(prompt_text, label, delay=3):
    await asyncio.sleep(delay)
    return await ask(prompt_text, label)

# ── Tests ─────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 65)
    print("  SIA LOCAL INTELLIGENCE TEST")
    print("  Backend: Gemini  |  No server needed")
    print("=" * 65)

    # ── TEST 1: Unknown level — should ask for class ──────────────────────────
    divider("TEST 1: Unknown level — Sia should ask for class first")
    p = build_prompt(
        question="What is a noun?",
        subject="English",
        education_level="UNKNOWN",
        language="english",
        student_name="Chidi",
    )
    await ask(p, "Sia response (should ask for class)")

    # ── TEST 2: Known level — should give dual definitions ────────────────────
    divider("TEST 2: SS2 level — dual Nigerian + Cambridge definition")
    p = build_prompt(
        question="What is a noun?",
        subject="English",
        education_level="SS2",
        language="english",
        student_name="Chidi",
    )
    await ask(p, "Sia response (Nigerian + Cambridge definition)")

    # ── TEST 3: JSS1 level — simpler explanation ──────────────────────────────
    divider("TEST 3: JSS1 level — define photosynthesis")
    p = build_prompt(
        question="What is photosynthesis?",
        subject="Biology",
        education_level="JSS1",
        language="english",
        student_name="Amaka",
    )
    await ask(p, "Sia response (JSS1 level)")

    # ── TEST 4: Maths problem solving ─────────────────────────────────────────
    divider("TEST 4: SS3 — Solve a quadratic equation")
    p = build_solve_prompt(
        question="Solve: x² + 5x + 6 = 0",
        subject="Mathematics",
        education_level="SS3",
        language="english",
        student_name="Emeka",
    )
    await ask(p, "Sia response (step-by-step solve)")

    # ── TEST 5: Explain a concept ─────────────────────────────────────────────
    divider("TEST 5: SS2 — Explain Newton's Third Law")
    p = build_explain_prompt(
        topic="Newton's Third Law of Motion",
        subject="Physics",
        education_level="SS2",
        language="english",
        student_name="Fatima",
    )
    await ask(p, "Sia response (concept explanation)")

    # ── TEST 6: Pidgin language ───────────────────────────────────────────────
    divider("TEST 6: SS1 — Explain osmosis in Pidgin English")
    p = build_explain_prompt(
        topic="Osmosis",
        subject="Biology",
        education_level="SS1",
        language="pidgin",
        student_name="Tunde",
    )
    await ask(p, "Sia response (Pidgin)")

    # ── TEST 7: Conversation history — Sia should not restart ─────────────────
    divider("TEST 7: Conversation context — student follows up")
    history = [
        {"role": "user",      "content": "What is a verb?"},
        {"role": "assistant", "content": "A verb is a word that describes an action, state, or occurrence. Examples: run, is, happen."},
    ]
    p = build_prompt(
        question="Can you give me more examples?",
        subject="English",
        education_level="SS1",
        language="english",
        student_name="Ngozi",
        conversation_history=history,
    )
    await ask(p, "Sia response (should continue, not restart)")

    # ── TEST 8: JAMB exam level ───────────────────────────────────────────────
    divider("TEST 8: JAMB level — define electrochemistry")
    p = build_prompt(
        question="What is electrochemistry?",
        subject="Chemistry",
        education_level="JAMB",
        language="english",
        student_name="Bello",
    )
    await ask(p, "Sia response (JAMB depth)")

    print("=" * 65)
    print("  ALL TESTS COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
