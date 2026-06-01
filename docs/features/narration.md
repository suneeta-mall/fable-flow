# AI Narration

FableFlow converts your story into audio narration using text-to-speech.

## Overview

The pipeline handles voice selection, emotional tone matching, pacing and emphasis, and integration with background music and sound effects.

## Key Features

### Voice Generation

Offers multiple voices with age-appropriate tones, emotional expression, and per-character differentiation.

### Audio Enhancement

Applies natural pauses, emphasis, and tone adjustments, then balances narration against background music.

### Multiple Output Formats

Outputs WAV, MP3, M4A, OGG, and AAC for high-quality, mobile, web, and streaming use.

## Agent Architecture

A dedicated **Narrator Agent** converts manuscript text to speech, applies tone and pacing, produces audio files, and integrates with video and book production.

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Listen to generated narration in the Media Gallery

### Option 2: CLI

```bash
# Run the full generation pipeline (narration runs as a stage within it)
fable-flow generate examples/cassie_beach_adventure_input.json
```

Narration runs as a stage within `fable-flow generate`. Use `--resume` to re-run only missing pieces. The stage can also be re-run from FableFlow Studio.

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

* `audio/` directory containing:
    * Main narration files
    * Character voice files
    * Background music
    * Sound effects
* `metadata.json` with audio details
* `voice_guide.json` for consistency

## Integration

Narration feeds into:

* **Story Processing** - Uses enhanced text
* **Video Production** - Provides audio tracks
* **PDF Publishing** - Links audio files
* **Web Publishing** - Optimizes for streaming

## Best Practices

1. **Voice Selection** - match the audience and story tone, and keep voices consistent.
2. **Audio Quality** - check pronunciation, pacing, tone, and music balance.
3. **File Management** - organize by chapter, track versions, and back up originals.

## Troubleshooting

### Common Issues

**Issue**: Unnatural speech patterns
**Solution**: Adjust pacing and emphasis settings

**Issue**: Background music too loud
**Solution**: Fine-tune audio mixing parameters

**Issue**: Voice inconsistency
**Solution**: Use voice presets and check settings

### Getting Help

See the [full documentation](../README.md), [GitHub issues](https://github.com/suneeta-mall/fable-flow/issues), and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
