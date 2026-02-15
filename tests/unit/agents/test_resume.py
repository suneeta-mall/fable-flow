"""Tests for the --resume flow: skip work whose output already exists on disk."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from PIL import Image

from fable_flow.agents.book_assembly import IllustrationGeneratorAgent
from fable_flow.agents.movie_adaptation import MovieAssemblerAgent
from fable_flow.agents.scene_production import SceneProductionCoordinator
from fable_flow.schemas.book_content import Chapter, IllustrationSpec
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)
from fable_flow.schemas.scene_manifest import (
    ImageAsset,
    MusicAsset,
    NarrationAsset,
    SceneManifest,
    SceneSpec,
    SubtitleAsset,
    VideoAsset,
)


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


@pytest.mark.asyncio
async def test_illustration_generator_resume_skips_existing(characters, tmp_path):
    chapters = [
        Chapter(
            number=1,
            title="A",
            text="t",
            page_start=3,
            page_end=4,
            illustrations=[
                IllustrationSpec(
                    page=4,
                    placement="full_page",
                    description="d",
                    characters=["Cassie"],
                    scene_context="x",
                ),
                IllustrationSpec(
                    page=5,
                    placement="inline",
                    description="d2",
                    characters=["Cassie"],
                    scene_context="x",
                ),
            ],
        )
    ]

    # Pre-create the first illustration's file
    illustrations_dir = tmp_path / "illustrations"
    illustrations_dir.mkdir(parents=True, exist_ok=True)
    (illustrations_dir / "chapter_1_ill_1.png").write_bytes(b"existing")

    mock_model = AsyncMock()
    mock_model.generate_image = AsyncMock(return_value=b"NEW_PNG")
    agent = IllustrationGeneratorAgent(image_model=mock_model, output_dir=tmp_path)

    result = await agent.generate_all(chapters, characters, resume=True)

    # First illustration reused, second one generated
    assert mock_model.generate_image.await_count == 1
    assert result[0].illustrations[0].image_path.endswith("chapter_1_ill_1.png")
    assert (tmp_path / "illustrations" / "chapter_1_ill_2.png").exists()
    # Existing file untouched
    assert (illustrations_dir / "chapter_1_ill_1.png").read_bytes() == b"existing"


@pytest.mark.asyncio
async def test_illustration_generator_no_resume_regenerates_all(characters, tmp_path):
    chapters = [
        Chapter(
            number=1,
            title="A",
            text="t",
            page_start=3,
            page_end=4,
            illustrations=[
                IllustrationSpec(
                    page=4,
                    placement="full_page",
                    description="d",
                    characters=["Cassie"],
                    scene_context="x",
                ),
            ],
        )
    ]
    (tmp_path / "illustrations").mkdir(parents=True, exist_ok=True)
    (tmp_path / "illustrations" / "chapter_1_ill_1.png").write_bytes(b"existing")

    mock_model = AsyncMock()
    mock_model.generate_image = AsyncMock(return_value=b"NEW_PNG")
    agent = IllustrationGeneratorAgent(image_model=mock_model, output_dir=tmp_path)

    await agent.generate_all(chapters, characters, resume=False)

    assert mock_model.generate_image.await_count == 1
    assert (tmp_path / "illustrations" / "chapter_1_ill_1.png").read_bytes() == b"NEW_PNG"


@pytest.mark.asyncio
async def test_produce_scene_resume_skips_completed_sub_steps(tmp_path, characters):
    """Pre-populate a scene with completed narration/image; ensure they're not regenerated."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    narration_file = scenes_dir / "ch1_scene01_narration.m4a"
    image_file = scenes_dir / "ch1_scene01_image.png"
    narration_file.write_bytes(b"audio")
    Image.new("RGB", (1280, 720), color="white").save(image_file)

    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="A short scene.",
        characters=[],
        setting="x",
        mood="x",
        estimated_duration=3.0,
        narration=NarrationAsset(file=str(narration_file), duration=3.0, text_chunks=["A short."]),
        image=ImageAsset(file=str(image_file), source="generated", width=1280, height=720),
    )

    tts_model = AsyncMock()
    tts_model.generate_speech = AsyncMock()
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock()
    music_model = AsyncMock()
    music_model.generate_music = AsyncMock(return_value=b"WAV")

    coordinator = SceneProductionCoordinator(
        tts_model=tts_model,
        music_model=music_model,
        image_model=image_model,
        video_model=None,
        characters=characters,
        output_dir=tmp_path,
    )

    # Patch ffmpeg subprocess so video/music/composite "succeed" without calling ffmpeg
    async def fake_ffmpeg(*args, **kwargs):
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

        class _P:
            returncode = 0

            async def communicate(self):
                return (b"", b"")

            def kill(self):
                pass

            async def wait(self):
                return 0

        return _P()

    from unittest.mock import patch

    with patch("asyncio.create_subprocess_exec", side_effect=fake_ffmpeg):
        await coordinator.produce_scene(scene, resume=True)

    # Narration not regenerated (TTS not called)
    tts_model.generate_speech.assert_not_awaited()
    # Image not regenerated
    image_model.generate_image.assert_not_awaited()
    # Music WAS generated (no existing music file pre-populated)
    music_model.generate_music.assert_awaited_once()
    # Composite was produced
    assert scene.composite is not None
    assert Path(scene.composite).exists()


@pytest.mark.asyncio
async def test_produce_scene_invokes_save_callback_per_step(tmp_path, characters):
    """The save callback is invoked after every step that produced something."""
    tts_model = AsyncMock()
    tts_model.generate_speech = AsyncMock(return_value=b"audio")
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=b"PNG_BYTES")
    music_model = AsyncMock()
    music_model.generate_music = AsyncMock(return_value=b"WAV")

    coordinator = SceneProductionCoordinator(
        tts_model=tts_model,
        music_model=music_model,
        image_model=image_model,
        video_model=None,
        characters=characters,
        output_dir=tmp_path,
    )

    scene = SceneSpec(
        id="ch1_scene01",
        chapter=1,
        sequence=1,
        text="x",
        characters=[],
        setting="x",
        mood="x",
        estimated_duration=3.0,
    )

    save_count = 0

    def save():
        nonlocal save_count
        save_count += 1

    from unittest.mock import patch

    async def fake_ffmpeg(*args, **kwargs):
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

        class _P:
            returncode = 0

            async def communicate(self):
                return (b"", b"")

            def kill(self):
                pass

            async def wait(self):
                return 0

        return _P()

    with (
        patch("asyncio.create_subprocess_exec", side_effect=fake_ffmpeg),
        patch.object(coordinator, "_probe_duration", return_value=3.0),
    ):
        await coordinator.produce_scene(scene, resume=False, on_step_complete=save)

    # 6 sub-steps: narration, image, video, music, subtitles, composite
    assert save_count == 6


@pytest.mark.asyncio
async def test_movie_assembler_resume_skips_existing_mp4(tmp_path):
    manifest = SceneManifest(
        book_title="X",
        total_scenes=1,
        estimated_total_duration=5.0,
        scenes=[
            SceneSpec(
                id="s1",
                chapter=1,
                sequence=1,
                text="t",
                setting="x",
                mood="x",
                estimated_duration=5.0,
                composite=str(tmp_path / "s1.mp4"),
                narration=NarrationAsset(file="n.m4a", duration=5.0),
            )
        ],
    )
    (tmp_path / "s1.mp4").write_bytes(b"composite")
    existing_movie = tmp_path / "story.mp4"
    existing_movie.write_bytes(b"existing-movie")

    from unittest.mock import patch

    async def fake_ffmpeg(*args, **kwargs):
        # Should NOT be called when resuming and the movie already exists
        raise AssertionError("ffmpeg invoked despite resume + existing movie")

    with patch("asyncio.create_subprocess_exec", side_effect=fake_ffmpeg):
        result = await MovieAssemblerAgent(output_dir=tmp_path).assemble_movie(
            manifest, output_filename="story.mp4", resume=True
        )

    assert result == str(existing_movie)
    assert existing_movie.read_bytes() == b"existing-movie"


# Suppress unused-import warning from Path in test_produce_scene_resume_skips_completed_sub_steps
from pathlib import Path  # noqa: E402
