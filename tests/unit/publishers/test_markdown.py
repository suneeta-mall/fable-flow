"""Tests for inline-Markdown rendering in the book publishers."""

from __future__ import annotations

import pytest

from fable_flow.publishers._markdown import to_html, to_pdf


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain text", "plain text"),
        ("**bold**", "<strong>bold</strong>"),
        ("*italic*", "<em>italic</em>"),
        ("***both***", "<strong><em>both</em></strong>"),
        ("`code`", "<code>code</code>"),
        ("~~gone~~", "<del>gone</del>"),
        ("a **b** and *c*", "a <strong>b</strong> and <em>c</em>"),
        # underscores are left alone (identifiers / filenames)
        ("book_content.json", "book_content.json"),
        ("snake_case_name", "snake_case_name"),
        # spaced asterisks are not emphasis
        ("2 * 3 = 6", "2 * 3 = 6"),
        # special chars are escaped, including inside emphasis
        ("a < b & c", "a &lt; b &amp; c"),
        ("**a & b**", "<strong>a &amp; b</strong>"),
        # emphasis markers inside code spans are inert; code content is escaped
        ("`a*b* <c>`", "<code>a*b* &lt;c&gt;</code>"),
    ],
)
def test_to_html(text: str, expected: str) -> None:
    assert to_html(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain text", "plain text"),
        ("**bold**", "<b>bold</b>"),
        ("*italic*", "<i>italic</i>"),
        ("***both***", "<b><i>both</i></b>"),
        ("`code`", '<font face="Courier">code</font>'),
        ("~~gone~~", "<strike>gone</strike>"),
        ("book_content.json", "book_content.json"),
        ("2 * 3 = 6", "2 * 3 = 6"),
        ("a < b & c", "a &lt; b &amp; c"),
        ("**a & b**", "<b>a &amp; b</b>"),
    ],
)
def test_to_pdf(text: str, expected: str) -> None:
    assert to_pdf(text) == expected


def test_multiple_bold_in_one_line() -> None:
    assert to_html("**one** two **three**") == "<strong>one</strong> two <strong>three</strong>"


def test_bold_takes_precedence_over_italic() -> None:
    # ** must be consumed as bold, not as two italics
    assert to_html("**word**") == "<strong>word</strong>"


def test_empty_string() -> None:
    assert to_html("") == ""
    assert to_pdf("") == ""
