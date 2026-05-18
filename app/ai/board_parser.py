"""
Board Parser
------------
Extracts structured board content from Sia's text response.
The board shows:
- Key points (bullet points)
- Calculations (step-by-step math)
- Diagrams (described as text, rendered on frontend as canvas)
- Formulas (LaTeX-style)
"""

import re
from typing import TypedDict


class BoardItem(TypedDict):
    type: str   # "heading" | "point" | "step" | "formula" | "diagram_hint"
    content: str


def extract_board_content(sia_response: str) -> list[BoardItem]:
    """
    Parse Sia's response and extract items to display on the virtual board.
    Returns a list of board items in order.
    """
    board = []
    lines = sia_response.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Numbered steps (1. 2. 3.)
        if re.match(r"^\d+\.\s+", line):
            content = re.sub(r"^\d+\.\s+", "", line)
            # Remove markdown bold
            content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
            board.append({"type": "step", "content": content})

        # Bullet points
        elif line.startswith(("- ", "• ", "* ")):
            content = line[2:].strip()
            content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
            board.append({"type": "point", "content": content})

        # Headings (bold lines or lines ending with :)
        elif re.match(r"^\*\*(.+)\*\*:?$", line) or (line.endswith(":") and len(line) < 60):
            content = re.sub(r"\*\*(.*?)\*\*", r"\1", line).rstrip(":")
            board.append({"type": "heading", "content": content})

        # Formulas — lines with =, math symbols
        elif re.search(r"[=+\-×÷/^√∫∑]", line) and len(line) < 120:
            content = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            board.append({"type": "formula", "content": content})

        # Diagram hints — lines mentioning diagrams, figures, images
        elif any(word in line.lower() for word in ["diagram", "figure", "imagine", "picture", "draw", "sketch"]):
            board.append({"type": "diagram_hint", "content": line})

    # Limit to 12 board items max
    return board[:12]
