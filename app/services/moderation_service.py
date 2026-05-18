import re
from typing import Tuple

# Strict bad word list — extend as needed
BAD_WORDS = [
    "spam", "scam", "whatsapp", "telegram", "instagram", "facebook",
    "follow me", "dm me", "call me", "my number", "phone number",
    "click here", "free money", "send me",
]

# Patterns that indicate sharing personal/social info
PERSONAL_INFO_PATTERNS = [
    r"\b\d{10,11}\b",                          # phone numbers
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # emails
    r"(wa\.me|t\.me|ig\.com|fb\.com)",         # social media links
    r"https?://(?!scholaxia\.com)\S+",         # external links
]


async def check_message_content(content: str) -> Tuple[bool, str]:
    """
    Returns (is_flagged, reason).
    Checks for bad words, personal info, social media links.
    """
    lower = content.lower()

    for word in BAD_WORDS:
        if word in lower:
            return True, f"Message contains prohibited content: '{word}'"

    for pattern in PERSONAL_INFO_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True, "Message contains personal information or external links"

    return False, ""
