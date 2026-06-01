# Quick Start Tutorial

Create your first AI-powered children's book and movie. By the end you'll have a complete book (PDF/EPUB) with illustrations, plus an optional movie adaptation with narration and music.

## Prerequisites

- Fable Flow installed ([Installation Guide](installation.md))
- Your virtual environment activated
- An input spec (a `FableFlowInput` JSON file) ready

## Tutorial Overview

Steps to build a multimedia story:

1. **Prepare Your Input Spec** - Start from an example JSON spec
2. **Validate the Spec** - Check it before generating
3. **Generate the Book and Movie** - Run the pipeline
4. **View Your Creation** - Open the generated artifacts

## Step 1: Prepare Your Input Spec

FableFlow takes a JSON **input spec** (a `FableFlowInput`), not a plain story file. The repository ships ready-to-use examples in `examples/`:

- `examples/cassie_beach_adventure_input.json`
- `examples/cassie_fei_fei_li_input.json`
- `examples/cassie_stephen_hawking_input.json`

Copy one as a starting point and edit the project metadata, characters, and story seed:

```bash
mkdir -p stories
cp examples/cassie_beach_adventure_input.json stories/my_first_story_input.json
```

The spec defines the project metadata, characters, settings, and a story seed describing the theme and plot. The generation pipeline drafts, edits, and proofs the story, structures it into chapters, places illustrations, and then optionally adapts it into a movie.

## Step 2: Validate the Spec

Check that your input spec is well-formed before generating:

```bash
# Validate the input spec
fable-flow validate stories/my_first_story_input.json
```

This verifies the JSON parses into a valid `FableFlowInput` and reports any validation errors.

## Step 3: Generate the Book and Movie

Run the full pipeline (book generation followed by movie adaptation):

```bash
# Generate from the input spec
fable-flow generate stories/my_first_story_input.json --output output/
```

The pipeline runs all stages: drafting and editing the story, structuring chapters, placing and generating illustrations, then producing narration, music, and video for the movie. There are no separate per-stage commands; everything runs as stages of `generate`.

Useful flags:

- `--output/-o DIR` - choose the output directory
- `--model/-m NAME` - select the LLM used for text generation
- `--book-only` - generate just the book (skip the movie adaptation)
- `--skip-book-publish` - skip rendering the PDF/EPUB
- `--resume` - resume a previously interrupted run

To generate only the book:

```bash
fable-flow generate stories/my_first_story_input.json --output output/ --book-only
```

You can also drive the same pipeline through the Makefile:

```bash
make run INPUT=stories/my_first_story_input.json OUTPUT=output/
```

## View Your Creation

The book artifacts (PDF/EPUB) and the movie (MP4) are written under your output directory:

```bash
# Open the generated PDF (Linux)
xdg-open output/*.pdf

# macOS
open output/*.pdf

# Windows
start output\*.pdf
```

## Next Steps

### Generate from the Other Examples
```bash
fable-flow generate examples/cassie_fei_fei_li_input.json --output output/fei_fei/
fable-flow generate examples/cassie_stephen_hawking_input.json --output output/hawking/
```

### Try a Different LLM
```bash
# Select the language model used for text generation
fable-flow generate stories/my_first_story_input.json --model qwen2.5
```

### Book-Only Runs
```bash
# Generate the book without the movie adaptation
fable-flow generate stories/my_first_story_input.json --book-only
```

### Explore Advanced Features

- **[Custom Models](../examples/custom-models.md)** - Use your own AI models
- **[Configuration](configuration.md)** - Customize Fable Flow settings
- **[API Reference](../api/core.md)** - Integrate with your own applications
- **[Contributing](../contributing/guidelines.md)** - Contribute to the open source project

## Troubleshooting

### Common Issues

**Issue**: "No API key found"
**Solution**: Set up your model configuration in the `.env` file (`MODEL_SERVER_URL`, `MODEL_API_KEY`, `DEFAULT_MODEL`) or use local models

**Issue**: Illustrations look inconsistent
**Solution**: Adjust the image model settings in `config/default.yaml`

**Issue**: Audio quality is poor
**Solution**: Check your TTS settings in `config/default.yaml`

**Issue**: Video generation fails
**Solution**: Ensure you have enough disk space and all dependencies installed

### Getting Help

- 📖 Check the [full documentation](../README.md)
- 🐛 Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- 💬 Join discussions in the [community forum](https://github.com/suneeta-mall/fable-flow/discussions)
