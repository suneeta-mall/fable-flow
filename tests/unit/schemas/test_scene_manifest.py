from __future__ import annotations

import json
from pathlib import Path

import pytest

from fable_flow.schemas.scene_manifest import (
    ImageAsset,
    MusicAsset,
    NarrationAsset,
    SceneManifest,
    SceneSpec,
    SubtitleAsset,
    VideoAsset,
)


class TestNarrationAsset:
    """Tests for NarrationAsset."""

    def test_valid_narration_asset(self):
        asset = NarrationAsset(
            file="scenes/ch1_scene01_narration.m4a",
            duration=6.5,
            text_chunks=["Cassie woke up early.", "She was excited."],
        )
        assert asset.file == "scenes/ch1_scene01_narration.m4a"
        assert asset.duration == 6.5
        assert len(asset.text_chunks) == 2


class TestImageAsset:
    """Tests for ImageAsset."""

    def test_image_from_book(self):
        asset = ImageAsset(
            file="illustrations/chapter_1_page_4.png",
            source="book",
            width=1024,
            height=768,
        )
        assert asset.source == "book"
        assert asset.width == 1024

    def test_generated_image(self):
        asset = ImageAsset(
            file="scenes/ch1_scene01_image.png",
            source="generated",
        )
        assert asset.source == "generated"
        assert asset.width is None


class TestVideoAsset:
    """Tests for VideoAsset."""

    def test_valid_video_asset(self):
        asset = VideoAsset(
            file="scenes/ch1_scene01_video.mp4",
            duration=6.5,
            fps=25.4,
        )
        assert asset.file == "scenes/ch1_scene01_video.mp4"
        assert asset.duration == 6.5
        assert asset.fps == 25.4


class TestMusicAsset:
    """Tests for MusicAsset."""

    def test_valid_music_asset(self):
        asset = MusicAsset(
            file="scenes/ch1_scene01_music.mp3",
            duration=6.5,
            fade_in=0.5,
            fade_out=0.5,
        )
        assert asset.duration == 6.5
        assert asset.fade_in == 0.5

    def test_music_default_fades(self):
        asset = MusicAsset(
            file="music.mp3",
            duration=10.0,
        )
        assert asset.fade_in == 0.5
        assert asset.fade_out == 0.5


class TestSubtitleAsset:
    """Tests for SubtitleAsset."""

    def test_valid_subtitle_asset(self):
        asset = SubtitleAsset(
            file="scenes/ch1_scene01_subtitles.srt",
        )
        assert asset.format == "SRT"

    def test_vtt_subtitle(self):
        asset = SubtitleAsset(
            file="subtitles.vtt",
            format="VTT",
        )
        assert asset.format == "VTT"


class TestSceneSpec:
    """Tests for SceneSpec."""

    def test_valid_scene_spec(self):
        scene = SceneSpec(
            id="ch1_scene01",
            chapter=1,
            sequence=1,
            text="Cassie woke up early, excited about the beach trip.",
            page_reference=4,
            characters=["Cassie"],
            setting="bedroom",
            mood="excited",
            illustration_reference="illustrations/chapter_1_page_4.png",
            estimated_duration=6.5,
        )
        assert scene.id == "ch1_scene01"
        assert scene.chapter == 1
        assert scene.sequence == 1
        assert len(scene.characters) == 1
        assert scene.narration is None

    def test_scene_with_generated_assets(self):
        scene = SceneSpec(
            id="ch1_scene01",
            chapter=1,
            sequence=1,
            text="Test scene",
            setting="test",
            mood="test",
            estimated_duration=5.0,
            narration=NarrationAsset(
                file="narration.m4a",
                duration=5.0,
            ),
            image=ImageAsset(
                file="image.png",
                source="generated",
            ),
            video=VideoAsset(
                file="video.mp4",
                duration=5.0,
            ),
            music=MusicAsset(
                file="music.mp3",
                duration=5.0,
            ),
            subtitles=SubtitleAsset(
                file="subtitles.srt",
            ),
            composite="scenes/ch1_scene01_final.mp4",
        )
        assert scene.narration is not None
        assert scene.image is not None
        assert scene.video is not None
        assert scene.music is not None
        assert scene.subtitles is not None
        assert scene.composite == "scenes/ch1_scene01_final.mp4"


class TestSceneManifest:
    """Tests for SceneManifest."""

    @pytest.fixture
    def sample_manifest(self):
        """Sample scene manifest for testing."""
        return {
            "book_title": "Cassie's Beach Adventure",
            "total_scenes": 2,
            "estimated_total_duration": 12.0,
            "scenes": [
                {
                    "id": "ch1_scene01",
                    "chapter": 1,
                    "sequence": 1,
                    "text": "Cassie woke up early.",
                    "page_reference": 4,
                    "characters": ["Cassie"],
                    "setting": "bedroom",
                    "mood": "excited",
                    "estimated_duration": 6.0,
                },
                {
                    "id": "ch1_scene02",
                    "chapter": 1,
                    "sequence": 2,
                    "text": "She ran downstairs.",
                    "characters": ["Cassie"],
                    "setting": "kitchen",
                    "mood": "happy",
                    "estimated_duration": 6.0,
                },
            ],
        }

    def test_valid_scene_manifest(self, sample_manifest):
        manifest = SceneManifest.model_validate(sample_manifest)
        assert manifest.book_title == "Cassie's Beach Adventure"
        assert manifest.total_scenes == 2
        assert manifest.estimated_total_duration == 12.0
        assert len(manifest.scenes) == 2
        assert manifest.scenes[0].id == "ch1_scene01"

    def test_from_json_file(self, tmp_path, sample_manifest):
        json_file = tmp_path / "scene_manifest.json"
        with open(json_file, "w") as f:
            json.dump(sample_manifest, f)

        manifest = SceneManifest.from_json_file(json_file)
        assert manifest.book_title == "Cassie's Beach Adventure"
        assert len(manifest.scenes) == 2

    def test_to_json_file(self, tmp_path, sample_manifest):
        manifest = SceneManifest.model_validate(sample_manifest)
        json_file = tmp_path / "output.json"

        manifest.to_json_file(json_file)

        assert json_file.exists()
        with open(json_file) as f:
            data = json.load(f)
        assert data["book_title"] == "Cassie's Beach Adventure"
        assert len(data["scenes"]) == 2

    def test_round_trip_json(self, tmp_path, sample_manifest):
        manifest1 = SceneManifest.model_validate(sample_manifest)
        json_file = tmp_path / "test.json"

        manifest1.to_json_file(json_file)
        manifest2 = SceneManifest.from_json_file(json_file)

        assert manifest1.model_dump() == manifest2.model_dump()
