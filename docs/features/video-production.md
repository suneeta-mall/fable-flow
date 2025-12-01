# Video Production

Fable Flow's video production feature transforms your story into engaging, animated videos. Using advanced AI models, it creates dynamic visual narratives that combine illustrations, narration, and music into a cohesive multimedia experience.

## Overview

The video production pipeline creates videos through a **three-agent system** that orchestrates:

* Scene animation and image-to-video conversion
* Narration and audio synchronization
* Music integration and mixing
* Visual effects and transitions
* Final assembly and rendering

## Agent Architecture

FableFlow uses a three-agent video production system:

- **Movie Director Agent** - Plans scenes, determines camera movements, creates storyboards
- **Animator Agent** - Converts illustrations to video using image-to-video AI models
- **Movie Producer Agent** - Assembles all elements (images, narration, music) into final video

These agents collaborate to create cohesive multimedia storytelling experiences.

## Key Features

### Animation Generation

The system provides:

* Scene-based animations
* Character movements
* Educational visualizations
* Dynamic transitions
* Camera movements

### Video Enhancement

Enhances videos with:

* Professional transitions
* Visual effects
* Text overlays
* Educational graphics
* Timing synchronization

### Output Format

Generates video in:

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

### Option 2: CLI - Individual Video Production

```bash
# Generate video (requires processed story, images, narration, music)
fable-flow director produce
```

Note: Video production depends on outputs from illustration, narration, and music agents.

### Option 3: CLI - Full Publishing Pipeline

```bash
# Run complete pipeline including video
fable-flow publisher process
```

This ensures all dependencies (story, illustrations, narration, music) are created first.

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

The video pipeline generates:

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

Video production works seamlessly with:

* **Story Processing** - Uses enhanced text
* **Illustration Generation** - Uses visual assets
* **Narration** - Synchronizes audio
* **Music Generation** - Integrates soundtrack

## Best Practices

1. **Animation Style**
    * Match target audience
    * Consider educational goals
    * Ensure smooth transitions
    * Maintain consistency

2. **Video Quality**
    * Check resolution
    * Verify frame rate
    * Test audio sync
    * Review transitions

3. **Asset Management**
    * Organize by scene
    * Track versions
    * Backup original files
    * Document settings

### Getting Help

- Check the [full documentation](../README.md)
- Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) 