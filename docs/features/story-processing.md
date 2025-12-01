# Story Processing & Editorial Review

FableFlow's story processing feature transforms your text into an enhanced, multimedia-ready narrative through a comprehensive AI-powered editorial review pipeline. This powerful system analyzes, structures, and optimizes your story through five specialized review stages while maintaining its core message and educational value.

## Overview

The story processing pipeline takes your input text and enhances it through a **5-stage AI editorial review process**:

1. **Friendly Proof** - Initial feedback on readability, flow, and engagement
2. **Critical Review** - Professional editorial analysis of structure, character development, and narrative
3. **Content Check** - Safety validation, age-appropriateness, and educational value assessment
4. **Story Edit** - Structure improvements, pacing optimization, and narrative enhancement
5. **Format Proof** - Final polish, formatting, and preparation for multimedia production

### Author Control

At each stage, you review the AI feedback and **approve or request revisions**. If you reject feedback at any stage, you can revise your manuscript and restart the review process. This ensures you maintain creative control while benefiting from AI-powered editorial insights.

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

### Option 1: FableFlow Studio (Recommended)

Use the web-based Studio interface for the best experience:

1. Start Studio: `make studio-start`
2. Navigate to http://localhost:3000
3. Open or create your story project
4. Edit your manuscript in the Monaco editor
5. Run the publisher pipeline from the UI
6. Monitor real-time progress via WebSocket updates
7. Review AI feedback at each editorial stage
8. Approve or request revisions

### Option 2: CLI - Individual Story Processing

```bash
# Process story manuscript only
fable-flow story process
```

### Option 3: CLI - Full Publishing Pipeline

```bash
# Run complete end-to-end pipeline (includes story processing + multimedia)
fable-flow publisher process
```

This runs all production stages: story review → illustrations → narration → music → books → video

### Configuration

Story processing can be customized through the `config/default.yaml` file or `.env` environment variables:

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

The story processing pipeline generates:

**In FableFlow Studio:**
- Real-time editorial feedback displayed in the UI
- Version comparison view for before/after
- Interactive approval/rejection workflow
- Live progress notifications

**CLI Output Files:**
- `manuscript.txt` - Enhanced manuscript after all review stages
- `editorial_feedback/` - Feedback from each review stage
- `metadata.json` - Processing metadata and settings
- Prepares content for downstream agents (illustration, narration, etc.)

## Agent Architecture

FableFlow uses specialized AI agents for each review stage:

- **Friendly Proofreader Agent** - Initial readability and engagement check
- **Critical Reviewer Agent** - Professional editorial analysis
- **Content Safety Checker Agent** - Safety and appropriateness validation
- **Story Editor Agent** - Structure and narrative improvements
- **Format Proofreader Agent** - Final polish and formatting

These agents work asynchronously using message passing, allowing for efficient parallel processing in the full publisher pipeline.

## Integration

The processed story feeds into downstream production agents:

- **Illustration Planner/Illustrator Agents** - Generate contextual illustrations
- **Book Producer Agent** - Create PDF, EPUB, and HTML books
- **Narrator Agent** - Generate audio narration
- **Music Director/Musician Agents** - Compose background music
- **Movie Director/Animator/Producer Agents** - Assemble final video

See [complete workflow documentation](../fableflow-workflow.md) for the full agent pipeline.

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