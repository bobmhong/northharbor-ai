"""Input sanitization to prevent NoSQL injection and XSS."""

from __future__ import annotations

import re
from typing import Any

_MONGO_OPERATORS = re.compile(r"^\$")


def strip_mongo_operators(data: Any) -> Any:
    """Recursively strip keys starting with ``$`` from dicts.

    Prevents NoSQL injection via MongoDB operator payloads like
    ``{"$gt": "", "$ne": ""}``.
    """
    if isinstance(data, dict):
        return {
            k: strip_mongo_operators(v)
            for k, v in data.items()
            if not _MONGO_OPERATORS.match(str(k))
        }
    if isinstance(data, list):
        return [strip_mongo_operators(item) for item in data]
    return data


def has_mongo_operators(data: Any) -> bool:
    """Return True if any dict key starts with ``$``."""
    if isinstance(data, dict):
        for k, v in data.items():
            if _MONGO_OPERATORS.match(str(k)):
                return True
            if has_mongo_operators(v):
                return True
    elif isinstance(data, list):
        return any(has_mongo_operators(item) for item in data)
    return False


_SCRIPT_TAG = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")


def escape_html(value: str) -> str:
    """Escape HTML special characters in a string value."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def strip_script_tags(value: str) -> str:
    """Remove ``<script>`` blocks from a string."""
    return _SCRIPT_TAG.sub("", value)
