"""Shared JSON parsing for LLM responses.

LLMs return JSON in varied formats (plain, fenced, embedded in prose).
This module tries each strategy in order and returns the first valid parse.
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

_FENCED_BLOCK = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_response(response: str, expect: type = list) -> Any:
    """Extract and parse a JSON value from an LLM response.

    Strategies (tried in order):
    1. The whole response is JSON.
    2. The largest fenced code block.
    3. First JSON object/array found by bracket-matching.

    Raises ValueError if nothing parses to the expected type.
    """
    candidates = _candidates(response)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, expect):
            return value
        if expect is dict and isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    logger.error(f"Failed to parse JSON. Response head: {response[:500]!r}")
    raise ValueError(f"No valid JSON {expect.__name__} found in response")


def _candidates(response: str) -> list[str]:
    out: list[str] = [response.strip()]
    for match in _FENCED_BLOCK.findall(response):
        out.append(match.strip())

    bracket = _find_bracketed(response, "[", "]")
    if bracket:
        out.append(bracket)
    bracket = _find_bracketed(response, "{", "}")
    if bracket:
        out.append(bracket)

    return out


def _find_bracketed(text: str, open_ch: str, close_ch: str) -> str | None:
    """Return the substring from the first `open_ch` to its matching `close_ch`."""
    start = text.find(open_ch)
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
