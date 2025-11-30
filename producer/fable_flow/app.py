import typer
from loguru import logger

from fable_flow.illustrator import app as illustrator_cli
from fable_flow.movie import app as director_cli
from fable_flow.music import app as music_cli
from fable_flow.narration import app as narration_cli
from fable_flow.publisher import app as publishing_pipeline_cli
from fable_flow.story import app as story_cli

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
app.add_typer(director_cli, name="director", help="Generate a video for the a story.")
app.add_typer(music_cli, name="music", help="Generate a music for the a story.")
app.add_typer(narration_cli, name="narration", help="Generate narration for the story.")
app.add_typer(story_cli, name="story", help="Generate a story.")
app.add_typer(illustrator_cli, name="illustrator", help="Generate a images for the story.")
app.add_typer(
    publishing_pipeline_cli,
    name="publisher",
    help="Gets a draft story ready for publishing.",
)


@app.callback()
def fable_flow(ctx: typer.Context) -> None:
    logger.info(
        "Welcome to Fable Flow! This tool helps you enhance your story by creating narration, generating illustrations, and producing videos.\n"
        "Available commands:\n"
        "  - publisher: Enhance your story, create narration, generate illustrations, and produce videos - an end-to-end publishing solution.\n"
        "    Example: fable-flow publisher <options>\n"
        "  - director: Generate a video for a given story.\n"
        "    Example: fable-flow director <options>\n"
        "  - music: Generate music for the story.\n"
        "    Example: fable-flow music <options>\n"
        "  - narration: Generate audio narration for the story.\n"
        "    Example: fable-flow narration <options>\n"
        "  - story: Enhance your story.\n"
        "    Example: fable-flow story <options>\n"
        "  - illustrator: Generate illustrative images for the story.\n"
        "    Example: fable-flow illustrator <options>\n"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    app()
