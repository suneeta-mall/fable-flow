"""End-to-end integration test for the FableFlow pipeline.

Phase 1 is exercised against mocked LLM + image model.
Phase 2 (scene production + ffmpeg) is exercised with mocked TTS/music/image/video
models and patched subprocess execution so the test runs on any machine.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from fable_flow.agents.book_assembly import (
    IllustrationGeneratorAgent,
    create_book_content,
)
from fable_flow.agents.movie_adaptation import (
    MovieAssemblerAgent,
    SceneExtractorAgent,
)
from fable_flow.agents.scene_production import SceneProductionCoordinator
from fable_flow.agents.story_development import (
    DraftStoryAgent,
    FinalProofAgent,
    StoryEditorAgent,
)
from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
    DedicatedPersonality,
    FableFlowInput,
    ProjectMetadata,
    StorySeed,
)


@pytest.fixture
def cassie_input_spec():
    return FableFlowInput(
        project=ProjectMetadata(
            title="Cassie's Beach Adventure",
            series="Curious Cassie",
            volume=1,
            target_age=6,
            genre="educational adventure",
        ),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious, adventurous",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="shoulder-length wavy black",
                    eyes="bright curious brown",
                    distinctive_features=["wide expressive eyes"],
                ),
                typical_clothing="colorful sundress",
            ),
            Character(
                name="Caleb",
                age=3,
                role=CharacterRole.SUPPORTING,
                relationship="Cassie's younger brother",
                personality="playful",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="curly black",
                    eyes="brown",
                ),
                typical_clothing="striped t-shirt",
            ),
        ],
        story_seed=StorySeed(
            theme="ocean exploration",
            setting="Sydney Harbor beach",
            learning_objectives=["tides are caused by the moon's gravity"],
        ),
        dedicated_to=DedicatedPersonality(
            name="Rachel Carson",
            field="marine biology",
            notable_for="Silent Spring, ocean conservation",
        ),
    )


def _make_image_bytes() -> bytes:
    import io

    buf = io.BytesIO()
    Image.new("RGB", (1280, 720), color="white").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_pipeline(cassie_input_spec, tmp_path):
    story_text = (
        "Cassie woke up early on Saturday morning. The sun was rising. "
        "She ran downstairs and found Caleb eating breakfast. "
        "At the beach the tide was low. Rocky tide pools appeared. "
        "Cassie and Caleb walked carefully. They found starfish and crabs. "
        "Cassie called Caleb over to see a sea anemone. "
        "The day ended with happy memories of the ocean."
    )

    draft = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=200)
    editor = StoryEditorAgent(model="x", output_dir=tmp_path)
    proof = FinalProofAgent(model="x", output_dir=tmp_path)
    for agent in (draft, editor, proof):
        agent._model.generate = AsyncMock(return_value=story_text)

    drafted = await draft.generate_story(cassie_input_spec)
    edited = await editor.edit_story(drafted, cassie_input_spec)
    final_story = await proof.proof_story(edited, cassie_input_spec)
    assert final_story == story_text

    chapter_response = """[
        {"number": 1, "title": "Morning Excitement",
         "text": "Cassie woke up early on Saturday morning. The sun was rising. She ran downstairs and found Caleb eating breakfast."},
        {"number": 2, "title": "Tide Pool Adventure",
         "text": "At the beach the tide was low. Rocky tide pools appeared. Cassie and Caleb walked carefully. They found starfish and crabs."},
        {"number": 3, "title": "Sea Anemone Wonder",
         "text": "Cassie called Caleb over to see a sea anemone. The day ended with happy memories of the ocean."}
    ]"""
    illustration_response = """{
        "chapters": [
            {"chapter_number": 1, "illustrations": [
                {"page": 4, "placement": "full_page", "description": "Cassie at sunrise",
                 "characters": ["Cassie"], "scene_context": "morning, bedroom, excited"}
            ]},
            {"chapter_number": 2, "illustrations": [
                {"page": 7, "placement": "full_page", "description": "Tide pools with creatures",
                 "characters": ["Cassie", "Caleb"], "scene_context": "beach, discovery"}
            ]},
            {"chapter_number": 3, "illustrations": [
                {"page": 10, "placement": "full_page", "description": "Sea anemone close-up",
                 "characters": ["Cassie", "Caleb"], "scene_context": "tide pool, wonder"}
            ]}
        ]
    }"""

    reflection_response = (
        '["What did Cassie notice?", "Why might tides change?", "Have you visited a beach?"]'
    )
    experiment_response = """{
        "title": "Tide Pool in a Tray",
        "concept": "Water levels change with the moon's pull.",
        "materials": ["shallow tray", "water", "small pebbles", "spoon"],
        "steps": [
            "Place pebbles in the tray",
            "Pour in a small amount of water",
            "Tilt the tray slightly",
            "Watch how water rises and falls"
        ],
        "what_to_observe": "Water moves toward the lower side, just like tides moving with gravity.",
        "safety_note": "Wipe up spills to avoid slipping."
    }"""
    biography_response = """{
        "name": "Rachel Carson",
        "title": "Marine Biologist & Author",
        "lifespan": "1907 – 1964",
        "one_line": "She taught the world that the ocean is full of wonder and worth protecting.",
        "summary": "Rachel grew up next to the sea and never stopped asking questions about it...",
        "fun_facts": [
            "Her book changed how people thought about nature",
            "She loved listening to the ocean",
            "She helped start the modern environmental movement"
        ],
        "why_inspiring": "She showed that careful watching can change the world."
    }"""

    shared_text_mock = AsyncMock()
    shared_text_mock.generate.side_effect = [
        chapter_response,
        illustration_response,
        reflection_response,
        reflection_response,
        reflection_response,
        experiment_response,
        biography_response,
    ]
    with (
        patch(
            "fable_flow.agents.book_assembly.EnhancedTextModel",
            return_value=shared_text_mock,
        ),
        patch(
            "fable_flow.agents.enrichment.EnhancedTextModel",
            return_value=shared_text_mock,
        ),
    ):
        book = await create_book_content(
            final_story, cassie_input_spec, image_model=None, output_dir=tmp_path
        )

    assert len(book.chapters) == 3
    assert sum(len(c.illustrations) for c in book.chapters) == 3
    assert all(c.reflection is not None for c in book.chapters)
    assert all(len(c.reflection.questions) == 3 for c in book.chapters)
    assert book.experiment is not None
    assert book.experiment.title == "Tide Pool in a Tray"
    assert book.biography is not None
    assert book.biography.name == "Rachel Carson"

    fake_image_model = AsyncMock()
    fake_image_model.generate_image = AsyncMock(return_value=_make_image_bytes())
    await IllustrationGeneratorAgent(fake_image_model, output_dir=tmp_path).generate_all(
        book.chapters, cassie_input_spec.characters
    )
    rendered_paths = [ill.image_path for ch in book.chapters for ill in ch.illustrations]
    assert all(p is not None for p in rendered_paths)
    assert all((tmp_path / "illustrations").glob("*.png"))

    pdf_path = tmp_path / "book.pdf"
    generate_pdf(book, pdf_path)
    assert pdf_path.exists() and pdf_path.stat().st_size > 1000

    epub_path = tmp_path / "book.epub"
    generate_epub(book, epub_path)
    assert epub_path.exists() and epub_path.stat().st_size > 1000

    import zipfile

    with zipfile.ZipFile(epub_path) as zf:
        names = set(zf.namelist())
        assert "OEBPS/experiment.xhtml" in names
        assert "OEBPS/biography.xhtml" in names
        chapter_html = zf.read("OEBPS/chapter_1.xhtml").decode()
        assert "Think About It" in chapter_html
        experiment_html = zf.read("OEBPS/experiment.xhtml").decode()
        assert "Tide Pool in a Tray" in experiment_html
        biography_html = zf.read("OEBPS/biography.xhtml").decode()
        assert "Rachel Carson" in biography_html

    scene_response = """[
        {"id": "ch1_s01", "chapter": 1, "sequence": 1,
         "text": "Cassie woke up early on Saturday morning.",
         "page_reference": 4, "characters": ["Cassie"],
         "setting": "bedroom", "mood": "excited"},
        {"id": "ch2_s01", "chapter": 2, "sequence": 1,
         "text": "At the beach the tide was low.",
         "characters": ["Cassie", "Caleb"], "setting": "beach", "mood": "curious"}
    ]"""

    extractor = SceneExtractorAgent(model="x", output_dir=tmp_path)
    extractor._model.generate = AsyncMock(return_value=scene_response)
    manifest = await extractor.extract_scenes(book)
    assert manifest.total_scenes == 2
    assert manifest.scenes[0].illustration_reference is not None
    assert manifest.scenes[1].illustration_reference is None

    tts_model = AsyncMock()
    tts_model.generate_speech = AsyncMock(return_value=b"audiobytes")
    music_model = AsyncMock()
    music_model.generate_music = AsyncMock(return_value=b"wavbytes")
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=_make_image_bytes())

    coordinator = SceneProductionCoordinator(
        tts_model=tts_model,
        music_model=music_model,
        image_model=image_model,
        video_model=None,
        characters=cassie_input_spec.characters,
        output_dir=tmp_path,
    )

    async def fake_subprocess(*args, **kwargs):
        cmd = list(args)
        target = next(
            (
                cmd[i]
                for i in range(len(cmd) - 1, 0, -1)
                if cmd[i].endswith((".mp4", ".mp3", ".srt"))
            ),
            None,
        )
        if target:
            from pathlib import Path as _P

            _P(target).parent.mkdir(parents=True, exist_ok=True)
            _P(target).write_bytes(b"FAKE")

        class FakeProc:
            returncode = 0

            async def communicate(self_inner):
                return (b"", b"")

            def kill(self_inner):
                pass

            async def wait(self_inner):
                return 0

        return FakeProc()

    with (
        patch.object(coordinator, "_probe_duration", return_value=3.0),
        patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess),
    ):
        for scene in manifest.scenes:
            await coordinator.produce_scene(scene)

    for scene in manifest.scenes:
        assert scene.narration and scene.narration.duration == 3.0
        assert scene.video and scene.video.duration == 3.0
        assert scene.music and scene.music.duration == 3.0
        assert scene.composite is not None

    assembler = MovieAssemblerAgent(output_dir=tmp_path)
    with patch("asyncio.create_subprocess_exec", side_effect=fake_subprocess):
        movie_path = await assembler.assemble_movie(manifest, output_filename="movie.mp4")

    assert movie_path.endswith("movie.mp4")
    assert (tmp_path / "movie.mp4").exists()
    movie_manifest = json.loads((tmp_path / "movie_manifest.json").read_text())
    assert movie_manifest["movie_title"] == "Cassie's Beach Adventure"
    assert movie_manifest["total_scenes"] == 2
