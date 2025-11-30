# Quick Start Tutorial

Welcome to Fable Flow! This tutorial will guide you through creating your first AI-powered multimedia story in just a few steps. By the end, you'll have a complete story with narration, illustrations, and music.

## Prerequisites

Before starting this tutorial, make sure you have:

- ✅ Fable Flow installed ([Installation Guide](installation.md))
- ✅ Your virtual environment activated
- ✅ A simple story or text ready to transform

## Tutorial Overview

We'll create a multimedia version of a short story in these steps:

1. **Prepare Your Story** - Set up your input text
2. **Process the Story** - Enhance with AI
3. **Generate Narration** - Create audio
4. **Create Illustrations** - Generate visuals  
5. **Add Music** - Compose background score
6. **Assemble Final Product** - Combine everything

Let's get started! 🚀

## Step 1: Prepare Your Story

First, let's create a simple story to work with. Create a new file called `my_first_story.txt`:

```bash
mkdir -p stories
cat > stories/my_first_story.txt << 'EOF'
The Curious Robot

Once upon a time, in a bustling laboratory, there lived a small robot named Sparky. Sparky had bright blue eyes that glowed with curiosity and a shiny silver body that reflected the colorful lights of the lab.

Every day, Sparky watched the scientists work on amazing experiments. He dreamed of helping them discover something wonderful. One morning, Sparky noticed a strange plant growing in the corner of the lab. Its leaves shimmered with an unusual golden glow.

"What makes you so special?" Sparky asked the plant, his optical sensors whirring with excitement.

The plant seemed to hum in response, and suddenly, Sparky realized that it was responding to the frequency of his electronic voice! Together, they had discovered a new form of plant-robot communication.

From that day forward, Sparky and the golden plant worked together, helping the scientists make incredible discoveries about the connection between technology and nature.
EOF
```

## Step 2: Process the Story

Now let's enhance our story using Fable Flow's AI story processing:

```bash
# Process and enhance the story
fable-flow story process --input stories/my_first_story.txt --output output/
```

This command will:
- ✨ Enhance the narrative structure
- 📝 Optimize language and pacing
- 🎯 Ensure age-appropriate content
- 📊 Generate scene breakdowns for illustration

**Expected Output:**
```
✅ Story processing complete!
📁 Enhanced story saved to: output/enhanced_story.txt
📋 Scene breakdown saved to: output/scenes.json
⏱️ Processing time: 2.3 seconds
```

## Step 3: Generate Narration

Convert your enhanced story into professional audio narration:

```bash
# Generate narration from the enhanced story
fable-flow director produce --input output/enhanced_story.txt --voice-style friendly
```

Options for voice style:
- `friendly` - Warm, engaging tone (great for children's stories)
- `professional` - Clear, authoritative tone
- `dramatic` - Expressive, theatrical tone
- `calm` - Soothing, gentle tone

**Expected Output:**
```
🎙️ Generating narration...
🔊 Voice synthesis complete!
📁 Audio files saved to: output/audio/
   - intro.wav
   - chapter_1.wav
   - chapter_2.wav
   - conclusion.wav
⏱️ Total audio duration: 3 minutes 45 seconds
```

## Step 4: Create Illustrations

Generate beautiful illustrations for your story:

```bash
# Generate illustrations based on scene descriptions
fable-flow illustrator draw --input output/scenes.json --style cartoon
```

Available illustration styles:
- `cartoon` - Friendly, colorful illustrations perfect for children
- `realistic` - Detailed, lifelike artwork
- `minimalist` - Clean, simple designs
- `watercolor` - Soft, artistic style

**Expected Output:**
```
🎨 Creating illustrations...
✅ Generated 5 illustrations:
   - sparky_in_lab.png
   - golden_plant.png  
   - sparky_discovers.png
   - communication.png
   - working_together.png
📁 Images saved to: output/images/
```

## Step 5: Add Background Music

Create a musical score that complements your story:

```bash
# Generate background music
fable-flow music produce --input output/enhanced_story.txt --mood uplifting
```

Music mood options:
- `uplifting` - Cheerful, inspiring melodies
- `mysterious` - Intriguing, suspenseful tones
- `peaceful` - Calm, soothing background
- `adventurous` - Exciting, dynamic rhythms

**Expected Output:**
```
🎵 Composing background music...
🎼 Generated 3 music tracks:
   - intro_theme.wav
   - discovery_theme.wav
   - conclusion_theme.wav
📁 Music saved to: output/music/
```

## Step 6: Assemble Final Product

Combine all elements into a complete multimedia presentation:

```bash
# Create final video/presentation
fable-flow publisher process --input output/ --format video
```

Available output formats:
- `video` - MP4 video with narration, images, and music
- `presentation` - Interactive slideshow
- `epub` - Enhanced digital book
- `pdf` - Printable illustrated book

**Expected Output:**
```
🎬 Assembling final product...
✅ Video created successfully!
📁 Final output: output/my_first_story_complete.mp4
📊 Video details:
   - Duration: 3 minutes 45 seconds
   - Resolution: 1920x1080
   - Format: MP4
   - Size: 45.2 MB
```

## View Your Creation

Congratulations! 🎉 You've created your first multimedia story. Let's see what you've made:

```bash
# View the final video (Linux/macOS)
open output/my_first_story_complete.mp4

# Or on Linux with default video player
xdg-open output/my_first_story_complete.mp4

# Windows
start output/my_first_story_complete.mp4
```

## What You've Accomplished

In just a few commands, you've:

- ✅ **Enhanced** a simple story with AI
- 🎙️ **Generated** professional narration
- 🎨 **Created** beautiful illustrations
- 🎵 **Composed** background music
- 🎬 **Assembled** everything into a polished video

## Next Steps

Now that you've created your first multimedia story, you can:

### Experiment with Different Styles
```bash
# Try different illustration styles
fable-flow illustrator draw --input output/scenes.json --style watercolor

# Experiment with voice options
fable-flow director produce --input output/enhanced_story.txt --voice-style dramatic

# Test different music moods
fable-flow music produce --input output/enhanced_story.txt --mood mysterious
```

### Work with Your Own Stories
```bash
# Process your own story file
fable-flow story process --input path/to/your/story.txt --output my_output/
```

### Customize the Output
```bash
# Create different output formats
fable-flow publisher process --input output/ --format epub
fable-flow publisher process --input output/ --format presentation
```

### Explore Advanced Features

- **[Custom Models](../examples/custom-models.md)** - Use your own AI models
- **[Configuration](configuration.md)** - Customize Fable Flow settings
- **[API Reference](../api/core.md)** - Integrate with your own applications
- **[Contributing](../contributing/guidelines.md)** - Contribute to the open source project

## Troubleshooting

### Common Issues

**Issue**: "No API key found"
**Solution**: Set up your API configuration in `.env` file or use local models

**Issue**: Illustrations look inconsistent
**Solution**: Use `--consistent-style` flag or adjust the style parameters

**Issue**: Audio quality is poor
**Solution**: Check your audio settings or try a different voice model

**Issue**: Video generation fails
**Solution**: Ensure you have enough disk space and all dependencies installed

### Getting Help

- 📖 Check the [full documentation](../README.md)
- 🐛 Report issues on [GitHub](https://github.com/suneeta-mall/fable-flow/issues)
- 💬 Join discussions in the [community forum](https://github.com/suneeta-mall/fable-flow/discussions)

## Congratulations! 

You've successfully completed the Fable Flow quick start tutorial. You're now ready to transform any story into an engaging multimedia experience. The possibilities are endless! ✨

**Share Your Creation**: We'd love to see what you've made! Share your stories with the community and inspire others to explore the magic of AI-powered storytelling. 