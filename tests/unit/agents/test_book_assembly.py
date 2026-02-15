from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.book_assembly import (
    ChapterStructureAgent,
    IllustrationGeneratorAgent,
    IllustrationPlacementAgent,
    build_character_visual_map,
    create_book_content,
)
from fable_flow.schemas.book_content import Chapter, IllustrationSpec
from fable_flow.schemas.input_spec import (
    Appearance,
    BookProductionConfig,
    Character,
    CharacterRole,
    FableFlowInput,
    ProductionConfig,
    ProjectMetadata,
    StorySeed,
)


@pytest.fixture
def sample_input_spec():
    return FableFlowInput(
        project=ProjectMetadata(title="Beach Story", target_age=6, genre="adventure"),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="black wavy",
                    eyes="brown",
                ),
                typical_clothing="sundress",
            ),
            Character(
                name="Caleb",
                age=3,
                role=CharacterRole.SUPPORTING,
                personality="playful",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="curly black",
                    eyes="brown",
                ),
                typical_clothing="striped shirt",
            ),
        ],
        story_seed=StorySeed(theme="ocean exploration", setting="beach"),
        production_config=ProductionConfig(book=BookProductionConfig(page_count_target=24)),
    )


def test_visual_map_includes_all_characters(sample_input_spec):
    visual = build_character_visual_map(sample_input_spec.characters)
    assert set(visual.keys()) == {"Cassie", "Caleb"}
    assert "Indian Australian" in visual["Cassie"]
    assert "sundress" in visual["Cassie"]


@pytest.mark.asyncio
async def test_chapter_structure_honours_outline_when_provided(sample_input_spec):
    """If story_seed.chapter_outline is set, the prompt instructs the LLM to use it."""
    from fable_flow.schemas.input_spec import ChapterOutlineItem

    sample_input_spec.story_seed.chapter_outline = [
        ChapterOutlineItem(number=1, title="Outlined Opening", beats="The story begins."),
        ChapterOutlineItem(number=2, title="Outlined Climax", beats="Things happen."),
    ]
    agent = ChapterStructureAgent(model="x")
    response = (
        '[{"number": 1, "title": "Outlined Opening", "text": "x"},'
        '{"number": 2, "title": "Outlined Climax", "text": "y"}]'
    )
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = response
        chapters = await agent.structure_story("some story", sample_input_spec)

    prompt = mock_gen.call_args.args[0]
    assert "REQUIRED chapter outline" in prompt
    assert "Outlined Opening" in prompt
    assert "Outlined Climax" in prompt
    assert chapters[0].title == "Outlined Opening"


@pytest.mark.asyncio
async def test_chapter_structure_sorts_and_paginates(sample_input_spec):
    agent = ChapterStructureAgent(model="x")
    out_of_order_response = """[
        {"number": 2, "title": "Second", "text": "Two two two."},
        {"number": 1, "title": "First", "text": "One one one one one one."}
    ]"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = out_of_order_response
        chapters = await agent.structure_story("dummy story", sample_input_spec)

    assert [ch.number for ch in chapters] == [1, 2]
    assert chapters[0].page_start == 3
    assert chapters[1].page_start == chapters[0].page_end + 1


@pytest.mark.asyncio
async def test_illustration_placement_skips_unknown_chapters(sample_input_spec):
    chapters = [
        Chapter(number=1, title="A", text="x", page_start=3, page_end=5),
        Chapter(number=2, title="B", text="y", page_start=6, page_end=8),
    ]
    agent = IllustrationPlacementAgent(model="x")
    response = """{
        "chapters": [
            {
                "chapter_number": 1,
                "illustrations": [
                    {
                        "page": 4,
                        "placement": "full_page",
                        "description": "Test",
                        "characters": ["Cassie"],
                        "scene_context": "morning"
                    }
                ]
            },
            {
                "chapter_number": 99,
                "illustrations": [
                    {
                        "page": 4,
                        "placement": "inline",
                        "description": "Should be skipped",
                        "characters": [],
                        "scene_context": "x"
                    }
                ]
            }
        ]
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = response
        updated = await agent.place_illustrations(
            chapters, sample_input_spec.characters, target_age=6
        )

    assert len(updated[0].illustrations) == 1
    assert updated[0].illustrations[0].page == 4
    assert len(updated[1].illustrations) == 0


@pytest.mark.asyncio
async def test_illustration_generator_renders_and_sets_paths(sample_input_spec, tmp_path):
    chapters = [
        Chapter(
            number=1,
            title="A",
            text="x",
            page_start=3,
            page_end=5,
            illustrations=[
                IllustrationSpec(
                    page=4,
                    placement="full_page",
                    description="Test illustration",
                    characters=["Cassie"],
                    scene_context="morning",
                )
            ],
        )
    ]

    mock_model = AsyncMock()
    mock_model.generate_image = AsyncMock(return_value=b"PNGDATA")
    agent = IllustrationGeneratorAgent(image_model=mock_model, output_dir=tmp_path)

    result = await agent.generate_all(chapters, sample_input_spec.characters)
    spec = result[0].illustrations[0]

    assert spec.image_path is not None
    written = (tmp_path / "illustrations" / "chapter_1_ill_1.png").read_bytes()
    assert written == b"PNGDATA"
    mock_model.generate_image.assert_called_once()
    call_kwargs = mock_model.generate_image.call_args.kwargs
    assert call_kwargs["seed"] is not None
    assert "Cassie" in call_kwargs["prompt"]


@pytest.mark.asyncio
async def test_create_book_content_orchestrates(sample_input_spec, tmp_path):
    """create_book_content calls: chapters → illustrations → 2× reflections → 1× experiment.

    With dedicated_to=None, biography is skipped.
    """
    chapter_response = """[
        {"number": 1, "title": "Morning", "text": "Cassie woke up."},
        {"number": 2, "title": "Adventure", "text": "She went to the beach."}
    ]"""
    illustration_response = """{
        "chapters": [
            {"chapter_number": 1, "illustrations": [
                {"page": 4, "placement": "full_page", "description": "Sunrise",
                 "characters": ["Cassie"], "scene_context": "morning"}
            ]},
            {"chapter_number": 2, "illustrations": []}
        ]
    }"""
    reflection_response = '["q1?", "q2?", "q3?"]'
    experiment_response = """{
        "title": "Sandcastle Builder",
        "concept": "Sand and water interact in interesting ways.",
        "materials": ["sand", "water", "cup"],
        "steps": ["Fill cup", "Add water", "Pour out", "Build castle"],
        "what_to_observe": "Wet sand sticks together but dry sand doesn't.",
        "safety_note": null
    }"""

    shared_mock = AsyncMock()
    shared_mock.generate.side_effect = [
        chapter_response,
        illustration_response,
        reflection_response,
        reflection_response,
        experiment_response,
    ]
    with (
        patch("fable_flow.agents.book_assembly.EnhancedTextModel", return_value=shared_mock),
        patch("fable_flow.agents.enrichment.EnhancedTextModel", return_value=shared_mock),
    ):
        book = await create_book_content(
            "story", sample_input_spec, image_model=None, output_dir=tmp_path
        )

    assert book.metadata.title == "Beach Story"
    assert len(book.chapters) == 2
    assert all(c.reflection is not None for c in book.chapters)
    assert book.experiment is not None
    assert book.experiment.title == "Sandcastle Builder"
    assert book.biography is None  # no dedicated_to in fixture
    assert (tmp_path / "book_content.json").exists()


@pytest.mark.asyncio
async def test_create_book_content_with_biography(sample_input_spec, tmp_path):
    from fable_flow.schemas.input_spec import DedicatedPersonality

    sample_input_spec.dedicated_to = DedicatedPersonality(
        name="Marie Curie", field="physics and chemistry"
    )

    chapter_response = '[{"number": 1, "title": "T", "text": "Cassie did science."}]'
    illustration_response = '{"chapters": [{"chapter_number": 1, "illustrations": []}]}'
    reflection_response = '["q1?", "q2?", "q3?"]'
    experiment_response = """{
        "title": "X", "concept": "Y",
        "materials": ["a"], "steps": ["s1", "s2"],
        "what_to_observe": "z", "safety_note": null
    }"""
    biography_response = """{
        "name": "Marie Curie", "title": "Scientist",
        "lifespan": "1867 – 1934",
        "one_line": "She discovered new elements.",
        "summary": "Marie loved learning...",
        "fun_facts": ["First woman Nobel laureate", "Studied radium", "Carried test tubes in her pocket"],
        "why_inspiring": "She kept asking why."
    }"""

    shared_mock = AsyncMock()
    shared_mock.generate.side_effect = [
        chapter_response,
        illustration_response,
        reflection_response,
        experiment_response,
        biography_response,
    ]
    with (
        patch("fable_flow.agents.book_assembly.EnhancedTextModel", return_value=shared_mock),
        patch("fable_flow.agents.enrichment.EnhancedTextModel", return_value=shared_mock),
    ):
        book = await create_book_content(
            "story", sample_input_spec, image_model=None, output_dir=tmp_path
        )

    assert book.biography is not None
    assert book.biography.name == "Marie Curie"
    assert book.biography.lifespan == "1867 – 1934"
