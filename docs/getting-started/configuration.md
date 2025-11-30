# Configuration Guide

This guide explains how to customize Fable Flow's behavior using the `config.yaml` file. All settings are optional and will use sensible defaults if not specified.

## Basic Structure

The configuration file uses YAML format. Here's the basic structure:

```yaml
# Model Configuration
model:
  server:
    url: "https://api.anthropic.com/v1"
    api_key: "${env.ANTHROPIC_API_KEY}"
  default: "claude-opus-4-20250514"
  text_generation:
    story: "${model.default}"
    content_moderation: "${model.default}"
    proofreading: "${model.default}"
  image_generation:
    model: "stabilityai/stable-diffusion-xl-base-1.0"
    style_consistency: "stabilityai/stable-diffusion-xl-refiner-1.0"
  text_to_speech:
    model: "tts_models/en/ljspeech/tacotron2-DDC"
    device: "cuda"
  music_generation:
    model: "facebook/musicgen-small"
  video_generation:
    model: "THUDM/CogVideoX1.5-5B-I2V"
    num_frames: 81
    num_inference_steps: 50
    guidance_scale: 6
    fps: 8
  content_safety:
    safety_model: "${model.default}"
    scientific_accuracy: "${model.default}"

# API Configuration
api:
  keys:
    openai: "${env.OPENAI_API_KEY}"

# Path Configuration
paths:
  base: "/path/to/your/project"
  output: "${paths.base}/.tmp/result_claude"

# Style Configuration
style:
  illustration:
    style_preset: "children's book illustration"
    color_scheme: "bright and cheerful"
    art_style: "watercolor and digital art blend"
  music:
    happy: "upbeat orchestral with playful melodies"
    sad: "gentle piano with soft strings"
    adventure: "epic orchestral with percussion"
    mystery: "mysterious strings with woodwinds"
  video:
    animation_style: "3D animation with 2D elements"
    color_palette: "vibrant and child-friendly"
    camera_style: "dynamic and engaging"
  pdf:
    page_size: [792.0, 612.0]
    margin_top: 36.0
    margin_bottom: 36.0
    margin_left: 54.0
    margin_right: 54.0
    title_font: "Helvetica-Bold"
    heading_font: "Helvetica-Bold"
    body_font: "Helvetica"
    caption_font: "Helvetica-Oblique"
    story_font: "Helvetica"
    title_font_size: 36
    chapter_font_size: 24
    body_font_size: 18
    caption_font_size: 14
    quote_font_size: 16
    title_color: "#000000"
    chapter_color: "#000000"
    body_color: "#000000"
    caption_color: "#666666"
    quote_color: "#000000"
    accent_color: "#000000"
    title_space_after: 36.0
    chapter_space_before: 36.0
    chapter_space_after: 24.0
    paragraph_space_after: 14.4
    line_height_multiplier: 1.5
    body_left_indent: 0.0
    body_right_indent: 0.0
    first_line_indent: 0.0
    dialogue_left_indent: 0.0
    image_width: 648.0
    image_height: 432.0
    image_space_before: 18.0
    image_space_after: 18.0
    full_page_image_width: 684.0
    full_page_image_height: 540.0
    use_drop_caps: false
    justify_text: false
    page_number_position: "bottom_center"
    page_number_font_size: 12
```

## Model Configuration

### Server Settings
Configure the model server and API key:
```yaml
model:
  server:
    url: "https://api.anthropic.com/v1"
    api_key: "${env.ANTHROPIC_API_KEY}"
```

### Text Generation
Configure text generation models:
```yaml
model:
  text_generation:
    story: "${model.default}"
    content_moderation: "${model.default}"
    proofreading: "${model.default}"
```

### Image Generation
Configure image generation models:
```yaml
model:
  image_generation:
    model: "stabilityai/stable-diffusion-xl-base-1.0"
    style_consistency: "stabilityai/stable-diffusion-xl-refiner-1.0"
```

### Text to Speech
Configure text-to-speech settings:
```yaml
model:
  text_to_speech:
    model: "tts_models/en/ljspeech/tacotron2-DDC"
    device: "cuda"
```

### Video Generation
Configure video generation settings:
```yaml
model:
  video_generation:
    model: "THUDM/CogVideoX1.5-5B-I2V"
    num_frames: 81
    num_inference_steps: 50
    guidance_scale: 6
    fps: 8
```

## API Configuration

Configure API keys for various services:
```yaml
api:
  keys:
    openai: "${env.OPENAI_API_KEY}"
```

## Path Configuration

Configure file system paths:
```yaml
paths:
  base: "/path/to/your/project"
  output: "${paths.base}/.tmp/result_claude"
```

## Style Configuration

### Illustration Style
Configure illustration settings:
```yaml
style:
  illustration:
    style_preset: "children's book illustration"
    color_scheme: "bright and cheerful"
    art_style: "watercolor and digital art blend"
```

### Music Style
Configure music style settings:
```yaml
style:
  music:
    happy: "upbeat orchestral with playful melodies"
    sad: "gentle piano with soft strings"
    adventure: "epic orchestral with percussion"
    mystery: "mysterious strings with woodwinds"
```

### Video Style
Configure video style settings:
```yaml
style:
  video:
    animation_style: "3D animation with 2D elements"
    color_palette: "vibrant and child-friendly"
    camera_style: "dynamic and engaging"
```

### PDF Style
Configure PDF styling for children's books:
```yaml
style:
  pdf:
    page_size: [792.0, 612.0]  # 11x8.5 inches in points
    margin_top: 36.0  # 0.5 inch in points
    margin_bottom: 36.0
    margin_left: 54.0  # 0.75 inch
    margin_right: 54.0
    title_font: "Helvetica-Bold"
    heading_font: "Helvetica-Bold"
    body_font: "Helvetica"
    caption_font: "Helvetica-Oblique"
    story_font: "Helvetica"
    title_font_size: 36
    chapter_font_size: 24
    body_font_size: 18
    caption_font_size: 14
    quote_font_size: 16
    title_color: "#000000"
    chapter_color: "#000000"
    body_color: "#000000"
    caption_color: "#666666"
    quote_color: "#000000"
    accent_color: "#000000"
    title_space_after: 36.0
    chapter_space_before: 36.0
    chapter_space_after: 24.0
    paragraph_space_after: 14.4
    line_height_multiplier: 1.5
    body_left_indent: 0.0
    body_right_indent: 0.0
    first_line_indent: 0.0
    dialogue_left_indent: 0.0
    image_width: 648.0
    image_height: 432.0
    image_space_before: 18.0
    image_space_after: 18.0
    full_page_image_width: 684.0
    full_page_image_height: 540.0
    use_drop_caps: false
    justify_text: false
    page_number_position: "bottom_center"
    page_number_font_size: 12
```

## Environment Variables

The configuration system supports environment variables. You can override configuration values using environment variables with the following format:

```bash
MODEL__DEFAULT=claude-opus-4-20250514
MODEL__SERVER__URL=https://api.anthropic.com/v1
API__KEYS__OPENAI=your-api-key
```

> Note: Environment variables take precedence over settings in `config.yaml`.

## Best Practices

1. **Start with Defaults**: Begin with default settings and adjust as needed
2. **Use Environment Variables**: For sensitive data like API keys
3. **Monitor Resource Usage**: Adjust model parameters based on your system
4. **Version Control**: Include your `config.yaml` in version control, but exclude `.env`

## Troubleshooting

### Common Issues

**Issue**: Configuration changes not taking effect
**Solution**: Ensure the file is properly formatted YAML and restart Fable Flow

**Issue**: API key errors
**Solution**: Check your API keys in both `.env` and `config.yaml`

**Issue**: Model loading errors
**Solution**: Verify model names and server URLs in the configuration

## Next Steps

- **[Quick Start Tutorial](quick-start.md)** - Try out your configuration
- **[Feature Overview](../features/story-processing.md)** - Learn about available features
- **[Examples](../examples/basic-workflow.md)** - See configuration in action 