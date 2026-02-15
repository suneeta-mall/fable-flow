from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.movie_adaptation import (
    MovieAssemblerAgent,
    SceneExtractorAgent,
)
from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    IllustrationSpec,
)
from fable_flow.schemas.scene_manifest import (
    NarrationAsset,
    SceneManifest,
    SceneSpec,
)


@pytest.fixture
def book_with_rendered_illustration():
    return BookContent(
        metadata=BookMetadata(title="Test Book", target_age=6, page_count=24, genre="adventure"),
        chapters=[
            Chapter(
                number=1,
                title="Chapter One",
                text="Cassie woke up early. She was excited about the beach trip.",
                page_start=3,
                page_end=8,
                illustrations=[
                    IllustrationSpec(
                        page=4,
                        placement="full_page",
                        description="Cassie in bedroom",
                        scene_context="morning",
                        image_path="/abs/illustrations/chapter_1_ill_1.png",
                    )
                ],
            ),
        ],
        full_text="Cassie woke up early. She was excited about the beach trip.",
        characters_used=["Cassie"],
    )


@pytest.mark.asyncio
async def test_extract_scenes_resolves_page_to_illustration(
    book_with_rendered_illustration, tmp_path
):
    extractor = SceneExtractorAgent(model="x", output_dir=tmp_path)
    mock_response = """[
        {
            "id": "ch1_scene01", "chapter": 1, "sequence": 1,
            "text": "Cassie woke up early.",
            "page_reference": 4, "characters": ["Cassie"],
            "setting": "bedroom", "mood": "excited"
        },
        {
            "id": "ch1_scene02", "chapter": 1, "sequence": 2,
            "text": "She was excited.",
            "characters": ["Cassie"], "setting": "bedroom", "mood": "happy"
        }
    ]"""
    with patch.object(extractor._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response
        manifest = await extractor.extract_scenes(book_with_rendered_illustration)

    assert manifest.total_scenes == 2
    assert manifest.scenes[0].illustration_reference == "/abs/illustrations/chapter_1_ill_1.png"
    assert manifest.scenes[1].illustration_reference is None
    assert (tmp_path / "scene_manifest.json").exists()


@pytest.mark.asyncio
async def test_assemble_movie_runs_ffmpeg(tmp_path):
    sample_files = [tmp_path / f"scenes/scene_{i}.mp4" for i in (1, 2)]
    for f in sample_files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"dummy")

    manifest = SceneManifest(
        book_title="Movie",
        total_scenes=2,
        estimated_total_duration=10.0,
        scenes=[
            SceneSpec(
                id="ch1_scene01",
                chapter=1,
                sequence=1,
                text="t",
                setting="x",
                mood="x",
                estimated_duration=5.0,
                composite=str(sample_files[0]),
                narration=NarrationAsset(file="n.m4a", duration=5.0),
            ),
            SceneSpec(
                id="ch1_scene02",
                chapter=1,
                sequence=2,
                text="t",
                setting="x",
                mood="x",
                estimated_duration=5.0,
                composite=str(sample_files[1]),
                narration=NarrationAsset(file="n.m4a", duration=5.0),
            ),
        ],
    )

    output_path = tmp_path / "movie.mp4"

    async def fake_run(*args, **kwargs):
        class _Fake:
            async def communicate(self_inner):
                output_path.write_bytes(b"FAKEMP4")
                return (b"", b"")

            returncode = 0

        return _Fake()

    assembler = MovieAssemblerAgent(output_dir=tmp_path)
    with patch("asyncio.create_subprocess_exec", side_effect=fake_run):
        movie_path = await assembler.assemble_movie(manifest, output_filename="movie.mp4")

    assert movie_path.endswith("movie.mp4")
    assert output_path.exists()
    concat = (tmp_path / "concat_list.txt").read_text()
    assert "scene_1.mp4" in concat
    movie_manifest = json.loads((tmp_path / "movie_manifest.json").read_text())
    assert movie_manifest["total_scenes"] == 2
    assert movie_manifest["total_duration"] == 10.0


@pytest.mark.asyncio
async def test_assemble_movie_raises_without_composites(tmp_path):
    manifest = SceneManifest(
        book_title="X",
        total_scenes=1,
        estimated_total_duration=5.0,
        scenes=[
            SceneSpec(
                id="x",
                chapter=1,
                sequence=1,
                text="t",
                setting="x",
                mood="x",
                estimated_duration=5.0,
            )
        ],
    )
    with pytest.raises(ValueError, match="No scene composites"):
        await MovieAssemblerAgent(output_dir=tmp_path).assemble_movie(manifest)
