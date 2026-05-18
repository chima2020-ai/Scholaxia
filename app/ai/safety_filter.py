"""
AI Safety Filter
----------------
Runs before and after model inference to ensure:
  - Input is educational (not off-topic, harmful, or manipulative)
  - Output doesn't contain blocked content
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
    "who is the president", "weather", "stock price", "lottery",
    "bet", "gambling", "recipe", "movie", "music", "celebrity",
]


def is_educational(question: str) -> Tuple[bool, str]:
    """Returns (is_safe, rejection_reason)."""
    lower = question.lower()

    for pattern in BLOCKED_INPUT_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return False, "I can only help with educational topics."

    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lower:
            return False, "I can only help with educational topics."

    return True, ""


def sanitize_output(text: str) -> str:
    """Remove any blocked content from model output."""
    for pattern in BLOCKED_OUTPUT_PATTERNS:
        text = re.sub(pattern, "[removed]", text, flags=re.IGNORECASE)
    return text.strip()
