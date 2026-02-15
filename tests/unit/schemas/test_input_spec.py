from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fable_flow.schemas.input_spec import (
    Appearance,
    BookProductionConfig,
    Character,
    CharacterRole,
    FableFlowInput,
    MovieProductionConfig,
    ProductionConfig,
    ProjectMetadata,
    StorySeed,
)


class TestAppearance:
    """Tests for Appearance schema."""

    def test_valid_appearance(self):
        appearance = Appearance(
            heritage="Indian Australian",
            skin_tone="warm honey-brown",
            hair="shoulder-length wavy black with natural shine",
            eyes="bright curious brown",
            distinctive_features=["wide expressive eyes", "infectious smile"],
        )
        assert appearance.heritage == "Indian Australian"
        assert appearance.skin_tone == "warm honey-brown"
        assert len(appearance.distinctive_features) == 2

    def test_appearance_without_distinctive_features(self):
        appearance = Appearance(
            heritage="European",
            skin_tone="fair",
            hair="blonde straight",
            eyes="blue",
        )
        assert appearance.distinctive_features == []


class TestCharacter:
    """Tests for Character schema."""

    def test_valid_character(self):
        character = Character(
            name="Cassie",
            age=6,
            role=CharacterRole.PROTAGONIST,
            personality="curious, adventurous, kind",
            appearance=Appearance(
                heritage="Indian Australian",
                skin_tone="warm honey-brown",
                hair="wavy black",
                eyes="brown",
            ),
            typical_clothing="colorful sundresses",
        )
        assert character.name == "Cassie"
        assert character.age == 6
        assert character.role == CharacterRole.PROTAGONIST

    def test_character_without_age(self):
        character = Character(
            name="Mystery Character",
            role=CharacterRole.MINOR,
            personality="mysterious",
            appearance=Appearance(
                heritage="Unknown", skin_tone="pale", hair="hooded", eyes="hidden"
            ),
            typical_clothing="dark cloak",
        )
        assert character.age is None

    def test_character_with_relationship(self):
        character = Character(
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
            typical_clothing="striped shirts",
            relationship="Cassie's younger brother",
        )
        assert character.relationship == "Cassie's younger brother"

    def test_invalid_age_zero(self):
        with pytest.raises(ValidationError) as exc_info:
            Character(
                name="Invalid",
                age=0,
                role=CharacterRole.PROTAGONIST,
                personality="test",
                appearance=Appearance(heritage="Test", skin_tone="test", hair="test", eyes="test"),
                typical_clothing="test",
            )
        assert "age" in str(exc_info.value).lower()

    def test_invalid_age_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            Character(
                name="Invalid",
                age=101,
                role=CharacterRole.PROTAGONIST,
                personality="test",
                appearance=Appearance(heritage="Test", skin_tone="test", hair="test", eyes="test"),
                typical_clothing="test",
            )
        assert "age" in str(exc_info.value).lower()


class TestStorySeed:
    """Tests for StorySeed schema."""

    def test_valid_story_seed(self):
        seed = StorySeed(
            theme="ocean exploration",
            setting="Sydney Harbor beach",
            learning_objectives=["tides are caused by moon's gravity", "ocean ecosystems"],
        )
        assert seed.theme == "ocean exploration"
        assert len(seed.learning_objectives) == 2
        assert seed.draft_story is None

    def test_story_seed_with_draft(self):
        draft_text = "Cassie woke up early, excited about the beach trip..."
        seed = StorySeed(
            theme="beach adventure",
            setting="beach",
            draft_story=draft_text,
        )
        assert seed.draft_story == draft_text

    def test_empty_theme_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            StorySeed(theme="   ", setting="beach")
        assert "theme" in str(exc_info.value).lower()

    def test_empty_setting_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            StorySeed(theme="adventure", setting="")
        assert "setting" in str(exc_info.value).lower()


class TestProjectMetadata:
    """Tests for ProjectMetadata schema."""

    def test_valid_project_metadata(self):
        metadata = ProjectMetadata(
            title="Cassie's Beach Adventure",
            series="Curious Cassie",
            volume=1,
            target_age=6,
            genre="educational adventure",
        )
        assert metadata.title == "Cassie's Beach Adventure"
        assert metadata.series == "Curious Cassie"
        assert metadata.volume == 1

    def test_project_without_series(self):
        metadata = ProjectMetadata(
            title="Standalone Story",
            target_age=7,
            genre="fantasy",
        )
        assert metadata.series is None
        assert metadata.volume is None

    def test_invalid_target_age_too_young(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                title="Test",
                target_age=2,
                genre="test",
            )
        assert "target_age" in str(exc_info.value).lower()

    def test_invalid_target_age_too_old(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectMetadata(
                title="Test",
                target_age=13,
                genre="test",
            )
        assert "target_age" in str(exc_info.value).lower()


class TestBookProductionConfig:
    """Tests for BookProductionConfig schema."""

    def test_default_config(self):
        config = BookProductionConfig()
        assert config.format == ["pdf", "epub"]
        assert config.page_count_target == 24
        assert config.illustration_style == "digital watercolor blend"

    def test_custom_config(self):
        config = BookProductionConfig(
            format=["pdf"],
            page_count_target=32,
            illustration_style="modern flat illustration",
        )
        assert config.format == ["pdf"]
        assert config.page_count_target == 32

    def test_empty_format_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            BookProductionConfig(format=[])
        assert "format" in str(exc_info.value).lower()

    def test_invalid_page_count_too_low(self):
        with pytest.raises(ValidationError) as exc_info:
            BookProductionConfig(page_count_target=5)
        assert "page_count_target" in str(exc_info.value).lower()

    def test_invalid_page_count_too_high(self):
        with pytest.raises(ValidationError) as exc_info:
            BookProductionConfig(page_count_target=150)
        assert "page_count_target" in str(exc_info.value).lower()


class TestMovieProductionConfig:
    """Tests for MovieProductionConfig schema."""

    def test_default_config(self):
        config = MovieProductionConfig()
        assert config.enabled is True
        assert config.include_narration is True
        assert config.include_subtitles is True

    def test_disabled_movie(self):
        config = MovieProductionConfig(enabled=False)
        assert config.enabled is False


class TestProductionConfig:
    """Tests for ProductionConfig schema."""

    def test_default_config(self):
        config = ProductionConfig()
        assert isinstance(config.book, BookProductionConfig)
        assert isinstance(config.movie, MovieProductionConfig)

    def test_custom_config(self):
        config = ProductionConfig(
            book=BookProductionConfig(format=["pdf"], page_count_target=16),
            movie=MovieProductionConfig(enabled=False),
        )
        assert config.book.format == ["pdf"]
        assert config.movie.enabled is False


class TestFableFlowInput:
    """Tests for complete FableFlowInput schema."""

    @pytest.fixture
    def valid_input_data(self):
        """Valid input data for testing."""
        return {
            "project": {
                "title": "Cassie's Beach Adventure",
                "series": "Curious Cassie",
                "volume": 1,
                "target_age": 6,
                "genre": "educational adventure",
            },
            "characters": [
                {
                    "name": "Cassie",
                    "age": 6,
                    "role": "protagonist",
                    "personality": "curious, adventurous, kind",
                    "appearance": {
                        "heritage": "Indian Australian",
                        "skin_tone": "warm honey-brown",
                        "hair": "shoulder-length wavy black",
                        "eyes": "bright curious brown",
                        "distinctive_features": ["wide expressive eyes"],
                    },
                    "typical_clothing": "colorful sundresses",
                }
            ],
            "story_seed": {
                "theme": "ocean exploration",
                "setting": "Sydney Harbor beach",
                "learning_objectives": ["tides", "ocean ecosystems"],
            },
        }

    def test_valid_complete_input(self, valid_input_data):
        input_spec = FableFlowInput.model_validate(valid_input_data)
        assert input_spec.project.title == "Cassie's Beach Adventure"
        assert len(input_spec.characters) == 1
        assert input_spec.characters[0].name == "Cassie"
        assert input_spec.story_seed.theme == "ocean exploration"

    def test_default_production_config(self, valid_input_data):
        input_spec = FableFlowInput.model_validate(valid_input_data)
        assert input_spec.production_config.book.format == ["pdf", "epub"]
        assert input_spec.production_config.movie.enabled is True

    def test_custom_production_config(self, valid_input_data):
        valid_input_data["production_config"] = {
            "book": {"format": ["pdf"], "page_count_target": 32},
            "movie": {"enabled": False},
        }
        input_spec = FableFlowInput.model_validate(valid_input_data)
        assert input_spec.production_config.book.format == ["pdf"]
        assert input_spec.production_config.movie.enabled is False

    def test_multiple_characters(self, valid_input_data):
        valid_input_data["characters"].append(
            {
                "name": "Caleb",
                "age": 3,
                "role": "supporting",
                "personality": "playful",
                "appearance": {
                    "heritage": "Indian Australian",
                    "skin_tone": "warm honey-brown",
                    "hair": "curly black",
                    "eyes": "brown",
                },
                "typical_clothing": "striped shirts",
            }
        )
        input_spec = FableFlowInput.model_validate(valid_input_data)
        assert len(input_spec.characters) == 2

    def test_no_protagonist_raises_error(self, valid_input_data):
        valid_input_data["characters"][0]["role"] = "supporting"
        with pytest.raises(ValidationError) as exc_info:
            FableFlowInput.model_validate(valid_input_data)
        assert "protagonist" in str(exc_info.value).lower()

    def test_no_characters_raises_error(self, valid_input_data):
        valid_input_data["characters"] = []
        with pytest.raises(ValidationError) as exc_info:
            FableFlowInput.model_validate(valid_input_data)
        assert "characters" in str(exc_info.value).lower()

    def test_from_json_file(self, tmp_path, valid_input_data):
        json_file = tmp_path / "input.json"
        with open(json_file, "w") as f:
            json.dump(valid_input_data, f)

        input_spec = FableFlowInput.from_json_file(json_file)
        assert input_spec.project.title == "Cassie's Beach Adventure"

    def test_to_json_file(self, tmp_path, valid_input_data):
        input_spec = FableFlowInput.model_validate(valid_input_data)
        json_file = tmp_path / "output.json"

        input_spec.to_json_file(json_file)

        assert json_file.exists()
        with open(json_file) as f:
            data = json.load(f)
        assert data["project"]["title"] == "Cassie's Beach Adventure"

    def test_round_trip_json(self, tmp_path, valid_input_data):
        input_spec1 = FableFlowInput.model_validate(valid_input_data)
        json_file = tmp_path / "test.json"

        input_spec1.to_json_file(json_file)
        input_spec2 = FableFlowInput.from_json_file(json_file)

        assert input_spec1.model_dump() == input_spec2.model_dump()
