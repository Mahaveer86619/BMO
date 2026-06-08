import re
import random
from datetime import datetime

# Patterns are checked in order; first match wins.
_PATTERNS: list[tuple[str, list[str]]] = [
    ("greeting",  [r"\b(hi+|hello|hey+|good (morning|afternoon|evening)|howdy)\b"]),
    ("farewell",  [r"\b(bye+|goodbye|see (you|ya)|later|good ?night|cya)\b"]),
    ("thanks",    [r"\b(thanks|thank you|cheers|appreciate it|ty)\b"]),
    ("status",    [r"\bhow are you\b", r"\byou (okay|ok|good|fine|alright)\b", r"\bare you (okay|ok)\b"]),
    ("time",      [r"\bwhat(\'s| is) the time\b", r"\bwhat time is it\b", r"\bcurrent time\b"]),
    ("identity",  [r"\b(who|what) are you\b", r"\byour name\b"]),
    ("help",      [r"\bwhat can you do\b", r"\bhelp\b", r"\bcommands?\b"]),
]

_RESPONSES: dict[str, list[str]] = {
    "greeting": [
        "Hey! What's on your mind?",
        "Hi there! What's up?",
        "Hello! Good to hear you.",
    ],
    "farewell": [
        "Bye! Come back soon.",
        "See you later!",
        "Goodbye!",
    ],
    "thanks": [
        "You're welcome!",
        "Happy to help!",
        "Anytime!",
    ],
    "status": [
        "All good here, just waiting on you.",
        "Ready and buzzing!",
        "Doing great, thanks for asking!",
    ],
    "identity": [
        "I'm BMO, your tiny desk companion built from budget parts!",
        "BMO here — small but mighty, running on a Raspberry Pi Pico W.",
    ],
    "help": [
        "You can talk to me about anything! I'll do my best to respond.",
        "Just say what's on your mind — I'll chat, answer questions, or just listen.",
    ],
}


def detect_intent(text: str) -> str | None:
    text_lower = text.lower().strip()
    for intent, patterns in _PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return intent
    return None


def handle_intent(intent: str) -> str | None:
    if intent == "time":
        return f"It's {datetime.now().strftime('%I:%M %p')} right now."
    responses = _RESPONSES.get(intent)
    return random.choice(responses) if responses else None
