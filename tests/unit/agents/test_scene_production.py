from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from fable_flow.agents.scene_production import (
    SceneProductionCoordinator,
    _escape_ffmpeg_filter_path,
    _scene_seed,
)
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)
from fable_flow.schemas.scene_manifest import SceneSpec


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
                hair="black wavy",
                eyes="brown",
            ),
            typical_clothing="sundress",
        )
    ]


@pytest.fixture
def book_image_file(tmp_path):
    path = tmp_path / "book_illustration.png"
    Image.new("RGB", (1280, 720), color="white").save(path)
    return path


@pytest.fixture
def coordinator(tmp_path, characters):
    return SceneProductionCoordinator(
        tts_model=AsyncMock(),
        music_model=AsyncMock(),
        image_model=AsyncMock(),
        video_model=None,
        characters=characters,
        output_dir=tmp_path,
    )


def test_scene_seed_is_deterministic():
    assert _scene_seed("ch1_scene01") == _scene_seed("ch1_scene01")
    assert _scene_seed("ch1_scene01") != _scene_seed("ch1_scene02")


def test_escape_ffmpeg_path_handles_colons_and_commas():
    escaped = _escape_ffmpeg_filter_path("/tmp/test:foo,bar.srt")
    assert "\\:" in escaped
    assert "\\," in escaped


def test_image_prompt_includes_character_appearance(coordinator):
    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="Cassie ran to the beach.",
        setting="beach",
        mood="excited",
        characters=["Cassie"],
        estimated_duration=4.0,
    )
    prompt = coordinator._build_image_prompt(scene)
    assert "Indian Australian" in prompt
    assert "warm honey-brown" in prompt
    assert "beach" in prompt
    assert "excited" in prompt


@pytest.mark.asyncio
async def test_reuse_book_illustration(coordinator, book_image_file):
    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="A scene.",
        setting="x",
        mood="x",
        characters=[],
        illustration_reference=str(book_image_file),
        estimated_duration=4.0,
    )
    image = await coordinator._get_or_generate_image(scene)
    assert image.source == "book"
    assert image.file == str(book_image_file)
    assert image.width == 1280
    assert image.height == 720


@pytest.mark.asyncio
async def test_missing_book_illustration_raises(coordinator, tmp_path):
    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="A scene.",
        setting="x",
        mood="x",
        characters=[],
        illustration_reference=str(tmp_path / "does_not_exist.png"),
        estimated_duration=4.0,
    )
    with pytest.raises(FileNotFoundError):
        await coordinator._get_or_generate_image(scene)


@pytest.mark.asyncio
async def test_generate_new_image_when_no_reference(coordinator, tmp_path):
    coordinator.image_model.generate_image = AsyncMock(return_value=b"PNGDATA")
    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="A scene.",
        setting="x",
        mood="x",
        characters=[],
        estimated_duration=4.0,
    )
    image = await coordinator._get_or_generate_image(scene)
    assert image.source == "generated"
    assert image.width == 1280 and image.height == 720
    assert (tmp_path / "scenes" / "ch1_scene01_image.png").exists()
    coordinator.image_model.generate_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_narration_uses_real_audio_duration(coordinator, tmp_path):
    """Narration duration comes from the audio file, not text estimation."""
    coordinator.tts_model.generate_speech = AsyncMock(return_value=b"audiobytes")

    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="Cassie woke up early today.",
        setting="x",
        mood="x",
        characters=[],
        estimated_duration=4.0,
    )

    with patch.object(coordinator, "_probe_duration", return_value=3.21):
        narration = await coordinator._generate_narration(scene)

    assert narration.duration == 3.21
    assert len(narration.text_chunks) > 0
    assert (tmp_path / "scenes" / "ch1_scene01_narration.m4a").exists()
