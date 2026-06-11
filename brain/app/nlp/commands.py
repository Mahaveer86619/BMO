"""
BMO command routing layer.

Every voice input passes through here after STT.

Architecture: NLP-first, LLM-as-last-resort.

  Layer 1 — Social phrases (no wake word needed)
    Instant replies with no I/O. Handled by handle_direct().

  Layer 2 — Structured LUMI commands (wake word required)
    Routed by pattern matching. Each maps to a specific handler in brain.py:

      time      → time_tool.get_current_time()              (zero latency)
      weather   → weather_tool.get_weather(location)        (one HTTP call)
      search    → search_tool.search_web(query)             (one HTTP call)
      reminder  → reminder_tool.set_reminder(text, when)    (one DB write)
      help      → help_tool.get_help()                      (zero latency)
      calculate → _safe_eval(expr)                          (zero latency)
      identity  → hardcoded string                          (zero latency)

  Layer 3 — LLM fallback
      llm       → OllamaProvider.generate_response(payload) (single LLM call)
      Used for open-ended questions, creative requests, anything NLP can't classify.

  silence → input discarded (no wake word and not a social phrase)
"""

import ast
import operator
import random
import re


# ── Social patterns (no LUMI needed) ──────────────────────────────────────────

_SOCIAL = [
    ("greeting", r"\b(hi+|hello+|hey+|good (morning|afternoon|evening)|howdy)\b"),
    ("farewell", r"\b(bye+|goodbye|see (you|ya)|later|good ?night|cya)\b"),
    ("thanks",   r"\b(thanks?|thank you|cheers|appreciate it|ty)\b"),
    ("status",   r"\b(how are you|you (okay|ok|good)|are you okay)\b"),
]

_SOCIAL_REPLIES: dict[str, list[str]] = {
    "greeting": ["Hey! What's up?", "Hi there!", "Hello!"],
    "farewell": ["Bye! Come back soon.", "See you later!", "Goodbye!"],
    "thanks":   ["You're welcome!", "Happy to help!", "Anytime!"],
    "status":   ["All good here!", "Ready and buzzing!", "Doing great!"],
}

# ── LUMI intent patterns — ordered most-specific first ────────────────────────
# (regex, command)  — matched against the wake-word-stripped utterance.

_LUMI_PATTERNS = [
    # Time
    (r"\b(what.?s? the time|what time is it|what is the time|current time|time (now|right now)|tell me the time|time please)\b",
     "time"),

    # Weather
    (r"\b(weather|temperature|how (hot|cold|warm)|forecast|is it raining|will it rain|is it snowing)\b",
     "weather"),

    # Explicit web search (user says "search" / "look up")
    (r"\b(search (for|about|up)?|look up|find (info|out)?)\b",
     "search"),

    # Reminder / note
    (r"\b(remind(er)?|remind me|remember to|don.?t forget|save (a )?note|note that)\b",
     "reminder"),

    # Help
    (r"\b(help|what can you do|what do you do|your (features|abilities|commands)|how do i use you)\b",
     "help"),

    # Math
    (r"\bcalculate?\b|\bmath\b|\bwhat.?s\s+[\d\s\+\-\*\/]+",
     "calculate"),

    # Identity
    (r"\bwho\s+are\s+you\b|\byour\s+name\b|\bwhat\s+are\s+you\b",
     "identity"),
]

_DIRECT_HANDLERS = {
    "identity": lambda _: "I'm BMO — your tiny desk companion, built from budget parts and a lot of heart.",
    "greeting": lambda _: random.choice(_SOCIAL_REPLIES["greeting"]),
    "farewell": lambda _: random.choice(_SOCIAL_REPLIES["farewell"]),
    "thanks":   lambda _: random.choice(_SOCIAL_REPLIES["thanks"]),
    "status":   lambda _: random.choice(_SOCIAL_REPLIES["status"]),
}


# ── Extraction helpers ─────────────────────────────────────────────────────────

def extract_weather_location(payload: str) -> str | None:
    """Extract city/location from a weather payload. Returns None → use config default."""
    p = payload.lower().strip()
    # "weather in X" / "weather for X" / "forecast for X" — preposition required
    m = re.search(
        r"(?:weather|temperature|forecast)\s+(?:in|for|at|of)\s+([a-z][a-z\s]{1,30}?)(?:\?|$)",
        p,
    )
    if m:
        return m.group(1).strip()
    # "X weather" / "X temperature" — only if X doesn't look like a question phrase
    m = re.search(r"^([a-z][a-z\s]{1,30}?)\s+(?:weather|temperature|forecast)", p)
    if m:
        loc = m.group(1).strip()
        _Q = {"what", "how", "is", "it", "the", "a", "an", "will", "does", "do", "are"}
        if set(loc.split()) - _Q:  # at least one non-question word
            return loc
    # "how hot is it in X" / "is it raining in X"
    m = re.search(r"\b(?:in|at)\s+([a-z][a-z\s]{2,30}?)(?:\?|$|\s+(?:now|today|right now))", p)
    if m:
        return m.group(1).strip()
    return None


def extract_search_query(payload: str) -> str:
    """Strip the search verb from the payload to get the bare query."""
    clean = re.sub(
        r"^(search\s+(for|about|up\s+)?\s*|look\s+up\s*|find\s+(?:info(?:\s+(?:on|about))?\s*|out\s+about\s*)?)",
        "",
        payload,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    return clean or payload


def extract_reminder_args(payload: str) -> tuple[str, str | None]:
    """
    Split reminder payload into (reminder_text, when_string).

    Examples:
      "call mum at 5 pm"       → ("call mum", "5 pm")
      "buy milk tomorrow"      → ("buy milk", "tomorrow")
      "exercise in 30 minutes" → ("exercise", "in 30 minutes")
      "take meds"              → ("take meds", None)
    """
    when: str | None = None
    p = payload

    # Match time expressions at the end of the string
    m = re.search(
        r"\s+(at\s+[\w\s:.]+?(?:a\.?m|p\.?m)?|in\s+\d+\s+\w+|tomorrow(?:\s+\w+)?|tonight|next\s+\w+)\s*$",
        p,
        re.IGNORECASE,
    )
    if m:
        when = re.sub(r"^at\s+", "", m.group(1).strip(), flags=re.IGNORECASE).strip(" .")
        p = p[: m.start()].strip(" ,")

    # Strip leading reminder verbs
    p = re.sub(
        r"^(remind\s+(me\s+)?to\s+|reminder\s+(?:to\s+)?|remember\s+to\s+|"
        r"don.?t\s+forget\s+(?:to\s+)?|note\s+(?:that\s+)?|save\s+(?:a\s+)?note\s+)",
        "",
        p,
        flags=re.IGNORECASE,
    ).strip()

    return p or "something", when


# ── Public API ─────────────────────────────────────────────────────────────────

def route(text: str, require_lumi: bool = True) -> tuple[str, str]:
    """
    Parse transcribed text → (command, payload).

    command values:
      time | weather | search | reminder | help  → NLP tool (no LLM)
      calculate                                   → safe AST eval (no LLM)
      identity | greeting | farewell | thanks | status  → instant reply
      llm                                         → single LLM generate call
      silence                                     → discard
    """
    lower = text.lower().strip()

    # Social phrases bypass the wake word gate
    for intent, pattern in _SOCIAL:
        if re.search(pattern, lower):
            return intent, ""

    has_lumi = bool(re.search(r"\blumi\b", lower))

    if not has_lumi:
        if not require_lumi:
            # /chat endpoint: pattern-match on bare text
            for pattern, cmd in _LUMI_PATTERNS:
                if re.search(pattern, lower):
                    return cmd, lower
            return "llm", lower
        return "silence", ""

    # Strip the wake word
    stripped = re.sub(r"\blumi\b[,\s]*", "", lower, flags=re.IGNORECASE).strip(" ,.")
    if not stripped:
        return "greeting", ""

    # Match against structured intent patterns
    for pattern, cmd in _LUMI_PATTERNS:
        if re.search(pattern, stripped):
            return cmd, stripped

    # Catch-all: open-ended question or creative request → LLM
    return "llm", stripped


def handle_direct(command: str, payload: str) -> str | None:
    """
    Return an instant synchronous reply for commands that need no I/O.
    Returns None for anything that requires async work (tools or LLM).
    """
    handler = _DIRECT_HANDLERS.get(command)
    if handler:
        return handler(payload)

    if command == "calculate":
        result = _safe_eval(payload)
        if result is not None:
            return result  # raw number — format_response wraps it
        # safe_eval failed — fall through to LLM via _execute_intent

    return None


def build_llm_prompt(command: str, payload: str) -> str:
    """Kept for backward compatibility."""
    return payload


# ── Safe calculator ────────────────────────────────────────────────────────────

_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Mod:  operator.mod,
}


def _safe_eval(expr: str) -> str | None:
    # Translate word operators BEFORE stripping letters
    clean = expr.lower()
    clean = re.sub(r"\btimes\b|\bmultiplied\s+by\b",  "*", clean)
    clean = re.sub(r"\bx\b",                           "*", clean)
    clean = re.sub(r"\bplus\b",                        "+", clean)
    clean = re.sub(r"\bminus\b",                       "-", clean)
    clean = re.sub(r"\bdivided?\s+by\b|\bover\b",      "/", clean)
    clean = re.sub(r"\bsquared\b",                     "**2", clean)
    clean = re.sub(r"\bcubed\b",                       "**3", clean)
    # Strip everything that isn't a digit or math operator, collapse whitespace
    clean = re.sub(r"[^0-9\s\+\-\*\/\.\(\)\%\^]", "", clean).replace("^", "**")
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return None
    try:
        tree = ast.parse(clean, mode="eval")
        result = _eval_node(tree.body)
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return str(round(result, 6))
    except Exception:
        return None


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _OPS.get(type(node.op))
        if op is None:
            raise ValueError
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _OPS.get(type(node.op))
        if op is None:
            raise ValueError
        return op(_eval_node(node.operand))
    raise ValueError(f"Unsupported node: {type(node).__name__}")
