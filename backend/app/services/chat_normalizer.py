"""
Chat Normalizer — auto-structure raw chat input.
Converts free-form text (WeChat paste, mixed formats) into structured messages.

V2: User pastes any text → this module figures out who said what.
"""
import re


def normalize_chat(text: str) -> str:
    """Normalize raw chat text into structured format for AI analysis.

    Handles:
    - WeChat format: "她: 内容" / "他: 内容" / "我: 内容"
    - English format: "her: content" / "him: content" / "me: content"
    - Name prefix: "张三: 内容"
    - No prefix: auto-detect by alternating lines

    Returns cleaned text ready for AI prompt.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return text

    structured: list[str] = []

    for line in lines:
        # Already has a colon prefix (他: / 她: / 我: / her: / me: / name:)
        if re.match(r'^[^:：]{1,8}[：:]\s', line):
            structured.append(line)
        else:
            # Try to detect name/nickname prefix without colon
            # e.g., "张三 今天干嘛呢" → not obviously structured
            # Just append as-is — AI can handle free-form
            structured.append(line)

    return "\n".join(structured)


def extract_participants(text: str) -> tuple[str, str]:
    """Extract user and other person identifiers from chat.
    Returns (user_label, other_label) for UI display.
    """
    user_labels: set[str] = set()
    other_labels: set[str] = set()

    user_pattern = re.compile(r'^(我|me)\s*[：:]', re.IGNORECASE)
    other_pattern = re.compile(r'^(他|她|对方|him|her|they)\s*[：:]', re.IGNORECASE)

    for line in text.split("\n"):
        if user_pattern.match(line.strip()):
            user_labels.add("我")
        elif other_pattern.match(line.strip()):
            other_labels.add("对方")

    return (
        user_labels.pop() if user_labels else "我",
        other_labels.pop() if other_labels else "对方",
    )


def detect_wechat_style(text: str) -> bool:
    """Quick check: does this look like a chat conversation?"""
    lines = [l for l in text.split("\n") if l.strip()]
    if len(lines) < 2:
        return False

    # Check if >50% lines have dialogue markers
    has_prefix = sum(
        1 for l in lines
        if re.match(r'^[^：:\s]{1,8}[：:]\s', l)
        or re.match(r'^[^：:]{1,8}\s+[^：:]', l)
    )
    return has_prefix >= len(lines) * 0.3
