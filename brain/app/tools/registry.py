"""
Tool registry for BMO's LLM tool-calling pipeline.

TOOL_DEFINITIONS — passed to Ollama /api/chat so the model can request tools.
execute()        — dispatches a tool call by name and returns the result string.
"""

import json
import logging
from app.tools import time_tool, weather_tool, search_tool, help_tool, reminder_tool

log = logging.getLogger("bmo.tools")

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local date and time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city or location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location (e.g. 'London', 'New York').",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for specific facts, current events, or real-time information you cannot answer from training knowledge. Do NOT use for jokes, creative tasks, opinions, greetings, or general knowledge you already have.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Save a reminder for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "What to remind the user about.",
                    },
                    "when": {
                        "type": "string",
                        "description": "When to remind, in natural language (optional). E.g. 'at 5 pm', 'tomorrow morning'.",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_help",
            "description": "List what BMO can do and give usage examples.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


async def execute(name: str, arguments: dict | str) -> str:
    # Ollama sometimes returns arguments as a JSON string instead of a dict
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            arguments = {}

    log.info("Tool call: %s(%s)", name, arguments)

    if name == "get_current_time":
        return time_tool.get_current_time()

    if name == "get_weather":
        return await weather_tool.get_weather(arguments.get("location"))

    if name == "search_web":
        query = arguments.get("query", "")
        if not query:
            return "No search query provided."
        return await search_tool.search_web(query)

    if name == "set_reminder":
        text = arguments.get("text", "")
        if not text:
            return "No reminder text provided."
        return await reminder_tool.set_reminder(text, arguments.get("when"))

    if name == "get_help":
        return help_tool.get_help()

    return f"Unknown tool: {name!r}"
