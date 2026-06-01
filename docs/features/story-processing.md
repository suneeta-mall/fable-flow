# Story Processing & Editorial Review

FableFlow runs your text through a five-stage AI editorial pipeline that analyzes, structures, and prepares it for multimedia production while preserving its message and educational value.

## Overview

The pipeline enhances your input through five review stages:

1. **Friendly Proof** - readability, flow, and engagement feedback
2. **Critical Review** - structure, character development, and narrative analysis
3. **Content Check** - safety, age-appropriateness, and educational value
4. **Story Edit** - structure, pacing, and narrative improvements
5. **Format Proof** - final polish, formatting, and prep for production

### Author Control

At each stage you approve or request revisions. Reject feedback to revise your manuscript and restart the review, keeping creative control over the AI's suggestions.

## Key Features

### Intelligent Story Analysis

Analyzes narrative structure and flow, character consistency, educational value, age-appropriateness, and scientific accuracy where applicable.

### Content Enhancement

Optimizes vocabulary for the target audience, improves pacing, adds discussion points, and keeps tone and scientific accuracy consistent.

### Scene Preparation

Breaks the story into scenes, flags key visual moments, generates image prompts, and plans music and sound placement for downstream production.

## Usage

### Option 1: FableFlow Studio (Recommended)

Use the web-based Studio interface:

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Open or create your story project
4. Edit your manuscript in the Monaco editor
5. Run the publisher pipeline from the UI
6. Monitor real-time progress via WebSocket updates
7. Review AI feedback at each editorial stage
8. Approve or request revisions

### Option 2: CLI

```bash
# Run the full generation pipeline (story processing runs as a stage within it)
fable-flow generate examples/cassie_beach_adventure_input.json
```

Story processing runs as a stage within `fable-flow generate`. This runs all production stages: story review → illustrations → narration → music → books → video. Use `--book-only` to stop after the book (no movie), and `--resume` to re-run only missing pieces. The stage can also be re-run from FableFlow Studio.

### Configuration

Customize via `config/default.yaml` or `.env`:

```yaml
model:
  text_generation:
    story: "claude-opus-4-20250514"  # Or any vLLM-compatible model
    proofreading: "claude-sonnet-4-20250514"
    editorial: "claude-opus-4-20250514"

# Environment variables (.env file)
MODEL_API_KEY=your_api_key
MODEL_SERVER_URL=http://localhost:8000/v1  # Optional: custom vLLM server
```

FableFlow supports OpenAI API standards, including Claude API, vLLM, and other compatible model servers.

## Output

**In FableFlow Studio:** real-time editorial feedback, before/after version comparison, an approval/rejection workflow, and live progress notifications.

**CLI Output Files:**

- `manuscript.txt` - Enhanced manuscript after all review stages
- `editorial_feedback/` - Feedback from each review stage
- `metadata.json` - Processing metadata and settings
- Prepares content for downstream agents (illustration, narration, etc.)

## Agent Architecture

Each stage has a dedicated agent:

- **Friendly Proofreader Agent** - readability and engagement
- **Critical Reviewer Agent** - editorial analysis
- **Content Safety Checker Agent** - safety and appropriateness
- **Story Editor Agent** - structure and narrative
- **Format Proofreader Agent** - final polish and formatting

Agents communicate via message passing, enabling parallel processing in the full publisher pipeline.

## Integration

The processed story feeds downstream agents:

- **Illustration Planner/Illustrator Agents** - Generate contextual illustrations
- **Book Producer Agent** - Create PDF, EPUB, and HTML books
- **Narrator Agent** - Generate audio narration
- **Music Director/Musician Agents** - Compose background music
- **Movie Director/Animator/Producer Agents** - Assemble final video

See [complete workflow documentation](../fableflow-workflow.md) for the full agent pipeline.

## Best Practices

1. **Input Quality** - provide clear, well-structured text with educational objectives and target age group.
2. **Processing Options** - pick a model suited to your content; tune temperature for creativity vs. consistency; set a seed for reproducibility.
3. **Output Management** - review enhanced content and use the scene breakdown for illustration planning.

## Troubleshooting

### Common Issues

**Issue**: Story structure not maintained
**Solution**: Check input formatting and use appropriate model settings

**Issue**: Educational content not enhanced
**Solution**: Ensure educational objectives are clear in input

**Issue**: Scene breakdown incomplete
**Solution**: Verify story has clear scene transitions

### Getting Help

See the [full documentation](../README.md), [GitHub issues](https://github.com/suneeta-mall/fable-flow/issues), and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
