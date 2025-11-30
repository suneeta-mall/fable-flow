# Claude Instructions for Fable Flow

**Fable Flow** is an open-source agentic AI platform that transforms story manuscripts into complete multimedia experiences through AI-powered narration, illustrations, video production, and music composition.

## 🎯 Project Overview

Fable Flow is a **story creation agentic application** that automates the entire publishing pipeline from draft manuscripts to production-ready multimedia content. The system uses multiple AI agents working together to enhance stories and create engaging multimedia experiences.

### Core Capabilities
- **📚 Story Enhancement**: AI-powered manuscript refinement and optimization
- **🎙️ AI Narration**: Convert text to professional-quality audio narration  
- **🎨 Illustration Generation**: Create stunning visuals using AI image generation
- **🎬 Video Production**: Combine narration, illustrations, and music into engaging videos
- **🎵 Music Composition**: Generate background scores that complement narratives
- **📖 Content Generation**: Create supporting content and marketing materials

## 🏗️ Architecture & Technology Stack

### Core Technologies
- **Python 3.11+** - Primary language
- **Typer** - CLI interface and command orchestration
- **OpenAI** - Language model integration
- **Transformers/PyTorch** - Deep learning models
- **Loguru** - Structured logging
- **Pydantic** - Data validation and settings management

### AI/ML Stack
- **TTS (Text-to-Speech)** - Audio narration generation
- **Diffusers** - Image generation and AI art
- **Diffusers** - Advanced image generation
- **MoviePy** - Video processing and production
- **Librosa/Pydub** - Audio processing
- **OpenCV** - Computer vision tasks

### Project Structure
```
src/fable_flow/
├── __init__.py          # Package initialization
├── app.py              # Main CLI application entry point
├── agents.py           # AI agent orchestration and management
├── client.py           # External API clients and integrations
├── common.py           # Shared utilities and helper functions
├── config.py           # Configuration management
├── continuation.py     # Story continuation and enhancement logic
├── illustrator.py      # Image generation and illustration services
├── models.py           # Data models and schema definitions
├── movie.py            # Video production and director services
├── music.py            # Music generation and composition
├── narration.py        # Audio narration and TTS services
├── pdf.py              # PDF generation and document processing
├── publisher.py        # End-to-end publishing pipeline
└── story.py            # Core story processing and enhancement
│   ├── agents.py           # AI agents implementation
│   ├── config.py           # Configuration management
│   ├── models.py           # AI model wrappers
│   ├── common.py           # Shared utilities
│   ├── story.py            # Story processing
│   ├── illustrator.py      # Image generation
│   ├── music.py            # Music generation
│   ├── movie.py            # Video generation
│   ├── blog.py             # Blog generation
│   ├── publisher.py        # Publishing pipeline
│   └── pdf.py              # PDF generation
├── tests/                  # Test suite
├── config/                 # Configuration files
├── docs/                   # Documentation
├── examples/               # Example files
└── data/                   # Sample data
```

## Key Components

### 1. Configuration System
- Uses `omegaconf` and `pydantic` for type-safe configuration
- Main config in `src/fable_flow/config.py`
- Default config in `config/default.yaml`
- Environment variables loaded from `.env`

### 2. Agent System
- Built on `autogen-core` framework
- Each agent has specific responsibilities (story editing, illustration, etc.)
- Agents communicate via message passing
- Main agents defined in `src/fable_flow/agents.py`

### 3. CLI Interface
- Built with `typer`
- Entry point: `src/fable_flow/app.py`
- Subcommands: story, illustrator, music, movie, blog, publisher

## Common Development Tasks

### Adding a New Agent
1. Define agent class in `agents.py`
2. Add configuration in `config.py`
3. Add CLI command if needed
4. Write tests in `tests/`

### Running the Application
```bash
# Activate environment first
source .venv/bin/activate

# Run specific commands
fable-flow story process --help
fable-flow illustrator draw --help
fable-flow publisher process --help
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=fable_flow --cov-report=html

# Run specific test categories
python -m pytest tests/test_config.py -v
python -m pytest tests/test_agents.py -v
```

### Code Quality
```bash
# Format code (black + ruff)
make fmt

# Type checking
mypy src/fable_flow/

# Linting
ruff check src/fable_flow/
```

## Environment Variables

Create a `.env` file in the project root:
```bash
MODEL_API_KEY=your_openai_key
# Model server configuration
MODEL_SERVER_URL=http://localhost:8000/v1
MODEL_SERVER_API_KEY=dev-api-key

# Other API keys as needed
```

## Troubleshooting

### Import Errors
- Always activate virtual environment first: `source .venv/bin/activate`
- Install in editable mode: `pip install -e .`
- Check Python path: `which python`

### Test Failures
- Ensure virtual environment is activated
- Install dev dependencies: `pip install -e ".[dev]"`
- Check test configuration in `pyproject.toml`

### Configuration Issues
- Check `config/default.yaml` for default values
- Verify `.env` file exists and has correct keys
- Review `src/fable_flow/config.py` for configuration schema

## Code Review Checklist

When reviewing or modifying code:

1. **Type Safety**: Ensure type hints are used
2. **Error Handling**: Handle exceptions and fallbacks only where logically makes sense. Otherwise let the application fail upon error. Error is better than silent failures.
3. **Logging**: Use `loguru` for consistent logging
4. **Testing**: Add/update tests for new functionality
5. **Documentation**: Update docstrings and comments. Only add comments where code is not self-explainatory or complex. DO NOT add obvious comments. 
6. **Configuration**: Use config system instead of hardcoded values
7. **Async Patterns**: Use async/await correctly for I/O operations
8. **Resource Management**: Proper cleanup of files, connections, etc.

## Architecture Notes

- **Agentic AI System**: Uses multi-agent architecture with message passing
- **Async First**: Heavy use of asyncio for concurrent operations
- **Type Safe**: Pydantic models for data validation
- **Configurable**: Extensive configuration system with validation
- **Modular**: Clear separation of concerns between components
- **CLI Focused**: Primary interface is command-line tools

## Common Patterns

### Agent Implementation
```python
@type_subscription(topic_type="agent_type")
class MyAgent(RoutedAgent):
    def __init__(self, model_client, output_dir):
        super().__init__("Agent description")
        self._model_client = model_client
        self.output_dir = output_dir
    
    @message_handler
    async def handle_message(self, message: Manuscript, ctx: MessageContext):
        # Process message
        result = await self._model_client.create(...)
        # Publish to next agent
        await self.publish_message(...)
```

### Model Usage
```python
# Text generation
model = EnhancedTextModel(model_name)
result = await model.generate(prompt, system_message)

# Image generation
image_model = EnhancedImageModel()
image_data = await image_model.generate_image(prompt, style)
```

---

**Remember**: Always start with `source .venv/bin/activate` before any development work!