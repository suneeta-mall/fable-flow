# Illustration Generation

Fable Flow's illustration generation feature creates beautiful, contextually relevant artwork for your stories. Using advanced AI models, it generates illustrations that match your story's style, tone, and educational objectives.

## Overview

The illustration pipeline processes your story to create:

* Scene-specific illustrations
* Character designs
* Educational diagrams
* Cover artwork
* Supporting visuals

## Key Features

### Intelligent Scene Analysis

The system analyzes your story to:

* Identify key visual moments
* Extract character descriptions
* Recognize educational concepts
* Determine appropriate visual style
* Plan illustration placement

### Style Consistency

Maintains visual coherence through:

* Consistent character designs
* Unified color palette
* Matching art style
* Age-appropriate visuals
* Educational clarity

### Multiple Illustration Types

Generates various illustration styles:

* Children's book illustrations
* Educational diagrams
* Character portraits
* Scene compositions
* Cover artwork

## Usage

### Option 1: FableFlow Studio (Recommended)

Use the web-based Studio interface:

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline which includes illustration generation
4. Preview generated illustrations in the Media Gallery
5. Monitor real-time progress

### Option 2: CLI - Individual Illustration Generation

```bash
# Generate illustrations (requires processed story)
fable-flow illustrator draw
```

### Option 3: CLI - Full Publishing Pipeline

```bash
# Run complete pipeline including illustrations
fable-flow publisher process
```

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

FableFlow uses a two-agent illustration system:

- **Illustration Planner Agent** - Analyzes story scenes, identifies key visual moments, creates detailed image prompts
- **Illustrator Agent** - Generates images using AI models (DALL-E, Stable Diffusion), ensures consistency

These agents work together to create cohesive visual narratives that match your story's tone and educational objectives.

## Output

The illustration pipeline generates:

* `illustrations/` directory containing:
    * Scene illustrations
    * Character designs
    * Educational diagrams
    * Cover artwork
* `metadata.json` with illustration details
* `style_guide.json` for consistency

## Integration

Illustrations work seamlessly with:

* **Story Processing** - Uses scene breakdown
* **Video Production** - Provides visual assets
* **PDF Publishing** - Formats for print
* **Web Publishing** - Optimizes for web

## Best Practices

1. **Style Selection**
    * Choose age-appropriate styles
    * Consider educational objectives
    * Maintain consistency
    * Match story tone

2. **Quality Control**
    * Review generated illustrations
    * Check educational accuracy
    * Verify style consistency
    * Ensure age-appropriateness

3. **Asset Management**
    * Organize by scene/chapter
    * Maintain style guides
    * Track revisions
    * Backup original files

## Troubleshooting

### Common Issues

**Issue**: Inconsistent character designs
**Solution**: Use style consistency settings and character reference sheets

**Issue**: Educational diagrams unclear
**Solution**: Provide detailed prompts and check accuracy

**Issue**: Style mismatch
**Solution**: Adjust style parameters and use style presets

### Getting Help

- Check the [full documentation](../README.md)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) 