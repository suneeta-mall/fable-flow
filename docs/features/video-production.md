# Video Production

FableFlow turns your story into an animated video, combining illustrations, narration, and music through a three-agent system.

## Overview

The pipeline animates scenes (image-to-video), synchronizes narration and audio, integrates music, applies transitions and effects, and renders the final video.

## Agent Architecture

Three agents collaborate:

- **Movie Director Agent** - Plans scenes, determines camera movements, creates storyboards
- **Animator Agent** - Converts illustrations to video using image-to-video AI models
- **Movie Producer Agent** - Assembles all elements (images, narration, music) into final video

## Key Features

### Animation Generation

Produces scene-based animations with character movement, camera moves, and dynamic transitions.

### Video Enhancement

Adds transitions, visual effects, text overlays, and timing synchronization.

### Output Format

* **MP4** (H.264/AAC) - Universal format for web, mobile, and desktop playback
  - Codec: libx264 (video), aac (audio)
  - Frame rate: 24 fps
  - Compatible with all major platforms and browsers

## Usage

### Option 1: FableFlow Studio (Recommended)

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Run the publisher pipeline
4. Watch generated video in the Media Gallery
5. Monitor three-stage production: Director → Animator → Producer

### Option 2: CLI

```bash
# Run the full generation pipeline (video production runs as a stage within it)
fable-flow generate examples/cassie_beach_adventure_input.json
```

Video production runs as a stage within `fable-flow generate`, after the illustration, narration, and music stages it depends on. This ensures all dependencies (story, illustrations, narration, music) are created first. Use `--resume` to re-run only missing pieces. The stage can also be re-run from FableFlow Studio.

### Configuration

Video settings in `config/default.yaml`:

```yaml
model:
  video_generation:
    model: "hunyuanvideo-community/HunyuanVideo-I2V"
    height: 720
    width: 1280
    num_frames: 129  # HunyuanVideo supports up to 129 frames (5 seconds)
    num_inference_steps: 50
    guidance_scale: 1.0
    true_cfg_scale: 6.0
    fps: 25
    negative_prompt: "scary faces, frightening expressions, dark shadows..."

style:
  video:
    animation_style: "3D animation with 2D elements"
    color_palette: "vibrant and child-friendly"
    camera_style: "dynamic and engaging"
```

**Supported Models:**

- `hunyuanvideo-community/HunyuanVideo-I2V` - High quality image-to-video (default)
- Other image-to-video diffusion models via Hugging Face

## Output

**Main Output:**
```
output/
└── story_video.mp4       # Final assembled video with narration and music
```

**Intermediate Files (created during production):**
```
output/
├── movie_director.txt    # Director's scene planning and storyboard
├── movie_0.mp4          # Individual scene videos
├── movie_1.mp4
├── movie_N.mp4
├── music_0.mp3          # Music segments per scene
├── music_1.mp3
└── music_N.mp3
```

**Dependencies (required from other agents):**

- `image_0.png`, `image_1.png`, etc. - From IllustratorAgent
- `narration.m4a` - From NarratorAgent
- `music.mp3` - From MusicianAgent (fallback if per-scene music not available)

## Integration

Video production feeds into:

* **Story Processing** - Uses enhanced text
* **Illustration Generation** - Uses visual assets
* **Narration** - Synchronizes audio
* **Music Generation** - Integrates soundtrack

## Best Practices

1. **Animation Style** - match the audience and educational goals, with smooth, consistent transitions.
2. **Video Quality** - check resolution, frame rate, and audio sync.
3. **Asset Management** - organize by scene, track versions, and back up originals.

### Getting Help

See the [full documentation](../README.md), [GitHub issues](https://github.com/suneeta-mall/fable-flow/issues), and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
