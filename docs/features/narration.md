# AI Narration

Fable Flow's narration feature transforms your story into engaging, professional-quality audio narration. Using advanced text-to-speech technology, it creates natural-sounding voiceovers that bring your story to life.

## Overview

The narration pipeline converts your story into audio through:

* Voice selection and customization
* Emotional tone matching
* Pacing and emphasis control
* Background music integration
* Sound effect placement

## Key Features

### Voice Generation

The system provides:

* Multiple voice options
* Age-appropriate tones
* Emotional expression
* Character voice differentiation
* Educational clarity

### Audio Enhancement

Enhances narration with:

* Natural pauses and pacing
* Emotional emphasis
* Character voice distinction
* Educational tone adjustment
* Background music integration

### Multiple Output Formats

Supports various audio formats:

* WAV for high quality
* MP3 for compatibility
* M4A for mobile devices
* OGG for web use
* AAC for streaming

## Agent Architecture

FableFlow uses a dedicated **Narrator Agent** that:

- Converts manuscript text to natural-sounding speech
- Applies appropriate emotional tone and pacing
- Generates high-quality audio files for storytelling
- Integrates with video and book production

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Listen to generated narration in the Media Gallery

### Option 2: CLI - Individual Narration

```bash
# Generate narration (requires processed story)
fable-flow narration produce
```

### Option 3: CLI - Full Publishing Pipeline

```bash
# Run complete pipeline including narration
fable-flow publisher process
```

### Configuration

Narration settings in `config.yaml`:

```yaml
model:
  text_to_speech:
    model: "tts_models/en/ljspeech/tacotron2-DDC"
    device: "cuda"

style:
  narration:
    voice_presets:
      friendly: "warm and engaging"
      professional: "clear and authoritative"
      dramatic: "expressive and theatrical"
      calm: "soothing and gentle"
```

## Output

The narration pipeline generates:

* `audio/` directory containing:
    * Main narration files
    * Character voice files
    * Background music
    * Sound effects
* `metadata.json` with audio details
* `voice_guide.json` for consistency

## Integration

Narration works seamlessly with:

* **Story Processing** - Uses enhanced text
* **Video Production** - Provides audio tracks
* **PDF Publishing** - Links audio files
* **Web Publishing** - Optimizes for streaming

## Best Practices

1. **Voice Selection**
    * Match target audience
    * Consider story tone
    * Ensure clarity
    * Maintain consistency

2. **Audio Quality**
    * Check pronunciation
    * Verify pacing
    * Test emotional tone
    * Review background music

3. **File Management**
    * Organize by chapter
    * Track versions
    * Backup original files
    * Document settings

## Troubleshooting

### Common Issues

**Issue**: Unnatural speech patterns
**Solution**: Adjust pacing and emphasis settings

**Issue**: Background music too loud
**Solution**: Fine-tune audio mixing parameters

**Issue**: Voice inconsistency
**Solution**: Use voice presets and check settings

### Getting Help

- Check the [full documentation](../README.md)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) 