# FableFlow Core API 🔌

Programmatic and CLI access to the book-first generation pipeline. The pipeline runs in two phases — **Phase 1** builds the book (`book_content.json` → PDF/EPUB), **Phase 2** adapts it to a movie (MP4).

## 🚀 Getting Started

### Installation

**Prerequisites:** Python 3.13, Git, and (for media generation) a CUDA GPU.

```bash
git clone https://github.com/suneeta-mall/fable-flow.git
cd fable-flow
make install        # uv sync — creates .venv from uv.lock
```

### Environment Configuration

The LLM client uses the OpenAI wire format and points at any compatible server. Set these in `.env`:

```bash
MODEL_SERVER_URL=http://localhost:8000/v1   # vLLM, Ollama, or a hosted proxy
MODEL_API_KEY=your-api-key
DEFAULT_MODEL=google/gemma-4-31B-it
```

See [Configuration](../getting-started/configuration.md) for the full set of options.

### CLI Usage

The CLI exposes two commands:

```bash
# Validate an input spec without generating anything
fable-flow validate examples/cassie_beach_adventure_input.json

# Run the full pipeline: story → book (PDF/EPUB) → movie
fable-flow generate examples/cassie_beach_adventure_input.json
```

`generate` options:

| Flag | Effect |
|------|--------|
| `--output, -o DIR` | Output directory (default `output/<input_name>`) |
| `--model, -m NAME` | Override the LLM from config |
| `--book-only` | Skip Phase 2 (movie) |
| `--skip-book-publish` | Skip PDF/EPUB rendering (`book_content.json` is still written) |
| `--resume` | Reuse artifacts already on disk; only generate what's missing |

Or via the Makefile:

```bash
make run INPUT=examples/cassie_beach_adventure_input.json
make validate INPUT=examples/cassie_beach_adventure_input.json
```

## 📋 Architecture

FableFlow is a sequence of focused agents, each calling an LLM or media model. The book is the authoritative artifact; the movie adapts from it.

**Phase 1 — Book** (`fable_flow.agents`)

- `DraftStoryAgent`, `StoryEditorAgent`, `FinalProofAgent` — draft, edit, proof the story (`story_development.py`)
- `ChapterStructureAgent`, `IllustrationPlacementAgent` — chapters and illustration plan (`book_assembly.py`)
- `CharacterReferenceAgent` — canonical character reference images (`character_ref.py`)
- `IllustrationGeneratorAgent` — render illustrations (`book_assembly.py`)
- `CoverDesignerAgent` — front/back covers (`cover_designer.py`)
- `BiographyAgent`, `ExperimentDesignerAgent`, `ReflectionGeneratorAgent` — enrichment (`enrichment.py`)
- `create_book_content()` orchestrates these into a `BookContent`

**Phase 2 — Movie** (`fable_flow.agents`)

- `SceneExtractorAgent` — break the book into scenes (`movie_adaptation.py`)
- `SceneProductionCoordinator` — narration-first multimedia per scene (`scene_production.py`)
- `MovieAssemblerAgent` — assemble the final MP4 (`movie_adaptation.py`)

See the [complete workflow](../fableflow-workflow.md) for how these connect.

## 🔧 Configuration

`fable_flow.config` exposes a single validated `config` object loaded from `config/default.yaml` + `.env`.

```python
from fable_flow.config import config

config.model.server.url                 # e.g. http://localhost:8000/v1
config.model.default                    # e.g. google/gemma-4-31B-it
config.model.image_generation.model     # e.g. black-forest-labs/FLUX.2-dev
config.paths.output                     # Path("output")
```

Key config groups (see `producer/fable_flow/config.py`): `ModelServerConfig`, `ModelConfig`, `ImageGenerationConfig`, `TextToSpeechConfig`, `MusicGenerationConfig`, `VideoGenerationConfig`, `PathsConfig`, `StyleConfig`, `PDFConfig`, `BookConfig`.

## 🤖 Model Classes

Each media type is wrapped in an `Enhanced*Model` class in `fable_flow.models`. All generation methods are async.

```python
from fable_flow.models.text import EnhancedTextModel

model = EnhancedTextModel()                       # uses config.model.default
text = await model.generate(
    prompt="Enhance this story: ...",
    system_message="You are a children's book editor.",
    temperature=0.7,
)
```

| Class | Method | Returns |
|-------|--------|---------|
| `EnhancedTextModel` | `generate(prompt, system_message, temperature=None, max_tokens=None)` | `str` |
| `EnhancedImageModel` | `generate_image(prompt, width, height, seed, negative_prompt)` | `bytes` (PNG) |
| `EnhancedImageModel` | `generate_with_reference(prompt, reference_image_path, ...)` | `bytes` (PNG) |
| `EnhancedTTSModel` | `generate_speech(text, voice_id=None)` | `bytes` |
| `EnhancedMusicModel` | `generate_music(prompt, max_new_tokens=256)` | `bytes` |
| `EnhancedVideoModel` | `generate_video(...)` | video frames |

The image/video/music/TTS classes load their pipelines on construction and expose `release()` to free GPU memory.

## 📖 Book Generation

Books render from a `BookContent` object via `fable_flow.publishers`:

```python
from pathlib import Path
from fable_flow.schemas.book_content import BookContent
from fable_flow.publishers import generate_pdf, generate_epub

book = BookContent.from_json_file("output/my_book/book_content.json")
generate_pdf(book, Path("output/my_book/book.pdf"))
generate_epub(book, Path("output/my_book/book.epub"))
```

Both are CPU-only (ReportLab for PDF, a zipped EPUB 3 package) and read styling from `config.pdf` / `config.book`.

## 🔗 Programmatic Usage

Run the full pipeline from Python by reusing the CLI entry point:

```python
import asyncio
from pathlib import Path
from fable_flow.app import _run_pipeline

asyncio.run(_run_pipeline(
    input_file=Path("examples/cassie_beach_adventure_input.json"),
    output_dir=Path("output/cassie"),
    model=None,
    book_only=True,
    skip_book_publish=False,
    resume=True,
))
```

Or drive individual agents directly — load a `FableFlowInput`, then call the agent you need:

```python
from fable_flow.schemas.input_spec import FableFlowInput
from fable_flow.agents.story_development import DraftStoryAgent

spec = FableFlowInput.from_json_file("examples/cassie_beach_adventure_input.json")
draft = await DraftStoryAgent().generate_story(spec)
```

## 🖥️ FableFlow Studio

Studio is a separate web app for editing `book_content.json` and re-running media generation. It reuses the schemas, models, and publishers above.

```bash
make studio-start    # API on :8077, UI on http://localhost:3000
```

Key endpoints (`studio/api.py`): `GET /api/projects`, `GET|POST /api/book`, `POST /api/ai/improve`, `POST /api/ai/chat`, `POST /api/image/regenerate`, `POST /api/publish`.

## 📚 Data Models

All artifacts are Pydantic models with `from_json_file()` / `to_json_file()`:

- `FableFlowInput` (`schemas/input_spec.py`) — project, characters, story seed, production config
- `BookContent` (`schemas/book_content.py`) — `BookMetadata`, `Chapter[]`, `IllustrationSpec`, `Experiment`, `Biography`, `CoverImages`
- `SceneManifest` (`schemas/scene_manifest.py`) — `SceneSpec[]` plus narration/image/video/music/subtitle assets

## 🧪 Testing

```bash
make test                                  # full suite
uv run pytest tests/unit/agents -q         # a subset
uv run pytest --cov=fable_flow             # with coverage
```

## 📖 Further Documentation

- **[Complete Workflow](../fableflow-workflow.md)** — agents and pipeline details
- **[Story Processing](../features/story-processing.md)** — draft → edit → proof
- **[Book Production](../features/book-production.md)** — PDF/EPUB generation
- **[Illustration Generation](../features/illustrations.md)** — image generation
- **[Configuration](../getting-started/configuration.md)** — all config options
