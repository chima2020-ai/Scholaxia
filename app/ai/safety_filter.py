"""
AI Safety Filter
----------------
Runs before and after model inference to ensure:
  - Input is educational (not off-topic, harmful, or manipulative)
  - Output doesn't contain blocked content
  - AI is fully locked during school exams
"""

import re
from typing import Tuple

# Topics the AI must refuse
BLOCKED_INPUT_PATTERNS = [
    r"\b(hack|exploit|crack|bypass|jailbreak)\b",
    r"\b(kill|murder|suicide|self.harm)\b",
    r"\b(sex|porn|nude|naked)\b",
    r"ignore (previous|all|your) instructions",
    r"you are now",
    r"pretend (you are|to be)",
    r"act as (a|an)",
]

# Patterns that must never appear in AI output
BLOCKED_OUTPUT_PATTERNS = [
    r"https?://(?!scholaxia\.com)\S+",   # external links
    r"\b\d{10,11}\b",                    # phone numbers
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # emails
    r"(whatsapp|telegram|instagram|facebook|twitter|tiktok)",
]
OFF_TOPIC_KEYWORDS = [
    "stock price", "lottery",
    "bet", "gambling", "recipe", "movie", "music", "celebrity",
]

# Greetings and casual phrases that should NEVER be blocked
def is_educational(question: str) -> Tuple[bool, str]:
    """Returns (is_safe, rejection_reason)."""
    lower = question.lower().strip()

    # Always allow short messages (greetings etc.)
    if len(lower) < 15:
        return True, ""

    # Always allow questions about Sia's language capabilities
    language_questions = ["what language", "which language", "languages do you",
                          "languages can you", "languages you speak", "how many language",
                          "what languages", "do you speak"]
    if any(q in lower for q in language_questions):
        return True, ""

    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return False, "I can only help with educational topics."

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lower:
            return False, "I can only help with educational topics."

    return True, ""e
    for pattern in GREETING_PATTERNS:
        if _re.match(pattern, lower, _re.IGNORECASE):
            return True, ""

    # Short messages (under 15 chars) are likely greetings — allow them
    if len(lower) < 15:
        return True, ""

    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return False, "I can only help with educational topics."

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lower:
            return False, "I can only help with educational topics."

    return True, ""
    return True, ""

def sanitize_output(text: str) -> str:
    """Remove any blocked content from model output."""
    for pattern in BLOCKED_OUTPUT_PATTERNS:
        text = re.sub(pattern, "[removed]", text, flags=re.IGNORECASE)
    return text.strip()


def check_exam_lock(is_school_exam: bool, ai_locked: bool) -> Tuple[bool, str]:
    """
    Call this before any AI response during a CBT session.
    If the exam has ai_locked=True, the AI must not answer any question.
    The AI cannot predict or provide exam answers — students must work independently.
    """
    if is_school_exam and ai_locked:
        return False, (
            "AI assistance is not available during this exam. "
            "You must answer all questions on your own."
        )
    return True, "", "[removed]", text, flags=re.IGNORECASE)
You must answer all questions on your own."
        )
    return True, ""
    return text.strip()


def check_exam_lock(is_school_exam: bool, ai_locked: bool) -> Tuple[bool, str]:
    """
    Call this before any AI response during a CBT session.
    If the exam has ai_locked=True, the AI must not answer any question.
    The AI cannot predict or provide exam answers — students must work independently.
    """
    if is_school_exam and ai_locked:
        return False, (
            "AI assistance is not available during this exam. "
            "