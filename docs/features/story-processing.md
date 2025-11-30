# Story Processing

Fable Flow's story processing feature transforms your text into an enhanced, multimedia-ready narrative. This powerful system analyzes, structures, and optimizes your story for various output formats while maintaining its core message and educational value.

## Overview

The story processing pipeline takes your input text and enhances it through several stages:

1. **Story Analysis** - Evaluates narrative structure, character development, and educational content
2. **Content Enhancement** - Optimizes language, pacing, and engagement
3. **Scene Breakdown** - Prepares the story for illustration and multimedia production
4. **Format Preparation** - Structures the content for various output formats (PDF, video, etc.)

## Key Features

### Intelligent Story Analysis

The system analyzes your story for:

* Narrative structure and flow
* Character development and consistency
* Educational value and learning objectives
* Engagement level and age-appropriateness
* Scientific accuracy (when applicable)

### Content Enhancement

Automatically improves your story by:

* Optimizing language and vocabulary for target audience
* Enhancing pacing and narrative flow
* Adding educational elements and discussion points
* Ensuring consistent tone and style
* Maintaining scientific accuracy

### Scene Preparation

Prepares your story for multimedia production by:

* Breaking down scenes for illustration
* Identifying key moments for visual emphasis
* Creating image prompts for illustration generation
* Structuring content for video production
* Planning music and sound effect placement

## Usage

### Basic Processing

```bash
fable-flow story process --input path/to/your/story.txt --output output/
```

### Advanced Options

```bash
fable-flow story process \
  --input path/to/your/story.txt \
  --output output/ \
  --model claude-opus-4-20250514 \
  --temperature 0.0 \
  --seed 42
```

### Configuration

Story processing can be customized through the `config.yaml` file:

```yaml
model:
  text_generation:
    story: "claude-opus-4-20250514"
    content_moderation: "claude-opus-4-20250514"
    proofreading: "claude-opus-4-20250514"
  content_safety:
    safety_model: "claude-opus-4-20250514"
    scientific_accuracy: "claude-opus-4-20250514"
```

## Output

The story processing pipeline generates several output files:

- `enhanced_story.txt` - The optimized story text
- `scenes.json` - Scene breakdown for illustration
- `analysis.json` - Story analysis and suggestions
- `metadata.json` - Processing metadata and settings

## Integration

The processed story can be used with other Fable Flow features:

- **Illustration Generation** - Uses scene breakdown for image creation
- **Video Production** - Structures content for video generation
- **PDF Publishing** - Formats content for book creation
- **Audio Narration** - Prepares text for voice synthesis

## Best Practices

1. **Input Quality**
    - Provide clear, well-structured input text
    - Include any specific educational objectives
    - Specify target age group if relevant

2. **Processing Options**
    - Use appropriate model for your content type
    - Adjust temperature for creativity vs. consistency
    - Set seed for reproducible results

3. **Output Management**
    - Review enhanced content before proceeding
    - Use scene breakdown for illustration planning
    - Consider analysis suggestions for improvements

## Troubleshooting

### Common Issues

**Issue**: Story structure not maintained
**Solution**: Check input formatting and use appropriate model settings

**Issue**: Educational content not enhanced
**Solution**: Ensure educational objectives are clear in input

**Issue**: Scene breakdown incomplete
**Solution**: Verify story has clear scene transitions

### Getting Help

- Check the [full documentation](../README.md)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) 