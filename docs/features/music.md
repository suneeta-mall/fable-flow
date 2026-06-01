# Music Generation

FableFlow generates original soundtracks that match your story's mood, pace, and themes.

## Overview

The pipeline analyzes mood, identifies themes, selects instruments, composes the music, and mixes the audio.

## Key Features

### Music Generation

Produces original, mood-appropriate compositions, including character motifs and scene-specific tracks.

### Audio Enhancement

Handles mixing, volume balancing, transitions, and integration with narration.

### Multiple Output Formats

Outputs WAV, MP3, M4A, OGG, and AAC for high-quality, mobile, web, and streaming use.

## Agent Architecture

Two agents work together:

- **Music Director Agent** - Analyzes story mood, plans musical themes, determines instrumentation
- **Musician Agent** - Generates original compositions using AI music models

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Listen to generated music in the Media Gallery

### Option 2: CLI

```bash
# Run the full generation pipeline (music generation runs as a stage within it)
fable-flow generate examples/cassie_beach_adventure_input.json
```

Music generation runs as a stage within `fable-flow generate`. Use `--resume` to re-run only missing pieces. The stage can also be re-run from FableFlow Studio.

### Configuration

Music settings in `config.yaml`:

```yaml
model:
  music_generation:
    model: "facebook/musicgen-small"

style:
  music:
    happy: "upbeat orchestral with playful melodies"
    sad: "gentle piano with soft strings"
    adventure: "epic orchestral with percussion"
    mystery: "mysterious strings with woodwinds"
```

## Output

* `music/` directory containing:
    * Main soundtrack
    * Scene-specific tracks
    * Character themes
    * Sound effects
* `metadata.json` with music details
* `mood_guide.json` for consistency

## Integration

Music feeds into:

* **Story Processing** - Uses mood analysis
* **Video Production** - Provides soundtrack
* **Narration** - Balances with voice
* **Illustration** - Enhances visual impact

## Best Practices

1. **Mood Selection** - match the story tone and audience, and keep moods consistent.
2. **Audio Quality** - check mixing, balance, and transitions.
3. **Asset Management** - organize by scene, track versions, and back up originals.

## Troubleshooting

### Common Issues

**Issue**: Music too loud/quiet
**Solution**: Adjust mixing parameters and volume levels

**Issue**: Mood mismatch
**Solution**: Review mood settings and story analysis

**Issue**: Integration problems
**Solution**: Check synchronization and timing settings

### Getting Help

See the [full documentation](../README.md), [GitHub issues](https://github.com/suneeta-mall/fable-flow/issues), and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
