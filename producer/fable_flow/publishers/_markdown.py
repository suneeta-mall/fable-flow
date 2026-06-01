"""Inline-Markdown rendering for the book publishers.

The story text produced upstream contains inline Markdown — bold ``**…**``,
italic ``*…*``, inline code `` `…` ``, and strikethrough ``~~…~~``. This module
converts that markup to the target backend's inline tags so it renders as
formatting rather than literal asterisks:

- :func:`to_html` → HTML for the EPUB publisher (``<strong>``, ``<em>``,
  ``<code>``, ``<del>``)
- :func:`to_pdf` → ReportLab ``Paragraph`` mini-markup for the PDF publisher
  (``<b>``, ``<i>``, ``<font face="Courier">``, ``<strike>``)

Both backends treat ``&``, ``<`` and ``>`` as special, so the source text is
XML-escaped first; the emphasis markers (``*``, `` ` ``, ``~``) survive escaping
and are converted afterwards. Only inline emphasis is handled — block structure
(paragraphs, lists) is the caller's job.

Underscore emphasis (``_x_``) is deliberately NOT supported, so identifiers and
file names like ``book_content.json`` are left untouched.
"""

from __future__ import annotations

import re
from collections.abc import Callable

# Code spans first (and not across line breaks) so emphasis inside them is inert.
_CODE = re.compile(r"`([^`\n]+)`")
_BOLD_ITALIC = re.compile(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*", re.DOTALL)
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.DOTALL)
_ITALIC = re.compile(r"\*(?=\S)(.+?)(?<=\S)\*", re.DOTALL)
_STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.DOTALL)
_PLACEHOLDER = re.compile("\x00(\\d+)\x00")


def _escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _convert(
    text: str,
    *,
    bold: Callable[[str], str],
    italic: Callable[[str], str],
    code: Callable[[str], str],
    strike: Callable[[str], str],
) -> str:
    stashed: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        stashed.append(code(_escape_xml(match.group(1))))
        return f"\x00{len(stashed) - 1}\x00"

    work = _CODE.sub(_stash, text)
    work = _escape_xml(work)
    work = _BOLD_ITALIC.sub(lambda m: bold(italic(m.group(1))), work)
    work = _BOLD.sub(lambda m: bold(m.group(1)), work)
    work = _ITALIC.sub(lambda m: italic(m.group(1)), work)
    work = _STRIKE.sub(lambda m: strike(m.group(1)), work)
    return _PLACEHOLDER.sub(lambda m: stashed[int(m.group(1))], work)


def to_html(text: str) -> str:
    """Render inline Markdown in ``text`` as EPUB-safe HTML."""
    return _convert(
        text,
        bold=lambda s: f"<strong>{s}</strong>",
        italic=lambda s: f"<em>{s}</em>",
        code=lambda s: f"<code>{s}</code>",
        strike=lambda s: f"<del>{s}</del>",
    )


def to_pdf(text: str) -> str:
    """Render inline Markdown in ``text`` as ReportLab ``Paragraph`` markup."""
    return _convert(
        text,
        bold=lambda s: f"<b>{s}</b>",
        italic=lambda s: f"<i>{s}</i>",
        code=lambda s: f'<font face="Courier">{s}</font>',
        strike=lambda s: f"<strike>{s}</strike>",
    )
