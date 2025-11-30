import pytest
import yaml

from fable_flow.config import (
    AgentTypesConfig,
    APIConfig,
    ContentSafetyConfig,
    ModelConfig,
    PathsConfig,
    PDFConfig,
    PromptsConfig,
    Settings,
    StyleConfig,
    TextGenerationConfig,
)


# Fixtures
@pytest.fixture
def test_config_path(tmp_path):
    config_content = f"""
    model:
      server:
        url: "http://test-server:8000/v1"
        api_key: "test-key"
      default: "test-model"
      text_generation:
        story: "test-story-model"
        content_moderation: "test-moderation-model"
        proofreading: "test-proofreading-model"
      image_generation:
        model: "test-image-model"
        style_consistency: "test-style-model"
      text_to_speech:
        model: "test-tts-model"
        device: "cpu"
      content_safety:
        safety_model: "test-safety-model"
        scientific_accuracy: "test-accuracy-model"
      music_generation:
        model: "test-music-model"
      video_generation:
        model: "test-video-model"
        num_frames: 81
        num_inference_steps: 50
        guidance_scale: 6
        fps: 8
    api:
      keys:
        openai: "test-openai-key"
    paths:
      base: "{tmp_path}/base"
      output: "{tmp_path}/output"
    style:
      illustration:
        style_preset: "test-style"
        color_scheme: "test-colors"
        art_style: "test-art"
      music:
        happy: "test-happy"
        sad: "test-sad"
        adventure: "test-adventure"
        mystery: "test-mystery"
      video:
        animation_style: "test-animation"
        color_palette: "test-palette"
        camera_style: "test-camera"
    prompts:
      proof_agent: "Test proof agent prompt"
      critical_reviewer: "Test critical reviewer prompt"
      content_moderator: "Test content moderator prompt"
      editor: "Test editor prompt"
      author_friend: "Test author friend prompt"
      movie_director: "Test movie director prompt"
      image_planner: "Test image planner prompt"
      illustrator: "Test illustrator prompt"
      composer: "Test composer prompt"
      book_producer: "Test book producer prompt"
    agent_types:
      author_friend: "TestAuthorFriendAgent"
      critique: "TestCritiqueAgent"
      content_moderator: "TestModeratorAgent"
      editor: "TestEditorAgent"
      format_proof: "TestFormatProofAgent"
      narrator: "TestNarratorAgent"
      illustrator: "TestIllustratorAgent"
      illustration_planner: "TestIllustratorPlannerAgent"
      producer: "TestBookProducerAgent"
      user: "TestUser"
      movie_director_type: "TestMovieDirectorType"
      music_director: "TestMusicDirectorAgent"
      musician: "TestMusicianAgent"
      animator: "TestAnimatorAgent"
      movie_producer: "TestMovieProducerAgent"
    """
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def test_yaml_path(tmp_path):
    config_content = f"""
    model:
      server:
        url: "http://test-server:8000/v1"
        api_key: "test-key"
      default: "test-model"
      text_generation:
        story: "${{model.default}}"
        content_moderation: "${{model.default}}"
        proofreading: "${{model.default}}"
      image_generation:
        model: "test-image-model"
        style_consistency: "test-style-model"
      text_to_speech:
        model: "test-tts-model"
        device: "cpu"
      content_safety:
        safety_model: "${{model.default}}"
        scientific_accuracy: "${{model.default}}"
      music_generation:
        model: "test-music-model"
      video_generation:
        model: "test-video-model"
        num_frames: 81
        num_inference_steps: 50
        guidance_scale: 6
        fps: 8
    api:
      keys:
        openai: "${{env.OPENAI_API_KEY}}"
    paths:
      base: "{tmp_path}/base"
      output: "{tmp_path}/output"
    style:
      illustration:
        style_preset: "test-style"
        color_scheme: "test-colors"
        art_style: "test-art"
      music:
        happy: "test-happy"
        sad: "test-sad"
        adventure: "test-adventure"
        mystery: "test-mystery"
      video:
        animation_style: "test-animation"
        color_palette: "test-palette"
        camera_style: "test-camera"
    prompts:
      proof_agent: "Test proof agent prompt"
      critical_reviewer: "Test critical reviewer prompt"
      content_moderator: "Test content moderator prompt"
      editor: "Test editor prompt"
      author_friend: "Test author friend prompt"
      movie_director: "Test movie director prompt"
      image_planner: "Test image planner prompt"
      illustrator: "Test illustrator prompt"
      composer: "Test composer prompt"
      book_producer: "Test book producer prompt"
    agent_types:
      author_friend: "TestAuthorFriendAgent"
      critique: "TestCritiqueAgent"
      content_moderator: "TestModeratorAgent"
      editor: "TestEditorAgent"
      format_proof: "TestFormatProofAgent"
      narrator: "TestNarratorAgent"
      illustrator: "TestIllustratorAgent"
      illustration_planner: "TestIllustratorPlannerAgent"
      producer: "TestBookProducerAgent"
      user: "TestUser"
      movie_director_type: "TestMovieDirectorType"
      music_director: "TestMusicDirectorAgent"
      musician: "TestMusicianAgent"
      animator: "TestAnimatorAgent"
      movie_producer: "TestMovieProducerAgent"
    """
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return config_file


# Model Config Tests
def test_model_config_defaults():
    config = ModelConfig(
        text_generation=TextGenerationConfig(
            story="test", content_moderation="test", proofreading="test"
        ),
        content_safety=ContentSafetyConfig(safety_model="test", scientific_accuracy="test"),
    )
    assert config.server.url == "http://localhost:8000/v1"
    assert config.server.api_key == "dev-api-key"
    assert config.default == "google/gemma-3-27b-it"
    assert config.image_generation.model == "stabilityai/stable-diffusion-xl-base-1.0"
    assert config.text_to_speech.voice_preset == "af_heart"
    assert config.text_to_speech.device == "cuda"


def test_model_config_validation():
    with pytest.raises(ValueError):
        ModelConfig(
            text_generation=TextGenerationConfig(story="", content_moderation="", proofreading=""),
            content_safety=ContentSafetyConfig(safety_model="", scientific_accuracy=""),
        )


# Paths Config Tests
def test_paths_config_creation(tmp_path):
    base_path = tmp_path / "base"
    output_path = tmp_path / "output"

    config = PathsConfig(base=base_path, output=output_path)

    assert base_path.exists()
    assert output_path.exists()
    assert config.base == base_path
    assert config.output == output_path


# PDF Config Tests
def test_pdf_config_defaults():
    config = PDFConfig()
    # Long portrait dimensions (7 x 10 inches in points)
    assert abs(config.page_size[0] - 504.0) < 1e-1  # 7 inch width in points
    assert abs(config.page_size[1] - 720.0) < 1e-1  # 10 inch height in points
    # Use tolerance for floating point comparisons
    assert abs(config.margin_top - 43.2) < 1e-1  # 0.6 inch in points
    assert abs(config.margin_bottom - 43.2) < 1e-1  # 0.6 inch in points
    assert abs(config.margin_left - 43.2) < 1e-1  # 0.6 inch in points
    assert abs(config.margin_right - 43.2) < 1e-1  # 0.6 inch in points
    assert config.title_font == "Helvetica-Bold"
    assert config.body_font == "Helvetica"
    assert config.title_font_size == 24
    assert config.body_font_size == 16
    assert config.title_color == "#1565C0"  # Dark blue
    assert config.body_color == "#212121"  # Very dark gray
    assert config.line_height_multiplier == 1.4
    assert config.image_width == 324.0  # 4.5 inch in points
    assert config.image_height == 252.0  # 3.5 inch in points


# API Config Tests
def test_api_config_env_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    config = APIConfig()
    assert config.keys["openai"] == "test-openai-key"


# Style Config Tests
def test_style_config_defaults():
    config = StyleConfig()
    assert config.illustration["style_preset"] == "children's book illustration"
    assert config.illustration["color_scheme"] == "bright and cheerful"
    assert config.music["happy"] == "upbeat orchestral with playful melodies"
    assert config.music["sad"] == "gentle piano with soft strings"
    assert config.video["animation_style"] == "3D animation with 2D elements"
    assert config.video["color_palette"] == "vibrant and child-friendly"


# Prompts Config Tests
def test_prompts_config_defaults():
    config = PromptsConfig()
    # Check for actual keywords that appear in the prompts
    assert "quality assurance" in config.proof_agent.lower()
    assert "creative writing" in config.critical_reviewer.lower()
    assert "safety" in config.content_moderator.lower()
    assert "editor" in config.editor.lower()
    assert "literature mentor" in config.author_friend.lower()
    assert "illustration strategist" in config.image_planner.lower()
    assert "illustrator" in config.illustrator.lower()
    assert "music" in config.composer.lower()
    assert "designer" in config.book_producer.lower()


# Agent Types Config Tests
def test_agent_types_config_defaults():
    config = AgentTypesConfig()
    assert config.author_friend == "StoryAuthorFriendAgent"
    assert config.critique == "CritiqueAgent"
    assert config.content_moderator == "ModeratorAgent"
    assert config.editor == "EditorAgent"
    assert config.format_proof == "FormatProofAgent"
    assert config.narrator == "NarratorAgent"
    assert config.illustrator == "IllustratorAgent"
    assert config.illustration_planner == "IllustratorPlannerAgent"
    assert config.producer == "BookProducerAgent"
    assert config.user == "User"
    assert config.movie_director_type == "MovieDirectorAgent"
    assert config.music_director == "MusicDirectorAgent"
    assert config.musician == "MusicianAgent"
    assert config.animator == "AnimatorAgent"
    assert config.movie_producer == "MovieProducerAgent"


# YAML Loading Tests
def test_yaml_loading(test_yaml_path):
    settings = Settings.from_yaml(test_yaml_path)
    assert settings.model.server.url == "http://test-server:8000/v1"
    assert settings.model.server.api_key == "test-key"
    assert settings.model.default == "test-model"


def test_yaml_template_substitution(test_yaml_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    settings = Settings.from_yaml(test_yaml_path)

    # Test model default substitution
    assert settings.model.text_generation.story == "test-model"
    assert settings.model.text_generation.content_moderation == "test-model"
    assert settings.model.text_generation.proofreading == "test-model"
    assert settings.model.content_safety.safety_model == "test-model"
    assert settings.model.content_safety.scientific_accuracy == "test-model"

    # Test environment variable substitution
    assert settings.api.keys["openai"] == "test-openai-key"


def test_yaml_style_config(test_yaml_path):
    settings = Settings.from_yaml(test_yaml_path)

    # Test illustration style
    assert settings.style.illustration["style_preset"] == "test-style"
    assert settings.style.illustration["color_scheme"] == "test-colors"
    assert settings.style.illustration["art_style"] == "test-art"

    # Test music style
    assert settings.style.music["happy"] == "test-happy"
    assert settings.style.music["sad"] == "test-sad"
    assert settings.style.music["adventure"] == "test-adventure"
    assert settings.style.music["mystery"] == "test-mystery"

    # Test video style
    assert settings.style.video["animation_style"] == "test-animation"
    assert settings.style.video["color_palette"] == "test-palette"
    assert settings.style.video["camera_style"] == "test-camera"


def test_yaml_prompts_config(test_yaml_path):
    settings = Settings.from_yaml(test_yaml_path)

    assert settings.prompts.proof_agent == "Test proof agent prompt"
    assert settings.prompts.critical_reviewer == "Test critical reviewer prompt"
    assert settings.prompts.content_moderator == "Test content moderator prompt"
    assert settings.prompts.editor == "Test editor prompt"
    assert settings.prompts.author_friend == "Test author friend prompt"
    assert settings.prompts.movie_director == "Test movie director prompt"
    assert settings.prompts.image_planner == "Test image planner prompt"
    assert settings.prompts.illustrator == "Test illustrator prompt"
    assert settings.prompts.composer == "Test composer prompt"
    assert settings.prompts.book_producer == "Test book producer prompt"


def test_yaml_agent_types_config(test_yaml_path):
    settings = Settings.from_yaml(test_yaml_path)

    assert settings.agent_types.author_friend == "TestAuthorFriendAgent"
    assert settings.agent_types.critique == "TestCritiqueAgent"
    assert settings.agent_types.content_moderator == "TestModeratorAgent"
    assert settings.agent_types.editor == "TestEditorAgent"
    assert settings.agent_types.format_proof == "TestFormatProofAgent"
    assert settings.agent_types.narrator == "TestNarratorAgent"
    assert settings.agent_types.illustrator == "TestIllustratorAgent"
    assert settings.agent_types.illustration_planner == "TestIllustratorPlannerAgent"
    assert settings.agent_types.producer == "TestBookProducerAgent"
    assert settings.agent_types.user == "TestUser"
    assert settings.agent_types.movie_director_type == "TestMovieDirectorType"
    assert settings.agent_types.music_director == "TestMusicDirectorAgent"
    assert settings.agent_types.musician == "TestMusicianAgent"
    assert settings.agent_types.animator == "TestAnimatorAgent"
    assert settings.agent_types.movie_producer == "TestMovieProducerAgent"


# Error Handling Tests
def test_yaml_invalid_path():
    with pytest.raises(FileNotFoundError):
        Settings.from_yaml("nonexistent_config.yaml")


def test_yaml_invalid_content(tmp_path):
    invalid_config = tmp_path / "invalid_config.yaml"
    invalid_config.write_text("invalid: yaml: content: [")

    with pytest.raises((ValueError, yaml.YAMLError)):
        Settings.from_yaml(invalid_config)


def test_yaml_missing_required_fields(tmp_path):
    incomplete_config = tmp_path / "incomplete_config.yaml"
    incomplete_config.write_text("""
    model:
      server:
        url: "http://test-server:8000/v1"
    """)

    with pytest.raises(ValueError):
        Settings.from_yaml(incomplete_config)
