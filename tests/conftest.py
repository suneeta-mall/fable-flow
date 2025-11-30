from unittest.mock import AsyncMock, MagicMock

import pytest

from fable_flow.config import (
    AgentTypesConfig,
    APIConfig,
    ContentSafetyConfig,
    ImageGenerationConfig,
    ModelConfig,
    PathsConfig,
    PromptsConfig,
    Settings,
    StyleConfig,
    TextGenerationConfig,
    TextToSpeechConfig,
)


@pytest.fixture
def mock_story_data():
    return {
        "story": "A magical tale unfolds in an enchanted forest...",
        "synopsis": "An epic adventure of friendship and courage...",
    }


@pytest.fixture
def mock_model_client():
    client = MagicMock()
    client.create = AsyncMock()
    return client


@pytest.fixture
def mock_runtime():
    runtime = AsyncMock()
    runtime.register_factory = AsyncMock()
    runtime.start = AsyncMock()
    runtime.publish_message = AsyncMock()
    runtime.stop_when_idle = AsyncMock()
    return runtime


@pytest.fixture
def test_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def test_output_dir(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_settings(tmp_path):
    return Settings(
        model=ModelConfig(
            text_generation=TextGenerationConfig(
                story="test", content_moderation="test", proofreading="test"
            ),
            content_safety=ContentSafetyConfig(safety_model="test", scientific_accuracy="test"),
            image_generation=ImageGenerationConfig(
                model="test-image-model", style_consistency="test-style-model"
            ),
            text_to_speech=TextToSpeechConfig(model="test-tts-model", device="cpu"),
            music_generation={"model": "test-music-model"},
            video_generation={
                "model": "test-video-model",
                "num_frames": 81,
                "num_inference_steps": 50,
                "guidance_scale": 6,
                "fps": 8,
            },
        ),
        paths=PathsConfig(base=tmp_path / "base", output=tmp_path / "output"),
        api=APIConfig(
            keys={
                "openai": "test-openai-key",
            }
        ),
        style=StyleConfig(),
        prompts=PromptsConfig(),
        agent_types=AgentTypesConfig(),
    )
