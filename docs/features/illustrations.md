# Illustration Generation

FableFlow generates illustrations that match your story's style, tone, and educational objectives.

## Overview

The pipeline produces scene illustrations, character designs, educational diagrams, cover artwork, and supporting visuals.

## Key Features

### Intelligent Scene Analysis

Identifies key visual moments, extracts character descriptions and educational concepts, picks a visual style, and plans where illustrations go.

### Style Consistency

Holds visual coherence across the book: consistent character designs, a unified color palette, and a single age-appropriate art style.

### Multiple Illustration Types

Covers children's book illustrations, educational diagrams, character portraits, scene compositions, and cover artwork.

## Usage

### Option 1: FableFlow Studio (Recommended)

Use the web-based Studio interface:

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline which includes illustration generation
4. Preview generated illustrations in the Media Gallery
5. Monitor real-time progress

### Option 2: CLI

```bash
# Run the full generation pipeline (illustration generation runs as a stage within it)
fable-flow generate examples/cassie_beach_adventure_input.json
```

Illustration generation runs as a stage within `fable-flow generate`. Use `--resume` to re-run only missing pieces. The stage can also be re-run from FableFlow Studio.

### Configuration

Illustration settings in `config/default.yaml`:

```yaml
model:
  image_generation:
    model: "dall-e-3"  # Or "stabilityai/stable-diffusion-xl"
    size: "1024x1024"
    quality: "hd"

style:
  illustration:
    style_preset: "children's book illustration"
    color_scheme: "vibrant and child-friendly"
    art_style: "digital illustration with warm, engaging characters"

# Environment variables (.env)
MODEL_API_KEY=your_api_key
```

## Agent Architecture

Two agents work together:

- **Illustration Planner Agent** - Analyzes story scenes, identifies key visual moments, creates detailed image prompts
- **Illustrator Agent** - Generates images using AI models (DALL-E, Stable Diffusion), ensures consistency

## Output

* `illustrations/` directory containing:
    * Scene illustrations
    * Character designs
    * Educational diagrams
    * Cover artwork
* `metadata.json` with illustration details
* `style_guide.json` for consistency

## Integration

Illustrations feed into:

* **Story Processing** - Uses scene breakdown
* **Video Production** - Provides visual assets
* **PDF Publishing** - Formats for print
* **Web Publishing** - Optimizes for web

## Best Practices

1. **Style Selection** - choose age-appropriate styles that match the story tone and educational goals.
2. **Quality Control** - review generated illustrations for accuracy, style consistency, and age-appropriateness.
3. **Asset Management** - organize by scene/chapter, keep style guides, and back up originals.

## Troubleshooting

### Common Issues

**Issue**: Inconsistent character designs
**Solution**: Use style consistency settings and character reference sheets

**Issue**: Educational diagrams unclear
**Solution**: Provide detailed prompts and check accuracy

**Issue**: Style mismatch
**Solution**: Adjust style parameters and use style presets

### Getting Help

See the [full documentation](../README.md), [GitHub issues](https://github.com/suneeta-mall/fable-flow/issues), and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
