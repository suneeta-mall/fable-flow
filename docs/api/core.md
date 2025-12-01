# FableFlow Core API 🔌

The FableFlow Core API provides programmatic access to story creation and multimedia production capabilities through an agent-based architecture. This documentation covers the main components, CLI usage, and integration patterns.

## 🚀 Getting Started

### Installation and Setup

**Prerequisites:**
- Python 3.11+
- Git

**Step 1: Clone the Repository**

```bash
git clone https://github.com/suneeta-mall/fable-flow.git
cd fable-flow
```

**Step 2: Create Virtual Environment**

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# Or on Windows:
# .venv\Scripts\activate
```

**Step 3: Install Dependencies**

```bash
# Install all dependencies using Makefile
make install

# This installs:
# - Core FableFlow package (editable mode)
# - All production dependencies
# - Development dependencies (optional)
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Model Server Configuration
MODEL_API_KEY=your-api-key

# Option 1: Use OpenAI directly
MODEL_SERVER_URL=https://api.openai.com/v1

# Option 2: Use custom vLLM server
MODEL_SERVER_URL=http://localhost:8000/v1

# Option 3: Use Anthropic Claude
MODEL_SERVER_URL=https://api.anthropic.com/v1
```

### Basic CLI Usage

```bash
# Run complete publishing pipeline
fable-flow publisher process

# Individual production steps
fable-flow story process        # Story enhancement
fable-flow illustrator draw     # Generate illustrations
fable-flow narration produce    # Generate narration
fable-flow music produce        # Generate music
fable-flow director produce     # Generate video
```

## 📋 Core Architecture

### Agent-Based System

FableFlow uses a multi-agent architecture built on `autogen-core`. Each agent is a specialized AI that handles specific production tasks.

**Review Agents:**
- `FriendProofReaderAgent` - Initial readability and engagement feedback
- `CritiqueAgent` - Professional editorial analysis
- `ContentModeratorAgent` - Safety and appropriateness validation
- `EditorAgent` - Structure and narrative improvements
- `FormatProofAgent` - Final polish and formatting

**Production Agents:**
- `NarratorAgent` - Audio narration generation
- `IllustrationPlannerAgent` - Scene planning and prompt creation
- `IllustratorAgent` - Image generation
- `BookProducerAgent` - PDF, EPUB, HTML book generation
- `MusicDirectorAgent` - Music planning
- `MusicianAgent` - Music generation
- `MovieDirectorAgent` - Video planning
- `AnimatorAgent` - Animation/scene creation
- `MovieProducerAgent` - Final video assembly

See [complete workflow documentation](../fableflow-workflow.md) for agent collaboration details.

## 🔧 Configuration System

### Config Module (`fable_flow.config`)

FableFlow uses Pydantic-based configuration with YAML files and environment variables.

```python
from fable_flow.config import config

# Access configuration
print(config.model.server.url)
print(config.model.default)
print(config.paths.output)
```

### Configuration Classes

**ModelServerConfig**
```python
class ModelServerConfig(BaseModel):
    url: str = "http://localhost:8000/v1"
    api_key: str = "dev-api-key"
    timeout: float = 300.0
    max_retries: int = 3
    retry_delay: float = 2.0
```

**TextGenerationConfig**
```python
class TextGenerationConfig(BaseModel):
    story: str                    # Model for story enhancement
    content_moderation: str       # Model for safety checks
    proofreading: str            # Model for proofreading
```

**ImageGenerationConfig**
```python
class ImageGenerationConfig(BaseModel):
    model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    style_consistency: str = "stabilityai/stable-diffusion-xl-refiner-1.0"
```

**TextToSpeechConfig**
```python
class TextToSpeechConfig(BaseModel):
    voice_preset: str = "af_heart"
    sample_rate: int = 24000
    device: str = "cuda"
```

**PDFConfig**
```python
class PDFConfig(BaseModel):
    page_size: tuple[float, float] = (6 * 72, 9 * 72)  # 6x9 inches
    margin_top: float = 0.5 * 72
    margin_bottom: float = 0.5 * 72
    image_width: float = 4.0 * 72
    title_font: str = "Helvetica-Bold"
    body_font: str = "Times-Roman"
    # ... many more styling options
```

### Custom Configuration

Create `config/my_config.yaml`:

```yaml
model:
  server:
    url: https://api.openai.com/v1
    api_key: ${MODEL_API_KEY}
  default: claude-opus-4-20250514
  text_generation:
    story: claude-opus-4-20250514
    proofreading: claude-sonnet-4-20250514

paths:
  output: ./output
  books: ./docs/books

pdf:
  page_size: [612, 792]  # 8.5 x 11 inches
  title_font_size: 28
  body_font_size: 14
```

Load custom config:
```bash
export FABLE_FLOW_CONFIG=config/my_config.yaml
fable-flow publisher process
```

## 🤖 Model Classes

### EnhancedTextModel

Text generation with robust continuation support.

```python
from fable_flow.models import EnhancedTextModel

model = EnhancedTextModel(model_name="claude-opus-4-20250514")

# Generate text with continuation handling
response = await model.complete(
    messages=[
        {"role": "system", "content": "You are a children's story editor."},
        {"role": "user", "content": "Enhance this story: ..."}
    ],
    temperature=0.7,
    max_tokens=2000
)
```

**Key Features:**
- Automatic continuation handling for long responses
- Retry logic with exponential backoff
- Context management for multi-turn conversations
- Integration with OpenAI-compatible APIs

**Implementation:** `producer/fable_flow/models.py:38`

### ImageModel

Image generation using Stable Diffusion models.

```python
from fable_flow.models import ImageModel

# Initialize with model
image_model = ImageModel(model_name="stabilityai/stable-diffusion-xl-base-1.0")

# Generate image
image = image_model.generate(
    prompt="A curious little girl exploring a colorful garden",
    negative_prompt="blurry, low quality",
    num_inference_steps=50
)

# Save image
image.save("output/illustration.png")
```

**Supported Models:**
- Stable Diffusion XL
- Stable Diffusion 3
- Flux
- And other diffusers-compatible models

### AudioModel

Text-to-speech using Kokoro.

```python
from fable_flow.models import AudioModel

audio_model = AudioModel(
    voice_preset="af_heart",
    sample_rate=24000
)

# Generate narration
audio_data = audio_model.synthesize(
    text="Once upon a time, in a land far away..."
)

# Save audio
audio_model.save(audio_data, "output/narration.wav")
```

### MusicModel

Background music generation using MusicGen.

```python
from fable_flow.models import MusicModel

music_model = MusicModel()

# Generate music
audio = music_model.generate(
    description="upbeat orchestral children's adventure music",
    duration=30  # seconds
)
```

## 📖 Book Generation

### PDFGenerator Class

Professional PDF book generation using ReportLab.

```python
from fable_flow.pdf import PDFGenerator
from fable_flow.common import Manuscript
from pathlib import Path

# Initialize generator
pdf_generator = PDFGenerator(output_dir=Path("output"))

# Generate PDF (requires HTML formatted content)
manuscript = Manuscript(
    content="Story text...",
    metadata={"title": "My Story", "author": "Author Name"}
)

book_metadata = {
    "title": "My Story",
    "author": "Author Name",
    "publisher": "FableFlow Publishing",
    "copyright_year": "2024"
}

pdf_generator.generate_pdf(
    html_content=formatted_html,  # From BookStructureGenerator
    message=manuscript,
    output_path=Path("output/book.pdf"),
    book_metadata=book_metadata
)
```

**Key Features:**
- Professional layout with margins and typography
- Embedded illustrations with captions
- Table of contents with bookmarks
- Page numbers and headers
- Custom styling via `config.pdf`

**Key Methods:**
- `generate_pdf()` - Main PDF generation method
- `_create_document()` - Document setup
- `_process_pages()` - Page layout processing
- `_process_image_element()` - Image placement
- `_create_styles()` - Typography and styling

**Implementation:** `producer/fable_flow/pdf.py:70`

### EPUBGenerator Class

EPUB3 e-book generation.

```python
from fable_flow.epub import EPUBGenerator
from fable_flow.common import Manuscript
from pathlib import Path

# Initialize generator
epub_generator = EPUBGenerator(output_dir=Path("output"))

# Generate EPUB (requires HTML formatted content)
manuscript = Manuscript(
    content="Story text...",
    metadata={"title": "My Story", "author": "Author Name"}
)

book_metadata = {
    "title": "My Story",
    "author": "Author Name",
    "publisher": "FableFlow Publishing",
    "language": "en"
}

epub_generator.generate_epub(
    html_content=formatted_html,  # From BookStructureGenerator
    message=manuscript,
    output_path=Path("output/book.epub"),
    book_metadata=book_metadata
)
```

**Key Features:**
- EPUB3 standard compliance
- Responsive layout for e-readers
- NCX navigation for table of contents
- Embedded images with proper packaging
- Complete metadata for library systems

**Key Methods:**
- `generate_epub()` - Main EPUB generation method
- `_create_content_opf()` - Package document
- `_create_toc_ncx()` - Navigation file
- `_create_epub_cover_with_text()` - Cover generation

**Implementation:** `producer/fable_flow/epub.py:19`

### Book Structure Utilities

**BookStructureGenerator** - Generate structured HTML from story content:

```python
from fable_flow.book_structure import BookStructureGenerator
from fable_flow.common import Manuscript

generator = BookStructureGenerator()

# Generate formatted HTML book structure
html_content = await generator.generate_book_html(
    manuscript=Manuscript(
        content="Story text...",
        metadata={"title": "My Story"}
    )
)

# Returns complete HTML with proper book structure:
# - Front/back covers
# - Title page
# - Table of contents
# - Story chapters
# - Back matter
```

**BookContentProcessor** - Utilities for content processing:

```python
from fable_flow.book_utils import BookContentProcessor

processor = BookContentProcessor()

# Validate book metadata
validated_metadata = processor.validate_book_metadata({
    "title": "My Story",
    "author": "Author Name"
})

# Clean HTML content
cleaned_html = processor.clean_html_content(raw_html)
```

**Implementation:**
- `producer/fable_flow/book_structure.py:16`
- `producer/fable_flow/book_utils.py:17`

## 🎬 CLI Commands

### Publisher Pipeline

Complete end-to-end pipeline:

```bash
# Run full pipeline
fable-flow publisher process

# Customize output directory
fable-flow publisher process --output-dir custom/output
```

**Implementation:** `producer/fable_flow/publisher.py`

### Story Processing

Story enhancement and editorial review:

```bash
# Process story through 5-stage review
fable-flow story process

# Uses manuscript from configured paths
```

**Implementation:** `producer/fable_flow/story.py`

### Illustration Generation

Image generation for story scenes:

```bash
# Generate illustrations
fable-flow illustrator draw

# Requires processed story and image prompts
```

**Implementation:** `producer/fable_flow/illustrator.py`

### Narration Generation

Audio narration creation:

```bash
# Generate narration
fable-flow narration produce

# Requires processed story text
```

**Implementation:** `producer/fable_flow/narration.py`

### Music Generation

Background music creation:

```bash
# Generate background music
fable-flow music produce

# Requires story metadata for mood
```

**Implementation:** `producer/fable_flow/music.py`

### Video Production

Video assembly and generation:

```bash
# Generate final video
fable-flow director produce

# Requires images, narration, and music
```

**Implementation:** `producer/fable_flow/movie.py`

## 🔗 Integration Patterns

### Custom Agent Implementation

Extend the agent system:

```python
from autogen_core import RoutedAgent, message_handler
from fable_flow.models import EnhancedTextModel

class CustomReviewAgent(RoutedAgent):
    def __init__(self, model_client):
        super().__init__("Custom review agent")
        self._model_client = model_client

    @message_handler
    async def handle_message(self, message, ctx):
        # Process message
        result = await self._model_client.complete(
            messages=[{"role": "user", "content": message.content}]
        )

        # Publish to next agent
        await self.publish_message(...)
```

### Using FableFlow in Python

```python
import asyncio
from fable_flow.publisher import main as publisher_main
from pathlib import Path

async def create_book():
    # Run publisher pipeline
    await publisher_main(
        story_fn=Path("story/draft_story.txt"),
        output_dir=Path("output/")
    )

# Run
asyncio.run(create_book())
```

### FableFlow Studio Integration

The Studio web interface integrates with the core API:

```python
# studio/api.py
from fable_flow.publisher import main as publisher_main
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/process")
async def process_story(series: str, book: str):
    story_path = Path(f"docs/books/{series}/{book}")
    await publisher_main(story_fn=story_path / "draft_story.txt")
    return {"status": "completed"}
```

## 📚 Data Models

### Manuscript Model

```python
from fable_flow.common import Manuscript

manuscript = Manuscript(
    content="Story text...",
    metadata={
        "title": "My Story",
        "author": "Author Name",
        "target_age": "6-8"
    }
)
```

**Implementation:** `producer/fable_flow/common.py`

### Story Formatter

```python
from fable_flow.story_formatter import StoryFormatter

formatter = StoryFormatter()
formatted = formatter.format(
    raw_text="unformatted story",
    style="children's book"
)
```

**Implementation:** `producer/fable_flow/story_formatter.py`

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=fable_flow --cov-report=html

# Run specific test
python -m pytest tests/test_agents.py -v
```

### Example Test

```python
import pytest
from fable_flow.config import config
from fable_flow.models import EnhancedTextModel

@pytest.mark.asyncio
async def test_text_generation():
    model = EnhancedTextModel(model_name=config.model.default)

    response = await model.complete(
        messages=[
            {"role": "user", "content": "Write a short story opening."}
        ],
        max_tokens=100
    )

    assert response.content
    assert len(response.content) > 0
```

## 📖 Further Documentation

- **[Complete Workflow](../fableflow-workflow.md)** - Agent collaboration and pipeline details
- **[Story Processing](../features/story-processing.md)** - 5-stage editorial review
- **[Book Production](../features/book-production.md)** - PDF/EPUB/HTML generation
- **[Illustration Generation](../features/illustrations.md)** - Image generation details
- **[CLI Reference](../create/index.md)** - Complete command reference

---

**Note:** FableFlow uses an agent-based architecture with asynchronous message passing. There is no single `StoryProcessor` class; instead, specialized agents collaborate through a message-passing system to create complete multimedia stories.

For implementation details, see the source code in `producer/fable_flow/` directory.
