from pathlib import Path
from unittest.mock import patch

import aiofiles
import pytest

from fable_flow.publisher import main, process


@pytest.fixture
def ant_sugar_story_setup() -> dict[str, str]:
    """Setup the Ant and Sugar story for testing."""
    return {
        "story": "Once there was an ant, she found a sugar. Happy days",
        "synopsis": "Ant and Sugar",
    }


class TestPublisherGeneration:
    """Test the actual publisher functionality with agents and output files."""

    @pytest.mark.asyncio
    async def test_publisher_agents_execute_without_error(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that all publisher agents execute without error."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "draft_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        try:
            await main(story_fn=story_dir, output_dir=test_output_dir)
        except Exception as e:
            pytest.fail(f"Publisher agents failed to execute: {e}")

    @pytest.mark.asyncio
    async def test_publisher_agents_create_output_files(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that publisher agents create non-empty output files."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "draft_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        await main(story_fn=story_dir, output_dir=test_output_dir)

        output_files: list[Path] = list(test_output_dir.rglob("*"))
        non_empty_files: int = sum(1 for f in output_files if f.is_file() and f.stat().st_size > 0)

        assert len(output_files) > 0, "No output files created by publisher agents"
        assert non_empty_files > 0, "All output files are empty"

    def test_publisher_cli_command_wiring(
        self, test_data_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that the CLI command is wired correctly."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()
        destination_dir: Path = test_data_dir / "publisher_output"
        destination_dir.mkdir()

        with open(story_dir / "draft_story.txt", "w") as f:
            f.write(ant_sugar_story_setup["story"])

        with open(story_dir / "draft_synopsis.txt", "w") as f:
            f.write(ant_sugar_story_setup["synopsis"])

        with patch("asyncio.run") as mock_run:
            try:
                process(None, story_dir, destination_dir, False)
                mock_run.assert_called_once()
            except Exception as e:
                pytest.fail(f"CLI command wiring failed: {e}")

    @pytest.mark.asyncio
    async def test_publisher_models_generate_output(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that publisher models run correctly and generate output."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "draft_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        await main(story_fn=story_dir, output_dir=test_output_dir)

        output_files: list[Path] = list(test_output_dir.rglob("*"))
        model_generated_content: bool = False

        for file_path in output_files:
            if file_path.is_file() and file_path.stat().st_size > 0:
                if file_path.suffix.lower() in [".pdf", ".html", ".txt", ".epub"]:
                    model_generated_content = True
                    break

        assert test_output_dir.exists(), "Output directory was not created"
        if not model_generated_content:
            pytest.skip("No publisher model output detected - may require API keys or model setup")

    @pytest.mark.asyncio
    async def test_publisher_simple_vs_full_mode(
        self, test_data_dir: Path, test_output_dir: Path, ant_sugar_story_setup: dict[str, str]
    ) -> None:
        """Test that simple vs full publishing modes work correctly."""
        story_dir: Path = test_data_dir / "ant_sugar"
        story_dir.mkdir()

        async with aiofiles.open(story_dir / "draft_story.txt", "w") as f:
            await f.write(ant_sugar_story_setup["story"])

        async with aiofiles.open(story_dir / "draft_synopsis.txt", "w") as f:
            await f.write(ant_sugar_story_setup["synopsis"])

        simple_output_dir: Path = test_output_dir / "simple"
        simple_output_dir.mkdir()
        await main(story_fn=story_dir, output_dir=simple_output_dir, simple_publish=True)

        full_output_dir: Path = test_output_dir / "full"
        full_output_dir.mkdir()
        await main(story_fn=story_dir, output_dir=full_output_dir, simple_publish=False)

        simple_files: list[Path] = list(simple_output_dir.rglob("*"))
        full_files: list[Path] = list(full_output_dir.rglob("*"))

        assert len(simple_files) > 0, "Simple mode created no output files"
        assert len(full_files) > 0, "Full mode created no output files"
