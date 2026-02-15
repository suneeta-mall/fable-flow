"""Chapter quality: adult-led STEM depth + per-chapter poem + chapter length."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.book_assembly import ChapterStructureAgent
from fable_flow.agents.story_development import DraftStoryAgent, StoryEditorAgent
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
    FableFlowInput,
    ProjectMetadata,
    StorySeed,
)


@pytest.fixture
def spec_with_adults():
    return FableFlowInput(
        project=ProjectMetadata(title="T", target_age=7, genre="adventure"),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious",
                appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
                typical_clothing="dress",
            ),
            Character(
                name="Mum",
                age=35,
                role=CharacterRole.SUPPORTING,
                personality="patient",
                appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
                typical_clothing="cardigan",
            ),
            Character(
                name="Caleb",
                age=3,
                role=CharacterRole.SUPPORTING,
                personality="playful",
                appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
                typical_clothing="t-shirt",
            ),
        ],
        story_seed=StorySeed(theme="tides", setting="beach"),
    )


def test_adult_authority_names_picks_only_adults(spec_with_adults):
    names = DraftStoryAgent._adult_authority_names(spec_with_adults)
    # Adult (Mum) is in; Cassie (6) and Caleb (3) are not.
    assert names == ["Mum"]


def test_draft_system_prompt_summarises_chapter_quality_requirements(spec_with_adults):
    """The compat summary covers length, adult-led STEM, and per-chapter poem.

    The actual chapter-by-chapter prompts live in `_ChapterDrafter`; this is
    the at-a-glance summary used by callers (and tests) for inspection.
    """
    agent = DraftStoryAgent(model="x", word_count_target=8000)
    sys_prompt = agent._build_system_prompt(spec_with_adults)
    # Length guidance present (any reasonable range)
    assert "words per chapter" in sys_prompt
    # Adult-led explanation pattern named
    assert "Adult-led" in sys_prompt
    assert "Mum" in sys_prompt
    assert "analogy" in sys_prompt.lower()
    # Per-chapter poem requirement
    assert "poem" in sys_prompt.lower()
    assert "* * *" in sys_prompt


def test_chapter_drafter_prompt_for_real_chapter(spec_with_adults):
    """The per-chapter prompt (the one the LLM actually sees) is rich."""
    from fable_flow.agents.story_development import _ChapterDrafter
    from fable_flow.schemas.input_spec import ChapterOutlineItem

    spec_with_adults.story_seed.chapter_outline = [
        ChapterOutlineItem(number=1, title="The Beach", beats="They arrive.")
    ]
    drafter = _ChapterDrafter(model=None)
    chapter = spec_with_adults.story_seed.chapter_outline[0]
    user = drafter._user_prompt(
        chapter=chapter,
        chapter_index=0,
        total_chapters=1,
        input_spec=spec_with_adults,
        synopsis_so_far="",
        motif_for_chapter="tiny dots",
        vocab_slice=[],
        prior_draft_block="",
    )
    # Length is specified per-chapter
    assert "700" in user and "1100" in user
    # Adult-led STEM, named adult
    assert "Mum" in user
    assert "analogy" in user.lower()
    # Poem mandatory
    assert "* * *" in user
    assert "thematic poem" in user.lower()
    # Motif threaded through
    assert "tiny dots" in user


def test_draft_user_prompt_includes_provided_draft(spec_with_adults):
    """When no chapter_outline (one-shot), the provided draft is folded into the prompt."""
    spec_with_adults.story_seed.draft_story = "Initial draft seed."
    agent = DraftStoryAgent(model="x", word_count_target=200)
    # _build_generation_prompt is the compat helper; for one-shot the real
    # user prompt is built inside _draft_one_shot. The compat helper still
    # signals the user intent.
    helper = agent._build_generation_prompt(spec_with_adults)
    assert "EXPAND IT" in helper


@pytest.mark.asyncio
async def test_editor_prompt_covers_chapter_quality(spec_with_adults):
    """Editor prompt asks for motif/poem/depth verification."""
    agent = StoryEditorAgent(model="x")
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "edited"
        await agent.edit_story("draft", spec_with_adults)
    user_prompt = mock_gen.call_args.args[0]
    lower = user_prompt.lower()
    # Three signature features covered
    assert "motif" in lower
    assert "poem" in lower
    assert "analogy" in lower or "explanation" in lower
    # Adult voice named
    assert "Mum" in user_prompt


@pytest.mark.asyncio
async def test_chapter_structurer_extracts_poem_from_text_field(spec_with_adults):
    agent = ChapterStructureAgent(model="x")
    raw = """[
        {
            "number": 1,
            "title": "Morning",
            "text": "Cassie woke up early and watched the harbour come alive.",
            "poem": "Sunlight on the bay,\\nPatient as a question asked —\\nThe tide says, 'Watch me.'"
        },
        {
            "number": 2,
            "title": "Discovery",
            "text": "At the museum they saw the pixel wall and were amazed.",
            "poem": "Tiny coloured squares,\\nEach one teaches a machine\\nWhat a banana is."
        }
    ]"""

    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = raw
        chapters = await agent.structure_story("a story", spec_with_adults)

    assert chapters[0].poem is not None
    assert "Sunlight on the bay" in chapters[0].poem
    assert "\n" in chapters[0].poem  # newlines preserved
    assert chapters[1].poem is not None
    assert "Tiny coloured squares" in chapters[1].poem
    # Poem is NOT embedded in the prose
    assert "Sunlight on the bay" not in chapters[0].text


@pytest.mark.asyncio
async def test_chapter_structurer_sweeps_inline_poem_when_field_missing(spec_with_adults):
    """If the LLM leaves the poem inside `text` and omits the `poem` field, we recover."""
    agent = ChapterStructureAgent(model="x")
    raw = (
        "[{"
        '"number": 1, "title": "Only", '
        '"text": "Cassie watched the harbour.\\n\\n* * *\\nA poem inside the text\\nbecause the model forgot\\nthe poem field.\\n* * *\\n", '
        '"poem": null'
        "}]"
    )
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = raw
        chapters = await agent.structure_story("a story", spec_with_adults)

    assert chapters[0].poem is not None
    assert "A poem inside the text" in chapters[0].poem
    # The poem is no longer in the prose
    assert "A poem inside the text" not in chapters[0].text
    # And the `* * *` markers are also gone
    assert "* * *" not in chapters[0].text


@pytest.mark.asyncio
async def test_chapter_structurer_handles_missing_poem(spec_with_adults, caplog):
    """No poem → chapter still loads, warning logged."""
    agent = ChapterStructureAgent(model="x")
    raw = (
        '[{"number": 1, "title": "Bare", "text": "Just prose, no poem here at all.", "poem": null}]'
    )
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = raw
        chapters = await agent.structure_story("a story", spec_with_adults)
    assert chapters[0].poem is None
    assert chapters[0].text == "Just prose, no poem here at all."


def test_chapter_normalize_poem_drops_markers():
    cleaned = ChapterStructureAgent._normalize_poem("* * *\nLine one\nLine two\n* * *")
    assert cleaned == "Line one\nLine two"


def test_chapter_normalize_poem_returns_none_for_blank():
    assert ChapterStructureAgent._normalize_poem("   ") is None
    assert ChapterStructureAgent._normalize_poem(None) is None
    assert ChapterStructureAgent._normalize_poem("") is None


@pytest.mark.asyncio
async def test_pdf_renders_chapter_poem(tmp_path):
    """Chapter with a poem produces a PDF Paragraph carrying each poem line."""
    from reportlab.platypus import KeepTogether, Paragraph

    from fable_flow.publishers.pdf import _build_styles, _render_chapter
    from fable_flow.schemas.book_content import Chapter

    chapter = Chapter(
        number=1,
        title="Test",
        text="Some prose.",
        poem="First line\nSecond line",
        page_start=3,
        page_end=4,
    )
    styles = _build_styles()
    flow: list = []
    _render_chapter(flow, chapter, styles)

    def _flat(items):
        for it in items:
            if isinstance(it, KeepTogether):
                yield from _flat(it._content)
            else:
                yield it

    text_pieces = [str(getattr(p, "text", "")) for p in _flat(flow) if isinstance(p, Paragraph)]
    assert any("First line" in t for t in text_pieces)
    assert any("Second line" in t for t in text_pieces)
    # Fleuron ornaments appear before and after the verse
    ornament_count = sum(1 for t in text_pieces if "❦" in t)
    assert ornament_count == 2


def test_epub_renders_chapter_poem(tmp_path):
    from fable_flow.publishers.epub import _chapter_html
    from fable_flow.schemas.book_content import Chapter

    chapter = Chapter(
        number=1,
        title="Test",
        text="A line of prose.",
        poem="First line\nSecond line",
        page_start=3,
        page_end=4,
    )
    html = _chapter_html(chapter, image_assets={})
    assert '<div class="poem">' in html
    assert "First line" in html
    assert "Second line" in html
    # Two fleuron ornaments — one at top, one at bottom (the bottom carries an
    # extra `poem-ornament-bottom` modifier class).
    assert html.count("❦") == 2
    assert "poem-ornament-bottom" in html


def test_epub_omits_poem_div_when_none(tmp_path):
    from fable_flow.publishers.epub import _chapter_html
    from fable_flow.schemas.book_content import Chapter

    chapter = Chapter(number=1, title="T", text="prose only", poem=None, page_start=3, page_end=4)
    html = _chapter_html(chapter, image_assets={})
    assert '<div class="poem">' not in html
    assert "❦" not in html
