"""Tests for Lucene query utility helpers."""

import pytest

from mydisease_mcp.tools._query_utils import (
    escape_lucene_phrase,
    escape_lucene_term,
    maybe_quote_field_value,
    quote_lucene_phrase,
    validate_lucene_field_name,
)


def test_escape_lucene_phrase_escapes_quotes_and_backslashes():
    """Phrase escaping should handle quote and backslash characters."""
    assert escape_lucene_phrase('a"b\\c') == 'a\\"b\\\\c'


def test_quote_lucene_phrase_wraps_escaped_value():
    """Quoted helper should wrap escaped phrase content."""
    assert quote_lucene_phrase('foo"bar') == '"foo\\"bar"'


def test_escape_lucene_term_escapes_special_chars():
    """Unquoted term escaping should neutralize Lucene control chars."""
    assert escape_lucene_term("MONDO:0007739") == "MONDO\\:0007739"
    assert escape_lucene_term("foo*bar?baz") == "foo\\*bar\\?baz"
    assert escape_lucene_term("a&&b||c") == "a\\&\\&b\\|\\|c"


def test_maybe_quote_field_value_branches():
    """Value helper should preserve quoted/phrase behavior and escape term values."""
    assert maybe_quote_field_value('"already quoted"') == '"already quoted"'
    assert maybe_quote_field_value("has spaces") == '"has spaces"'
    assert maybe_quote_field_value("foo?bar") == "foo\\?bar"
    assert maybe_quote_field_value("") == ""


def test_validate_lucene_field_name():
    """Field validator should reject malformed dynamic field names."""
    assert validate_lucene_field_name("mondo.id") == "mondo.id"
    assert validate_lucene_field_name("gene.symbol") == "gene.symbol"

    with pytest.raises(ValueError, match="Invalid field name"):
        validate_lucene_field_name("name OR *:*")
