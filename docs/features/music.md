# Music Generation

Fable Flow's music generation feature creates custom soundtracks that enhance your story's emotional impact and educational value. Using advanced AI models, it generates original music that matches your story's mood, pace, and themes.

## Overview

The music generation pipeline creates soundtracks through:

* Mood analysis
* Theme identification
* Instrument selection
* Composition generation
* Audio mixing

## Key Features

### Music Generation

The system provides:

* Original compositions
* Mood-appropriate music
* Educational themes
* Character motifs
* Scene-specific tracks

### Audio Enhancement

Enhances music with:

* Professional mixing
* Volume balancing
* Sound effects
* Transitions
* Narration integration

### Multiple Output Formats

Supports various audio formats:

* WAV for high quality
* MP3 for compatibility
* M4A for mobile devices
* OGG for web use
* AAC for streaming

## Agent Architecture

FableFlow uses a two-agent music system:

- **Music Director Agent** - Analyzes story mood, plans musical themes, determines instrumentation
- **Musician Agent** - Generates original compositions using AI music models

These agents create soundtracks that enhance emotional impact and complement the storytelling.

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Listen to generated music in the Media Gallery

### Option 2: CLI - Individual Music Generation

```bash
# Generate music (requires processed story)
fable-flow music produce
```

### Option 3: CLI - Full Publishing Pipeline

```bash
# Run complete pipeline including music
fable-flow publisher process
```

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

The music pipeline generates:

* `music/` directory containing:
    * Main soundtrack
    * Scene-specific tracks
    * Character themes
    * Sound effects
* `metadata.json` with music details
* `mood_guide.json` for consistency

## Integration

Music generation works seamlessly with:

* **Story Processing** - Uses mood analysis
* **Video Production** - Provides soundtrack
* **Narration** - Balances with voice
* **Illustration** - Enhances visual impact

## Best Practices

1. **Mood Selection**
    * Match story tone
    * Consider audience
    * Ensure appropriateness
    * Maintain consistency

2. **Audio Quality**
    * Check mixing
    * Verify balance
    * Test transitions
    * Review integration

3. **Asset Management**
    * Organize by scene
    * Track versions
    * Backup original files
    * Document settings

## Troubleshooting

### Common Issues

**Issue**: Music too loud/quiet
**Solution**: Adjust mixing parameters and volume levels

**Issue**: Mood mismatch
**Solution**: Review mood settings and story analysis

**Issue**: Integration problems
**Solution**: Check synchronization and timing settings

### Getting Help

- Check the [full documentation](../README.md)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) 