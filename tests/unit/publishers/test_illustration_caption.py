"""Reader-facing captions must come from `caption`, never `description`.

`description` is the internal image-gen prompt (full of appearance details and
art-direction language). It must never leak into the rendered book.
"""

from __future__ import annotations

import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from fable_flow.agents.book_assembly import IllustrationPlacementAgent
from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    IllustrationSpec,
)
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)

PROMPT_LEAK_MARKER = "warm honey-brown skin"


@pytest.fixture
def characters():
    return [
        Character(
            name="Cassie",
            age=6,
            role=CharacterRole.PROTAGONIST,
            personality="curious",
            appearance=Appearance(
                heritage="Indian Australian",
                skin_tone="warm honey-brown",
                hair="black",
                eyes="brown",
            ),
            typical_clothing="dress",
        )
    ]


def _book_with_illustration(image_path, *, caption: str | None) -> BookContent:
    return BookContent(
        metadata=BookMetadata(title="Test Book", target_age=6, page_count=8, genre="adventure"),
        chapters=[
            Chapter(
                number=1,
                title="One",
                text="Cassie watched the harbour.",
                page_start=3,
                page_end=6,
                illustrations=[
                    IllustrationSpec(
                        page=4,
                        placement="inline",
                        description=(
                            f"Cassie ({PROMPT_LEAK_MARKER}, wavy black hair) "
                            "at the window, golden sunrise"
                        ),
                        caption=caption,
                        scene_context="morning, window",
                    )
                ],
            )
        ],
        full_text="Cassie watched the harbour.",
        characters_used=["Cassie"],
    )


def _make_png(path):
    Image.new("RGB", (320, 240), color="white").save(path)


@pytest.mark.asyncio
async def test_placement_agent_parses_caption(characters):
    chapters = [Chapter(number=1, title="A", text="t", page_start=3, page_end=5)]
    agent = IllustrationPlacementAgent(model="x")
    response = """{
        "chapters": [{
            "chapter_number": 1,
            "illustrations": [{
                "page": 4,
                "placement": "full_page",
                "description": "Cassie with warm honey-brown skin at sunrise window",
                "caption": "Cassie watches the morning unfold over Sydney Harbor.",
                "characters": ["Cassie"],
                "scene_context": "morning, window, hopeful"
            }]
        }]
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = response
        updated = await agent.place_illustrations(chapters, characters, target_age=6)

    spec = updated[0].illustrations[0]
    assert spec.caption == "Cassie watches the morning unfold over Sydney Harbor."
    # description and caption are independent
    assert "warm honey-brown" in spec.description


@pytest.mark.asyncio
async def test_placement_agent_handles_missing_caption(characters):
    """If the LLM forgets the caption field, IllustrationSpec.caption stays None."""
    chapters = [Chapter(number=1, title="A", text="t", page_start=3, page_end=5)]
    agent = IllustrationPlacementAgent(model="x")
    response = """{
        "chapters": [{
            "chapter_number": 1,
            "illustrations": [{
                "page": 4,
                "placement": "full_page",
                "description": "An illustration",
                "characters": ["Cassie"],
                "scene_context": "morning"
            }]
        }]
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = response
        updated = await agent.place_illustrations(chapters, characters, target_age=6)

    assert updated[0].illustrations[0].caption is None


def _captured_caption_texts(story_flow) -> list[str]:
    """Pull the text out of every Paragraph flowable in the order it was added."""
    from reportlab.platypus import Paragraph

    return [str(p.text) for p in story_flow if isinstance(p, Paragraph)]


def test_pdf_renders_caption_not_description(tmp_path):
    """The reader-facing caption flowable carries `caption`, never `description`."""
    from fable_flow.publishers.pdf import _build_styles, _render_illustration

    img = tmp_path / "img.png"
    _make_png(img)
    spec = IllustrationSpec(
        page=4,
        placement="inline",
        description=f"Cassie ({PROMPT_LEAK_MARKER}) at sunrise window",
        caption="A quiet morning by the harbour.",
        scene_context="morning",
        image_path=str(img),
    )
    styles = _build_styles()
    flow: list = []
    _render_illustration(flow, spec, styles)

    text_pieces = _captured_caption_texts(flow)
    assert "A quiet morning by the harbour." in text_pieces
    assert all(PROMPT_LEAK_MARKER not in t for t in text_pieces)


def test_pdf_emits_no_caption_flowable_when_caption_missing(tmp_path):
    """When `caption` is None, no caption Paragraph is added — just the image."""
    from reportlab.platypus import Paragraph

    from fable_flow.publishers.pdf import _build_styles, _render_illustration

    img = tmp_path / "img.png"
    _make_png(img)
    spec = IllustrationSpec(
        page=4,
        placement="inline",
        description=f"Cassie ({PROMPT_LEAK_MARKER}) at sunrise window",
        caption=None,
        scene_context="morning",
        image_path=str(img),
    )
    styles = _build_styles()
    flow: list = []
    _render_illustration(flow, spec, styles)

    paragraphs = [f for f in flow if isinstance(f, Paragraph)]
    assert paragraphs == []  # no caption paragraph added
    # And just to be paranoid, the description never appears anywhere as text
    assert all(PROMPT_LEAK_MARKER not in str(getattr(f, "text", "")) for f in flow)


def test_pdf_smoke_renders(tmp_path):
    """generate_pdf still produces a non-trivial file with and without caption."""
    img = tmp_path / "img.png"
    _make_png(img)
    for caption in ("A quiet morning.", None):
        book = _book_with_illustration(str(img), caption=caption)
        book.chapters[0].illustrations[0].image_path = str(img)
        out = tmp_path / f"book-{'caption' if caption else 'nocaption'}.pdf"
        generate_pdf(book, out)
        assert out.exists() and out.stat().st_size > 1000


def test_epub_uses_caption_and_alt_safely(tmp_path):
    img = tmp_path / "img.png"
    _make_png(img)
    caption = "A quiet morning by the harbour."
    book = _book_with_illustration(str(img), caption=caption)
    book.chapters[0].illustrations[0].image_path = str(img)

    epub_path = tmp_path / "book.epub"
    generate_epub(book, epub_path)

    with zipfile.ZipFile(epub_path) as zf:
        ch1 = zf.read("OEBPS/chapter_1.xhtml").decode()

    assert caption in ch1
    # The image-gen prompt must NEVER appear in the rendered book
    assert PROMPT_LEAK_MARKER not in ch1
    # alt text falls back to caption, not description
    assert f'alt="{caption}"' in ch1


def test_epub_omits_caption_div_when_caption_missing(tmp_path):
    img = tmp_path / "img.png"
    _make_png(img)
    book = _book_with_illustration(str(img), caption=None)
    book.chapters[0].illustrations[0].image_path = str(img)

    epub_path = tmp_path / "book.epub"
    generate_epub(book, epub_path)

    with zipfile.ZipFile(epub_path) as zf:
        ch1 = zf.read("OEBPS/chapter_1.xhtml").decode()

    assert PROMPT_LEAK_MARKER not in ch1
    # No caption div when caption is missing
    assert '<div class="caption">' not in ch1
    # The image is still there
    assert "<img" in ch1
