"""Layout: page breaks before headers, ToC with back-matter, poem ornament."""

from __future__ import annotations

import zipfile

import pytest
from PIL import Image
from reportlab.platypus import KeepTogether, PageBreak, Paragraph

from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.publishers.epub import _chapter_html, _nav_html, _toc_html
from fable_flow.publishers.pdf import (
    _build_styles,
    _OutlineEntry,
    _render_chapter,
    _render_reflection,
)
from fable_flow.schemas.book_content import (
    Biography,
    BookContent,
    BookMetadata,
    Chapter,
    Experiment,
    ReflectionSection,
)


def _flatten(flow):
    """Iterate `flow` including items inside `KeepTogether` wrappers."""
    for item in flow:
        if isinstance(item, KeepTogether):
            yield from _flatten(item._content)
        else:
            yield item


def _make_png(path):
    Image.new("RGB", (320, 240), color="white").save(path)


def _full_book(tmp_path) -> BookContent:
    img = tmp_path / "ill.png"
    _make_png(img)
    return BookContent(
        metadata=BookMetadata(
            title="Cassie and the Dot",
            subtitle="A Story for the Curious",
            tagline="Some questions are very small.",
            target_age=8,
            page_count=24,
            genre="adventure",
            dedication_text="For curious children everywhere.",
        ),
        chapters=[
            Chapter(
                number=1,
                title="Morning",
                text="Cassie woke up to find the harbour was very still.",
                poem="A quiet bay,\nA waiting child,\nThe day begins.",
                page_start=3,
                page_end=6,
                reflection=ReflectionSection(
                    questions=[
                        "What did Cassie see?",
                        "Why was it quiet?",
                        "Have you watched a sunrise?",
                    ]
                ),
            ),
            Chapter(
                number=2,
                title="Discovery",
                text="At the museum, the wall of pictures stretched up.",
                poem=None,
                page_start=7,
                page_end=10,
            ),
        ],
        full_text="combined text",
        characters_used=["Cassie"],
        experiment=Experiment(
            title="Sorting Game",
            concept="Computers learn from examples.",
            materials=["paper", "pencil"],
            steps=["Draw three shapes", "Sort them by colour"],
            what_to_observe="That sorting feels easy to you but is hard to explain.",
            safety_note=None,
        ),
        biography=Biography(
            name="Fei-Fei Li",
            title="Computer Scientist",
            lifespan="1976 –",
            one_line="She taught computers to see.",
            summary="Fei-Fei grew up in Chengdu...",
            fun_facts=[
                "First woman to lead Stanford AI Lab",
                "Co-founded AI4ALL",
                "Author of The Worlds I See",
            ],
            why_inspiring="She asked audacious questions.",
        ),
        back_matter_for_parents="A short note for grown-ups about AI literacy.",
    )


# ----- PAGE BREAKS BEFORE HEADERS --------------------------------------------


def test_pdf_chapter_starts_with_page_break(tmp_path):
    """Every chapter heading begins on a new page (PageBreak flowable before)."""
    styles = _build_styles()
    chapter = Chapter(number=1, title="A", text="prose", poem=None, page_start=3, page_end=4)
    flow: list = []
    _render_chapter(flow, chapter, styles)
    assert isinstance(flow[0], PageBreak)


def test_pdf_reflection_starts_with_page_break(tmp_path):
    """`Think About It` lives on its own page."""
    styles = _build_styles()
    flow: list = []
    _render_reflection(flow, ["Q1?", "Q2?", "Q3?"], styles)
    assert isinstance(flow[0], PageBreak)
    headings = [p for p in flow if isinstance(p, Paragraph) and "Think About It" in str(p.text)]
    assert len(headings) == 1


def test_pdf_chapter_renders_reflection_after_prose(tmp_path):
    """When a chapter has both prose and reflection, reflection's page break IS in the flow."""
    styles = _build_styles()
    chapter = Chapter(
        number=1,
        title="A",
        text="prose paragraph",
        poem=None,
        page_start=3,
        page_end=4,
        reflection=ReflectionSection(questions=["Q1?", "Q2?", "Q3?"]),
    )
    flow: list = []
    _render_chapter(flow, chapter, styles)
    page_breaks = [i for i, x in enumerate(flow) if isinstance(x, PageBreak)]
    # At least two page breaks: one for the chapter, one for the reflection.
    assert len(page_breaks) >= 2


def test_epub_reflection_class_triggers_page_break(tmp_path):
    """EPUB CSS must declare `.reflection { page-break-before: always; ... }`."""
    book = _full_book(tmp_path)
    out = tmp_path / "book.epub"
    generate_epub(book, out)
    with zipfile.ZipFile(out) as zf:
        css = zf.read("OEBPS/style.css").decode()
    # The reflection rule must include page-break-before.
    assert "page-break-before" in css
    # And the .reflection selector must be one of the rules with it.
    reflection_rules = [line for line in css.split("\n") if line.lstrip().startswith(".reflection")]
    assert (
        any("page-break-before" in r for r in reflection_rules)
        or "page-break-before" in css.split(".reflection")[1].split("}")[0]
    )


def test_epub_chapter_html_uses_reflection_h2_heading(tmp_path):
    """`Think About It` is rendered as <h2> inside .reflection (h2 + class drive the page break)."""
    chapter = Chapter(
        number=1,
        title="C",
        text="x",
        page_start=3,
        page_end=4,
        reflection=ReflectionSection(questions=["Q1?", "Q2?", "Q3?"]),
    )
    html = _chapter_html(chapter, image_assets={})
    assert '<div class="reflection">' in html
    assert "<h2>Think About It</h2>" in html


# ----- POEM ORNAMENT --------------------------------------------------------


def test_pdf_poem_uses_fleuron_ornament(tmp_path):
    """PDF poem uses ─── ❦ ─── ornament dividers (replaces the old ✦ markers)."""
    styles = _build_styles()
    chapter = Chapter(
        number=1, title="A", text="prose", poem="line one\nline two", page_start=3, page_end=4
    )
    flow: list = []
    _render_chapter(flow, chapter, styles)
    text_pieces = [str(getattr(p, "text", "")) for p in _flatten(flow) if isinstance(p, Paragraph)]
    ornaments = [t for t in text_pieces if "❦" in t]
    assert len(ornaments) == 2
    assert all("───" in o for o in ornaments)


def test_pdf_poem_wrapped_in_keep_together(tmp_path):
    """Poem flowables must live inside `KeepTogether` so they don't split pages."""
    styles = _build_styles()
    chapter = Chapter(
        number=1, title="A", text="prose", poem="line one\nline two", page_start=3, page_end=4
    )
    flow: list = []
    _render_chapter(flow, chapter, styles)
    poem_groups = [item for item in flow if isinstance(item, KeepTogether)]
    assert len(poem_groups) == 1, "expected exactly one KeepTogether block (the poem)"
    inner_text = [
        str(getattr(p, "text", "")) for p in poem_groups[0]._content if isinstance(p, Paragraph)
    ]
    assert any("line one" in t for t in inner_text)
    assert any("line two" in t for t in inner_text)


def test_epub_poem_has_soft_card_styling(tmp_path):
    """EPUB poem CSS uses a soft background card + rules to read as verse."""
    book = _full_book(tmp_path)
    out = tmp_path / "book.epub"
    generate_epub(book, out)
    with zipfile.ZipFile(out) as zf:
        css = zf.read("OEBPS/style.css").decode()
    # Soft card: background + border on .poem
    poem_rule = css.split(".poem {")[1].split("}")[0]
    assert "background" in poem_rule
    assert "border-top" in poem_rule
    assert "border-bottom" in poem_rule
    assert "font-style: italic" in poem_rule


# ----- TABLE OF CONTENTS ----------------------------------------------------


def test_pdf_toc_lists_chapters_and_back_matter(tmp_path):
    """PDF Contents page mentions every chapter title and every back-matter section."""
    from fable_flow.publishers.pdf import _toc_entries

    book = _full_book(tmp_path)
    entries = _toc_entries(book)
    labels = [e[0] for e in entries]
    assert "Chapter 1: Morning" in labels
    assert "Chapter 2: Discovery" in labels
    assert "Try This at Home" in labels
    assert "Meet Fei-Fei Li" in labels
    assert "For Parents & Educators" in labels


def test_pdf_toc_omits_missing_back_matter(tmp_path):
    """A book without experiment/biography/for-parents only lists chapters."""
    from fable_flow.publishers.pdf import _toc_entries

    book = _full_book(tmp_path)
    book.experiment = None
    book.biography = None
    book.back_matter_for_parents = None
    entries = _toc_entries(book)
    labels = [e[0] for e in entries]
    assert all(label.startswith("Chapter") for label in labels)


def test_pdf_toc_entries_carry_anchor_keys(tmp_path):
    """Each ToC entry exposes the bookmark anchor key (chapter_N, experiment, …)."""
    from fable_flow.publishers.pdf import _toc_entries

    book = _full_book(tmp_path)
    entries = _toc_entries(book)
    by_label = {label: anchor for label, _page, anchor in entries}
    assert by_label["Chapter 1: Morning"] == "chapter_1"
    assert by_label["Chapter 2: Discovery"] == "chapter_2"
    assert by_label["Try This at Home"] == "experiment"
    assert by_label["Meet Fei-Fei Li"] == "biography"
    assert by_label["For Parents & Educators"] == "for_parents"


# ----- PDF OUTLINE / BOOKMARKS (viewer nav pane) ----------------------------


def test_pdf_chapter_registers_outline_entry(tmp_path):
    """Every chapter renders an `_OutlineEntry` so the viewer nav pane lists it."""
    styles = _build_styles()
    chapter = Chapter(number=1, title="Morning", text="prose", page_start=3, page_end=4)
    flow: list = []
    _render_chapter(flow, chapter, styles)
    outlines = [item for item in flow if isinstance(item, _OutlineEntry)]
    assert len(outlines) == 1
    assert outlines[0].key == "chapter_1"
    assert outlines[0].label == "Chapter 1: Morning"


def test_pdf_full_build_registers_all_outline_entries(tmp_path):
    """End-to-end PDF has bookmarks for Contents, every chapter, and every back-matter section."""
    book = _full_book(tmp_path)
    out = tmp_path / "book.pdf"
    generate_pdf(book, out)
    # Read bookmark keys directly from the rendered PDF.
    raw = out.read_bytes()
    for needle in (b"/Outlines", b"Chapter 1: Morning", b"Try This at Home", b"Meet Fei-Fei Li"):
        assert needle in raw, f"missing {needle!r} in PDF outline"


def test_pdf_toc_entries_render_as_clickable_links(tmp_path):
    """The Contents page renders each entry as a `<link href='#anchor'>` for click-nav."""
    from fable_flow.publishers.pdf import _build_front_matter

    book = _full_book(tmp_path)
    styles = _build_styles()
    flow: list = []
    _build_front_matter(flow, book, styles)
    paragraph_texts = [str(getattr(p, "text", "")) for p in flow if isinstance(p, Paragraph)]
    joined = "\n".join(paragraph_texts)
    assert 'href="#chapter_1"' in joined
    assert 'href="#chapter_2"' in joined
    assert 'href="#experiment"' in joined
    assert 'href="#biography"' in joined
    assert 'href="#for_parents"' in joined


def test_epub_toc_html_lists_chapters_and_back_matter(tmp_path):
    book = _full_book(tmp_path)
    html = _toc_html(book)
    assert "Chapter 1: Morning" in html
    assert "Chapter 2: Discovery" in html
    assert "Try This at Home" in html
    assert "Meet Fei-Fei Li" in html
    assert "For Parents &amp; Educators" in html
    # Back-matter entries get a distinguishing class.
    assert 'class="toc-back-matter"' in html


def test_epub_nav_html_lists_back_matter(tmp_path):
    book = _full_book(tmp_path)
    nav = _nav_html(book)
    assert "Try This at Home" in nav
    assert "Meet Fei-Fei Li" in nav
    assert "For Parents &amp; Educators" in nav


def test_full_epub_contains_toc_with_back_matter(tmp_path):
    """End-to-end EPUB: toc.xhtml has all entries, manifest includes everything."""
    book = _full_book(tmp_path)
    out = tmp_path / "book.epub"
    generate_epub(book, out)
    with zipfile.ZipFile(out) as zf:
        toc = zf.read("OEBPS/toc.xhtml").decode()
        opf = zf.read("OEBPS/content.opf").decode()
    assert "Try This at Home" in toc
    assert "Meet Fei-Fei Li" in toc
    assert 'href="experiment.xhtml"' in opf
    assert 'href="biography.xhtml"' in opf
    assert 'href="for_parents.xhtml"' in opf


def test_full_pdf_smoke_includes_all_sections(tmp_path):
    """End-to-end PDF: generates and contains plausible size for full book."""
    book = _full_book(tmp_path)
    out = tmp_path / "book.pdf"
    generate_pdf(book, out)
    # Non-trivial — at least the front matter + 2 chapters + experiment + bio + parents.
    assert out.stat().st_size > 4000
