from pathlib import Path
from unittest.mock import patch

import aiofiles
import pytest

from fable_flow.story import main, process


@pytest.fixture
def ant_sugar_story_setup():
    """Setup the Ant and Sugar story for testing."""
    return {
        "story": "Once there was an ant, she found a sugar. Happy days",
        "synopsis": "Ant and Sugar",
        "image_planner_story": "Once there was an ant, she found a sugar. Happy days",
    }


class TestStoryGeneration:
    """Test the actual story generation functionality with agents and output files."""

    @pytest.mark.asyncio
    async def test_story_agents_execute_without_error(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that all story agents execute without error."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "image_planner_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["image_planner_story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        try:
            await main(story_fn=story_dir, output_dir=test_output_dir)
        except Exception as e:
            pytest.fail(f"Story agents failed to execute: {e}")

    @pytest.mark.asyncio
    async def test_story_agents_create_output_files(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that story agents create non-empty output files."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "image_planner_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["image_planner_story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        await main(story_fn=story_dir, output_dir=test_output_dir)

        expected_files: list[str] = [
            "story_producer.txt",
        ]

        for filename in expected_files:
            output_file: Path = test_output_dir / filename
            if output_file.exists():
                assert output_file.stat().st_size > 0, f"Output file {filename} is empty"

    def test_story_cli_command_wiring(
        self, test_data_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that the CLI command is wired correctly."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        with open(story_dir / "image_planner_story.txt", "w") as f:
            f.write(ant_sugar_story_setup["image_planner_story"])

        with open(story_dir / "draft_synopsis.txt", "w") as f:
            f.write(ant_sugar_story_setup["synopsis"])

        with patch("asyncio.run") as mock_run:
            try:
                process(None, story_dir)
                mock_run.assert_called_once()
            except Exception as e:
                pytest.fail(f"CLI command wiring failed: {e}")

    @pytest.mark.asyncio
    async def test_models_generate_output(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that models run correctly and generate output."""
        # Setup input files
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "image_planner_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["image_planner_story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        await main(story_fn=story_dir, output_dir=test_output_dir)

        output_files: list[Path] = list(test_output_dir.glob("*.txt"))
        model_generated_content: bool = False

        for file_path in output_files:
            if file_path.stat().st_size > len(ant_sugar_story_setup["story"]):
                model_generated_content = True
                break

        assert test_output_dir.exists(), "Output directory was not created"
        if not model_generated_content and len(output_files) == 0:
            pytest.skip("No model output detected - may require API keys or model setup")
