from __future__ import annotations

import re
import string


SLANG_MAP = {
    "machaa": "macha",
    "macha": "friend",
    "pwoli": "awesome",
    "sheri": "ok",
    "alle": "right",
    "ishtam": "love",
    "njan": "i",
    "nee": "you",
    "entha": "what",
}


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()
    lowered = lowered.translate(str.maketrans("", "", string.punctuation))
    lowered = re.sub(r"\s+", " ", lowered)
    tokens = lowered.split(" ")
    normalized_tokens = [SLANG_MAP.get(token, token) for token in tokens]
    return " ".join(token for token in normalized_tokens if token)
