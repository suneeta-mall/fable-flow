# Claude Instructions for FableFlow

**FableFlow** is an open-source AI-powered multimedia story production platform that transforms story manuscripts into complete multimedia experiences through AI-powered narration, illustrations, video production, book generation (PDF/EPUB/HTML), and music composition.

## 🎯 Project Overview

FableFlow is an **agentic AI story creation application** that automates the entire publishing pipeline from draft manuscripts to production-ready multimedia content. The system uses multiple specialized AI agents working together to enhance stories and create engaging multimedia experiences for children's educational content.

### Core Capabilities
- **📚 Story Enhancement**: AI-powered manuscript refinement through multi-stage editorial review
- **🎙️ AI Narration**: Convert text to professional-quality audio narration
- **🎨 Illustration Generation**: Create consistent, contextual illustrations using AI image generation
- **🎵 Music Composition**: Generate background scores that complement narratives
- **🎬 Video Production**: Combine narration, illustrations, and music into engaging videos
- **📕 Book Production**: Generate professional books in multiple formats (PDF, EPUB, HTML)
- **🎨 FableFlow Studio**: Web-based workspace for managing projects and running production workflows

## 🏗️ Architecture & Project Structure

### Three Main Components

```
fable-flow/
├── producer/                    # Core AI production pipeline
│   └── fable_flow/             # Main Python package
│       ├── agents.py           # AI agent orchestration and implementations
│       ├── app.py              # CLI entry point (Typer commands)
│       ├── book_structure.py   # Book structure and formatting logic
│       ├── book_utils.py       # Book generation utilities
│       ├── client.py           # External API clients
│       ├── common.py           # Shared utilities
│       ├── config.py           # Configuration management (Pydantic models)
│       ├── continuation.py     # Story continuation logic
│       ├── epub.py             # EPUB3 book generation
│       ├── illustrator.py      # Image generation CLI
│       ├── models.py           # Data models and schemas
│       ├── movie.py            # Video production CLI
│       ├── music.py            # Music generation CLI
│       ├── narration.py        # Audio narration CLI
│       ├── pdf.py              # PDF book generation (ReportLab)
│       ├── publisher.py        # End-to-end publishing pipeline CLI
│       ├── story.py            # Story processing CLI
│       └── story_formatter.py  # Story formatting and structure
├── studio/                     # Web workspace for authors
│   ├── api.py                  # FastAPI backend with WebSocket support
│   ├── web-ui/                 # React + Vite frontend
│   │   ├── src/
│   │   │   ├── components/    # React components (Monaco editor, file browser)
│   │   │   ├── pages/         # Page components
│   │   │   └── ...
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── README.md
├── docs/                       # MkDocs documentation website
│   ├── README.md              # Homepage
│   ├── fableflow-workflow.md  # Complete workflow documentation
│   ├── books/                 # Published book content
│   ├── blog/                  # Curiosity Chronicles blog
│   ├── community/             # Community guidelines
│   ├── create/                # Creator guides
│   ├── curious-cassie/        # Curious Cassie series
│   └── ...
├── tests/                     # Test suite
├── config/                    # Configuration files
│   └── default.yaml          # Default configuration
├── .env                       # Environment variables (API keys)
├── Makefile                   # Build and run commands
├── pyproject.toml            # Python package configuration
└── mkdocs.yml                # MkDocs website configuration
```

## 🔧 Technology Stack

### Backend (producer/)
- **Python 3.11+** - Primary language
- **Typer** - CLI interface and command orchestration
- **Pydantic** - Data validation and settings management
- **Loguru** - Structured logging
- **ReportLab** - PDF generation
- **Pillow (PIL)** - Image processing
- **FFmpeg/MoviePy** - Video processing

### AI/ML Integration
- **VLLM Support via OpenAI API standards** - Story enhancement, editorial review, prompts with GenAI, with Claude API or any other alternative vLLM.
- **DALL-E / Stable Diffusion** - Image generation
- **Text-to-Speech APIs** - Audio narration
- **AI Music Generation** - Background scores

### Studio (studio/)
- **Frontend**: React + Vite + Tailwind CSS
- **Editor**: Monaco Editor (VS Code editor component)
- **Backend**: FastAPI + WebSocket (real-time updates)
- **Features**: Project browser, version comparison, media gallery, live progress

### Website (docs/)
- **MkDocs** - Static site generator
- **Material for MkDocs** - Theme
- **GitHub Pages** - Hosting
- **Mermaid** - Workflow diagrams

## 🎬 Complete Production Workflow

### High-Level Journey

1. **Author** writes stories in FableFlow Studio (web interface)
2. **Review** process refines content through 5-stage AI editorial review
3. **Production** generates multimedia in parallel:
   - Narration Agent → Audio files
   - Illustration Planner/Illustrator → Images
   - Music Director/Musician → Background music
   - Book Producer → PDF/EPUB/HTML books
   - Movie Director/Animator/Producer → Final video
4. **Publishing** creates multiple formats and assembles outputs
5. **Community** reads via the website, provides feedback

See [fableflow-workflow.md](docs/fableflow-workflow.md) for detailed workflow with diagrams.

### Review Pipeline Stages

1. **Friendly Proof** - Initial feedback and readability
2. **Critical Review** - Professional editorial analysis
3. **Content Check** - Safety and appropriateness validation
4. **Story Edit** - Structure and narrative improvements
5. **Format Proof** - Final polish and formatting

Author approves at each stage; rejection loops back to revision.

## 📋 Common Development Tasks

### Setup and Installation

```bash
# Clone and install
git clone https://github.com/suneeta-mall/fable-flow.git
cd fable-flow

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
make install

# Install Studio (first time only)
make studio-install
```

### Running Components

**Option 1: Full Development Environment**
```bash
make dev-all        # Start Studio + Website + Backend API
# Studio: http://localhost:3000
# Backend API: http://localhost:8000
# Website: http://localhost:8080

make stop-all       # Stop all services
```

**Option 2: Studio Only**
```bash
make studio-start   # Start Studio only
# Access at http://localhost:3000

make studio-stop    # Stop Studio
```

**Option 3: CLI Only**
```bash
# Run end-to-end publishing pipeline
fable-flow publisher process

# Run individual production steps
fable-flow story process       # Story enhancement
fable-flow illustrator draw    # Generate illustrations
fable-flow narration produce   # Generate narration
fable-flow music produce       # Generate music
fable-flow director produce    # Generate video
```

**Option 4: Website Development**
```bash
make serve          # Serve MkDocs website locally
# Access at http://localhost:8080
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API
MODEL_API_KEY=your_openai_key

# Optional: Custom model server
MODEL_SERVER_URL=http://localhost:8000/v1
MODEL_SERVER_API_KEY=dev-api-key

# Other API keys for TTS, image generation, etc.
```

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=fable_flow --cov-report=html

# Run specific test files
python -m pytest tests/test_agents.py -v
python -m pytest tests/test_book_generation.py -v
```

### Code Quality

```bash
# Format code (black + ruff)
make fmt

# Type checking
mypy producer/fable_flow/

# Linting
ruff check producer/fable_flow/
```

## 🤖 Agent Architecture

### Agent-Based Pipeline

FableFlow uses a multi-agent architecture where specialized agents handle different production tasks:

**Story Review Agents:**
- Friendly Proofreader
- Critical Reviewer
- Content Safety Checker
- Story Editor
- Format Proofreader

**Production Agents:**
- Narrator Agent - Audio generation
- Illustration Planner - Scene planning
- Illustrator Agent - Image generation
- Book Producer - PDF/EPUB/HTML assembly
- Music Director - Music planning
- Musician Agent - Music generation
- Movie Director - Video planning
- Animator Agent - Animation/scene creation
- Movie Producer - Final video assembly

### Agent Implementation Pattern

Agents are defined in `producer/fable_flow/agents.py` using the autogen-core framework:

```python
@type_subscription(topic_type="agent_topic")
class MyAgent(RoutedAgent):
    def __init__(self, model_client, output_dir):
        super().__init__("Agent description")
        self._model_client = model_client
        self.output_dir = output_dir

    @message_handler
    async def handle_message(self, message: MessageType, ctx: MessageContext):
        # Process the message
        result = await self._model_client.create(...)

        # Publish to next agent in pipeline
        await self.publish_message(...)
```

## 📚 Book Production

### Book Formats Generated

- **📕 PDF** (ReportLab): Print-ready layout with bookmarks, page numbers, TOC
- **📗 EPUB** (EPUB3): NCX navigation, OPF manifest, e-reader optimized
- **🌐 HTML**: Web-friendly, responsive design, browser preview

### Book Structure

Generated books include:
- Front Cover (with title overlay on illustration)
- Title Page
- Publication Information
- Table of Contents
- Preface
- Story Chapters (with contextual illustrations)
- About the Author
- Index
- Back Cover

Implementation: `producer/fable_flow/pdf.py` (PDF), `producer/fable_flow/epub.py` (EPUB)

## 🎨 FableFlow Studio

Web-based workspace for authors to manage story projects.

### Features
- **Project Browser**: Dashboard of all stories
- **Monaco Editor**: Professional code editor (VS Code component)
- **Version Compare**: Side-by-side diffs of story versions
- **Media Gallery**: Preview generated images, audio, videos
- **Live Progress**: Real-time WebSocket updates during production
- **File Management**: Upload, edit, organize story files

### Architecture
- Frontend: React + Vite (TypeScript)
- Backend: FastAPI + WebSocket
- Editor: Monaco Editor component
- URL: http://localhost:3000 (development)

## 📖 Documentation Website

MkDocs-based website at https://suneeta-mall.github.io/fable-flow

### Key Sections
- **Story Library**: Browse all published stories
- **Curious Cassie Series**: Featured educational children's books
- **Creator's Corner**: Guides, tutorials, CLI reference
- **Community Hub**: Guidelines, collaboration
- **Curiosity Chronicles**: Blog with author spotlights, behind-the-scenes

## 🔧 Configuration System

Configuration uses Pydantic models in `producer/fable_flow/config.py`:

- Type-safe configuration with validation
- Default config in `config/default.yaml`
- Environment variables loaded from `.env`
- Override via CLI flags or config files

## ⚠️ Troubleshooting

### Import Errors
- Always activate virtual environment: `source .venv/bin/activate`
- Install in editable mode: `pip install -e .`
- Check Python path: `which python`

### Studio Issues
- Ensure Node.js 18+ is installed
- Run `make studio-install` first time
- Check ports 3000, 8000 are available

### Build Issues
- Run `make install` to reinstall dependencies
- Clear cache: `rm -rf .mypy_cache .pytest_cache .ruff_cache`
- Rebuild: `make clean && make install`

## 📝 Code Review Checklist

When reviewing or modifying code:

1. **Type Safety**: Use type hints consistently
2. **Error Handling**: Handle exceptions where logical; let app fail on critical errors (error is better than silent failure)
3. **Logging**: Use `loguru` for consistent logging
4. **Testing**: Add/update tests for new functionality
5. **Documentation**: Update docstrings. Only add comments where code is complex or non-obvious. NO obvious comments.
6. **Configuration**: Use config system instead of hardcoded values
7. **Async Patterns**: Use async/await correctly for I/O operations
8. **Resource Management**: Proper cleanup of files, connections, temp resources

## 🎯 Architecture Principles

- **Agentic AI System**: Multi-agent architecture with message passing
- **Async First**: Heavy use of asyncio for concurrent operations
- **Type Safe**: Pydantic models for data validation
- **Configurable**: Extensive configuration system with validation
- **Modular**: Clear separation of concerns (producer/studio/docs)
- **CLI + Web**: Both command-line and web interfaces
- **Open Source**: Community-driven development

## 🚀 Quick Reference

```bash
# Development workflow
source .venv/bin/activate           # Always first!
make dev-all                         # Start everything
make stop-all                        # Stop everything

# Individual components
make studio-start                    # Studio only
make serve                           # Docs website only
fable-flow publisher process         # CLI pipeline

# Code quality
make fmt                             # Format code
python -m pytest tests/ -v           # Run tests

# Documentation
mkdocs build                         # Build docs site
mkdocs serve                         # Serve docs locally
```

---

**Remember**: Always start with `source .venv/bin/activate` before any development work!

**Project Focus**: Creating high-quality, educational children's stories with AI-powered multimedia to nurture curiosity and STEM learning in the next generation.
