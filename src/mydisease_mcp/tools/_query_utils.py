"""Helpers for safe Lucene query construction."""

from __future__ import annotations

import re

_FIELD_RE = re.compile(r"^[A-Za-z0-9_.]+$")
_TERM_SPECIAL_CHARS = set(r'+-!(){}[]^"~*?:\/&|')


def escape_lucene_phrase(value: str) -> str:
    """Escape a user-provided value for use inside quoted Lucene text."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def escape_lucene_term(value: str) -> str:
    """Escape a user-provided value for use as an unquoted Lucene term."""
    escaped = []
    for char in value:
        if char in _TERM_SPECIAL_CHARS or char.isspace():
            escaped.append(f"\\{char}")
        else:
            escaped.append(char)
    return "".join(escaped)


def quote_lucene_phrase(value: str) -> str:
    """Wrap escaped phrase content in quotes."""
    return f'"{escape_lucene_phrase(value)}"'


def maybe_quote_field_value(value: str) -> str:
    """Preserve existing field query style while preventing quote injection."""
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return quote_lucene_phrase(value[1:-1])
    if " " in value:
        return quote_lucene_phrase(value)
    return escape_lucene_term(value)


def validate_lucene_field_name(field_name: str) -> str:
    """Validate dynamic field names used in query syntax."""
    if not _FIELD_RE.fullmatch(field_name):
        raise ValueError(f"Invalid field name: {field_name}")
    return field_name
