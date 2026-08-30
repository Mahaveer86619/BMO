"""
Response template pools for BMO.

Every non-social reply passes through format_response() before TTS.
Templates use {result} as the placeholder for the raw tool or LLM output.
Multiple entries per command create natural variation across turns.
"""

import random

# Repeated entries act as weights — plain {result} is intentionally
# more common for commands whose output is already well-formatted.

_TEMPLATES: dict[str, list[str]] = {

    "time": [
        "{result}",
        "Let me check the clock. {result}",
        "Right now? {result}",
        "The time — {result}",
        "I just checked. {result}",
    ],

    "weather": [
        "{result}",
        "I checked for you! {result}",
        "Here's the weather: {result}",
        "Weather update: {result}",
        "Just looked it up. {result}",
    ],

    "search": [
        "Here's what I found: {result}",
        "I looked that up. {result}",
        "{result}",
        "Good question! {result}",
        "Here's what I know about that: {result}",
    ],

    "reminder": [
        "Got it! {result}",
        "Done! {result}",
        "Noted. {result}",
        "Saved it for you. {result}",
        "All set. {result}",
    ],

    "help": [
        "{result}",
        "Sure! {result}",
        "Happy to help. {result}",
        "Here's what I can do: {result}",
    ],

    "calculate": [
        "That's {result}.",
        "The answer is {result}.",
        "{result}. There you go!",
        "Easy one! {result}.",
        "I got {result}.",
    ],

    # LLM already generates conversational text — keep plain most of the time,
    # sprinkle light lead-ins occasionally for variety.
    "llm": [
        "{result}",
        "{result}",
        "{result}",
        "Oh! {result}",
        "Hmm, {result}",
    ],
}

_DEFAULT = ["{result}"]

# Commands that go through templating. Social phrases (greeting, farewell,
# thanks, status) and identity are already personality-formatted — skip them.
TEMPLATED = frozenset(_TEMPLATES)


def format_response(command: str, result: str) -> str:
    """Pick a random template for the command and inject the result."""
    templates = _TEMPLATES.get(command, _DEFAULT)
    return random.choice(templates).format(result=result)
