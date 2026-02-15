"""FableFlow CLI: end-to-end book + movie generation pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from fable_flow.agents.book_assembly import IllustrationGeneratorAgent, create_book_content
from fable_flow.agents.cover_designer import CoverDesignerAgent
from fable_flow.agents.movie_adaptation import MovieAssemblerAgent, SceneExtractorAgent
from fable_flow.agents.scene_production import SceneProductionCoordinator
from fable_flow.agents.story_development import (
    DraftStoryAgent,
    FinalProofAgent,
    StoryEditorAgent,
)
from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.schemas.book_content import BookContent
from fable_flow.schemas.input_spec import CharacterRole, FableFlowInput
from fable_flow.schemas.scene_manifest import SceneManifest

app = typer.Typer(
    name="fable-flow",
    help="AI-powered children's book and movie generation",
    no_args_is_help=True,
)
console = Console()


@app.command("validate")
def validate(
    input_file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
) -> None:
    """Validate an input JSON specification without generating content."""
    input_spec = FableFlowInput.from_json_file(input_file)
    summary = _summarize_input(input_spec)
    console.print(Panel.fit(summary, title="Valid input", border_style="green"))


@app.command("generate")
def generate(
    input_file: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    output_dir: Path = typer.Option(
        None, "--output", "-o", help="Output directory (defaults to output/<input_name>)"
    ),
    model: str = typer.Option(None, "--model", "-m", help="LLM name (overrides config)"),
    book_only: bool = typer.Option(False, "--book-only", help="Skip movie production"),
    skip_book_publish: bool = typer.Option(
        False, "--skip-book-publish", help="Skip PDF/EPUB rendering (book_content.json still saved)"
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Reuse any artifact already on disk; only generate missing/incomplete pieces",
    ),
) -> None:
    """Run the full pipeline: story → book (PDF/EPUB) → movie."""
    if output_dir is None:
        output_dir = Path("output") / input_file.stem

    try:
        asyncio.run(
            _run_pipeline(input_file, output_dir, model, book_only, skip_book_publish, resume)
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
        raise typer.Exit(130) from None
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


async def _run_pipeline(
    input_file: Path,
    output_dir: Path,
    model: str | None,
    book_only: bool,
    skip_book_publish: bool,
    resume: bool,
) -> None:
    input_spec = FableFlowInput.from_json_file(input_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel.fit(
            "[bold cyan]FableFlow Pipeline[/bold cyan]\n"
            "Book-first generation: story → book → movie"
            + ("\n[dim]resume mode: reusing existing artifacts[/dim]" if resume else ""),
            border_style="cyan",
        )
    )
    console.print(_summarize_input(input_spec))

    book_content = await _phase_one_book(
        input_spec, model, output_dir, skip_book_publish, resume=resume
    )

    if book_only or not input_spec.production_config.movie.enabled:
        console.print("[yellow]Movie generation skipped.[/yellow]")
        return

    await _phase_two_movie(book_content, input_spec, model, output_dir, resume=resume)


def _read_or_generate(path: Path, resume: bool) -> str | None:
    """If resuming and the file is on disk, return its text; otherwise None."""
    if resume and path.exists():
        logger.info(f"Resume: reusing {path.name}")
        console.print(f"[dim]↩ reusing {path.name}[/dim]")
        return path.read_text(encoding="utf-8")
    return None


async def _phase_one_book(
    input_spec: FableFlowInput,
    model: str | None,
    output_dir: Path,
    skip_book_publish: bool,
    resume: bool,
) -> BookContent:
    console.print(
        Panel.fit("[bold green]PHASE 1: BOOK GENERATION[/bold green]", border_style="green")
    )

    target_words = input_spec.production_config.book.page_count_target * 300

    draft_path = output_dir / "draft_story.txt"
    edited_path = output_dir / "edited_story.txt"
    final_path = output_dir / "final_story.txt"

    draft = _read_or_generate(draft_path, resume)
    if draft is None:
        console.print(f"\n[cyan]→[/cyan] Drafting story (~{target_words} words)")
        draft = await DraftStoryAgent(
            model=model, output_dir=output_dir, word_count_target=target_words
        ).generate_story(input_spec)
    console.print(f"[green]✓[/green] Draft: {len(draft.split())} words")

    edited = _read_or_generate(edited_path, resume)
    if edited is None:
        console.print("\n[cyan]→[/cyan] Editing story")
        edited = await StoryEditorAgent(model=model, output_dir=output_dir).edit_story(
            draft, input_spec
        )
    console.print(f"[green]✓[/green] Edited: {len(edited.split())} words")

    final_story = _read_or_generate(final_path, resume)
    if final_story is None:
        console.print("\n[cyan]→[/cyan] Final proof")
        final_story = await FinalProofAgent(model=model, output_dir=output_dir).proof_story(
            edited, input_spec
        )
    console.print(f"[green]✓[/green] Proofed: {len(final_story.split())} words")

    book_content_path = output_dir / "book_content.json"
    if resume and book_content_path.exists():
        console.print("[dim]↩ reusing book_content.json (LLM steps skipped)[/dim]")
    else:
        console.print("\n[cyan]→[/cyan] Building chapters and illustration plan")

    # LLM steps first; no image model loaded yet so we don't fight vLLM for VRAM.
    book_content = await create_book_content(
        final_story,
        input_spec,
        image_model=None,
        output_dir=output_dir,
        resume=resume,
    )
    total_illustrations = sum(len(ch.illustrations) for ch in book_content.chapters)
    console.print(
        f"[green]✓[/green] {len(book_content.chapters)} chapters, "
        f"{total_illustrations} illustrations planned"
    )

    missing_illustrations = [
        ill
        for ch in book_content.chapters
        for ill in ch.illustrations
        if not (ill.image_path and Path(ill.image_path).exists())
    ]
    cover_exists = (
        book_content.cover is not None
        and Path(book_content.cover.front_path).exists()
        and Path(book_content.cover.back_path).exists()
    )
    cover_needed = not (resume and cover_exists)
    if missing_illustrations or cover_needed:
        if missing_illustrations:
            console.print(
                f"\n[cyan]→[/cyan] Rendering {len(missing_illustrations)} "
                f"of {total_illustrations} illustrations"
            )
        image_model = _load_image_model()
        try:
            if missing_illustrations:
                await IllustrationGeneratorAgent(image_model, output_dir=output_dir).generate_all(
                    book_content.chapters,
                    input_spec.characters,
                    motifs=input_spec.production_config.book.illustration_motifs,
                    resume=resume,
                )
            if cover_needed:
                console.print("\n[cyan]→[/cyan] Designing front + back covers")
                protagonist_name = next(
                    (c.name for c in input_spec.characters if c.role == CharacterRole.PROTAGONIST),
                    None,
                )
                book_content.cover = await CoverDesignerAgent(
                    image_model, output_dir=output_dir
                ).design_covers(
                    book_content,
                    characters=input_spec.characters,
                    protagonist_name=protagonist_name,
                    resume=resume,
                )
                console.print(
                    f"[green]✓[/green] Covers: {Path(book_content.cover.front_path).name}, "
                    f"{Path(book_content.cover.back_path).name}"
                )
            book_content.to_json_file(book_content_path)
        finally:
            image_model.release()
    else:
        console.print("[dim]↩ all illustrations and covers already on disk[/dim]")

    if skip_book_publish:
        console.print("[yellow]Skipping PDF/EPUB rendering as requested.[/yellow]")
    else:
        formats = set(input_spec.production_config.book.format)
        title_slug = _safe_filename(book_content.metadata.title)
        if "pdf" in formats:
            pdf_path = output_dir / f"{title_slug}.pdf"
            if resume and pdf_path.exists():
                console.print(f"[dim]↩ reusing {pdf_path.name}[/dim]")
            else:
                console.print("\n[cyan]→[/cyan] Generating PDF")
                await asyncio.to_thread(generate_pdf, book_content, pdf_path)
                console.print(f"[green]✓[/green] PDF: {pdf_path}")
        if "epub" in formats:
            epub_path = output_dir / f"{title_slug}.epub"
            if resume and epub_path.exists():
                console.print(f"[dim]↩ reusing {epub_path.name}[/dim]")
            else:
                console.print("\n[cyan]→[/cyan] Generating EPUB")
                await asyncio.to_thread(generate_epub, book_content, epub_path)
                console.print(f"[green]✓[/green] EPUB: {epub_path}")

    console.print(
        Panel.fit(
            f"[bold green]✓ PHASE 1 COMPLETE[/bold green]\nBook content at {book_content_path}",
            border_style="green",
        )
    )
    return book_content


async def _phase_two_movie(
    book_content: BookContent,
    input_spec: FableFlowInput,
    model: str | None,
    output_dir: Path,
    resume: bool,
) -> None:
    console.print(
        Panel.fit("[bold blue]PHASE 2: MOVIE ADAPTATION[/bold blue]", border_style="blue")
    )

    movie_filename = f"{_safe_filename(book_content.metadata.title)}.mp4"
    movie_path = output_dir / movie_filename
    manifest_path = output_dir / "scene_manifest.json"

    if resume and manifest_path.exists():
        console.print(f"[dim]↩ reusing {manifest_path.name}[/dim]")
        manifest = SceneManifest.from_json_file(manifest_path)
    else:
        console.print("\n[cyan]→[/cyan] Extracting scenes")
        manifest = await SceneExtractorAgent(model=model, output_dir=output_dir).extract_scenes(
            book_content
        )
    console.print(
        f"[green]✓[/green] {manifest.total_scenes} scenes, "
        f"~{manifest.estimated_total_duration / 60:.1f} min estimated"
    )

    if resume and movie_path.exists() and _all_scenes_composited(manifest):
        console.print(f"[dim]↩ reusing existing {movie_path.name}; nothing to do[/dim]")
        console.print(
            Panel.fit(
                f"[bold blue]✓ PHASE 2 COMPLETE (resumed)[/bold blue]\n🎬 {movie_path}",
                border_style="blue",
            )
        )
        return

    console.print("\n[cyan]→[/cyan] Loading multimedia models")
    tts_model = _load_tts_model()
    music_model = _load_music_model()
    image_model = _load_image_model()
    video_model = _load_video_model()

    coordinator = SceneProductionCoordinator(
        tts_model=tts_model,
        music_model=music_model,
        image_model=image_model,
        video_model=video_model,
        characters=input_spec.characters,
        output_dir=output_dir,
        character_references=book_content.character_references,
        target_age=input_spec.project.target_age,
    )

    def save_manifest() -> None:
        manifest.to_json_file(manifest_path)

    try:
        console.print("\n[cyan]→[/cyan] Producing scenes")
        for i, scene in enumerate(manifest.scenes, 1):
            console.print(f"  [{i}/{manifest.total_scenes}] {scene.id}")
            await coordinator.produce_scene(scene, resume=resume, on_step_complete=save_manifest)
            save_manifest()

        console.print("\n[cyan]→[/cyan] Assembling movie")
        movie_path_str = await MovieAssemblerAgent(output_dir=output_dir).assemble_movie(
            manifest, output_filename=movie_filename, resume=resume
        )
        console.print(f"[green]✓[/green] Movie: {movie_path_str}")
    finally:
        for m in (video_model, image_model, music_model):
            if m is not None and hasattr(m, "release"):
                m.release()

    console.print(
        Panel.fit(
            f"[bold blue]✓ PHASE 2 COMPLETE[/bold blue]\n"
            f"🎬 {manifest.total_scenes} scenes, {manifest.estimated_total_duration / 60:.1f} min",
            border_style="blue",
        )
    )


def _all_scenes_composited(manifest: SceneManifest) -> bool:
    return all(s.composite and Path(s.composite).exists() for s in manifest.scenes)


def _load_image_model():
    from fable_flow.models.image import EnhancedImageModel

    return EnhancedImageModel()


def _load_tts_model():
    from fable_flow.models.tts import EnhancedTTSModel

    return EnhancedTTSModel()


def _load_music_model():
    from fable_flow.models.music import EnhancedMusicModel

    return EnhancedMusicModel()


def _load_video_model():
    from fable_flow.models.video import EnhancedVideoModel

    return EnhancedVideoModel()


def _safe_filename(title: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title)
    return cleaned.strip().lower().replace(" ", "_")[:80] or "fableflow_book"


def _summarize_input(spec: FableFlowInput) -> str:
    char_lines = "\n".join(f"  - {c.name} ({c.role.value})" for c in spec.characters)
    return (
        f"[bold]Project:[/bold] {spec.project.title}\n"
        f"[bold]Target Age:[/bold] {spec.project.target_age}\n"
        f"[bold]Genre:[/bold] {spec.project.genre}\n"
        f"[bold]Characters:[/bold]\n{char_lines}\n"
        f"[bold]Theme:[/bold] {spec.story_seed.theme}\n"
        f"[bold]Setting:[/bold] {spec.story_seed.setting.primary}\n"
        f"[bold]Target Pages:[/bold] {spec.production_config.book.page_count_target}\n"
        f"[bold]Movie Enabled:[/bold] {'Yes' if spec.production_config.movie.enabled else 'No'}"
    )


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
