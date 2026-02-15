"""Cover inclusion: PDF full-bleed cover page + EPUB cover-image manifest entry."""

from __future__ import annotations

import zipfile

import pytest
from PIL import Image

from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    CoverImages,
)


def _png(path, color="#88AAFF", size=(640, 960)):
    Image.new("RGB", size, color=color).save(path, format="PNG")


def _book_with_cover(tmp_path) -> BookContent:
    front = tmp_path / "front.png"
    back = tmp_path / "back.png"
    _png(front, "#446688")
    _png(back, "#88AA66")
    return BookContent(
        metadata=BookMetadata(
            title="My Book",
            target_age=8,
            page_count=10,
            genre="adventure",
            tagline="A quiet question.",
        ),
        chapters=[
            Chapter(number=1, title="Start", text="prose", page_start=3, page_end=4),
        ],
        full_text="text",
        characters_used=["Cassie"],
        cover=CoverImages(front_path=str(front), back_path=str(back)),
    )


def _book_without_cover(tmp_path) -> BookContent:
    return BookContent(
        metadata=BookMetadata(title="No Cover Book", target_age=8, page_count=10, genre="x"),
        chapters=[Chapter(number=1, title="Start", text="prose", page_start=3, page_end=4)],
        full_text="text",
        characters_used=["C"],
    )


# ----- PDF ------------------------------------------------------------------


def test_pdf_with_cover_produces_more_pages_than_without(tmp_path):
    """A book with a cover should have at least 2 extra pages (front + back)."""
    with_cover = tmp_path / "with.pdf"
    without_cover = tmp_path / "without.pdf"
    generate_pdf(_book_with_cover(tmp_path), with_cover)
    generate_pdf(_book_without_cover(tmp_path), without_cover)
    # Crude page-counter: '/Type /Page' marker count.
    with_count = with_cover.read_bytes().count(b"/Type /Page")
    without_count = without_cover.read_bytes().count(b"/Type /Page")
    assert with_count >= without_count + 2


def test_pdf_renders_without_cover_unchanged(tmp_path):
    """No cover → PDF still builds (regression check)."""
    out = tmp_path / "book.pdf"
    generate_pdf(_book_without_cover(tmp_path), out)
    assert out.stat().st_size > 1000


def test_pdf_cover_page_uses_zero_margin_frame(tmp_path):
    """`_build_page_templates` returns a cover frame at (0, 0) with no padding."""
    from fable_flow.config import config
    from fable_flow.publishers.pdf import _build_page_templates

    cover_tpl, body_tpl = _build_page_templates(config.pdf)
    cover_frame = cover_tpl.frames[0]
    page_w, page_h = config.pdf.page_size
    assert (cover_frame._x1, cover_frame._y1) == (0, 0)
    assert (cover_frame._width, cover_frame._height) == (page_w, page_h)
    # Body frame is inset by the configured margin.
    body_frame = body_tpl.frames[0]
    assert body_frame._x1 == config.pdf.margin


# ----- EPUB -----------------------------------------------------------------


def test_epub_with_cover_includes_cover_image_property(tmp_path):
    """The cover image must carry EPUB 3's `properties=\"cover-image\"` flag."""
    out = tmp_path / "with.epub"
    generate_epub(_book_with_cover(tmp_path), out)
    with zipfile.ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode()
    assert 'properties="cover-image"' in opf
    assert "images/cover_front.png" in opf
    assert "images/cover_back.png" in opf


def test_epub_cover_xhtml_is_first_in_spine(tmp_path):
    """`cover.xhtml` must come before `front_matter.xhtml` so it opens the book."""
    out = tmp_path / "with.epub"
    generate_epub(_book_with_cover(tmp_path), out)
    with zipfile.ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode()
    spine_section = opf.split("<spine>")[1].split("</spine>")[0]
    cover_idx = spine_section.index('idref="cover"')
    front_idx = spine_section.index('idref="front"')
    assert cover_idx < front_idx


def test_epub_back_cover_xhtml_is_last_in_spine(tmp_path):
    """`back_cover.xhtml` must be the final spine item."""
    out = tmp_path / "with.epub"
    generate_epub(_book_with_cover(tmp_path), out)
    with zipfile.ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode()
    spine_section = opf.split("<spine>")[1].split("</spine>")[0]
    spine_lines = [ln for ln in spine_section.splitlines() if "itemref" in ln]
    assert "back_cover" in spine_lines[-1]


def test_epub_cover_files_included_in_archive(tmp_path):
    """The PNG bytes plus the cover/back xhtml docs are written into the zip."""
    out = tmp_path / "with.epub"
    generate_epub(_book_with_cover(tmp_path), out)
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "OEBPS/images/cover_front.png" in names
    assert "OEBPS/images/cover_back.png" in names
    assert "OEBPS/cover.xhtml" in names
    assert "OEBPS/back_cover.xhtml" in names


def test_epub_without_cover_omits_cover_image_property(tmp_path):
    """No cover → no cover-image manifest entry, no cover.xhtml in archive."""
    out = tmp_path / "without.epub"
    generate_epub(_book_without_cover(tmp_path), out)
    with zipfile.ZipFile(out) as zf:
        opf = zf.read("OEBPS/content.opf").decode()
        names = set(zf.namelist())
    assert 'properties="cover-image"' not in opf
    assert "OEBPS/cover.xhtml" not in names
