# FableFlow Core API 🔌

The FableFlow Core API provides programmatic access to all story creation and processing capabilities. This documentation covers the main API components, usage patterns, and integration examples.

## 🚀 Getting Started

### Installation and Setup

```python
# Install FableFlow
pip install fable-flow

# Import core components
from fable_flow import StoryProcessor, Config, Story
from fable_flow.models import TextModel, ImageModel, AudioModel
from fable_flow.outputs import PDFGenerator, EPUBGenerator, HTMLGenerator
```

### Basic API Usage

```python
# Initialize processor with configuration
processor = StoryProcessor(config_file='config/my_config.yaml')

# Create a story from text
story_text = """
Once upon a time, there was a curious little girl named Emma...
"""

# Process the story
result = processor.create_story(
    content=story_text,
    title="Emma's Adventure",
    target_age="6-8",
    themes=["curiosity", "friendship"]
)

# Access generated content
print(f"Enhanced text: {result.enhanced_text}")
print(f"Generated {len(result.illustrations)} illustrations")
print(f"Audio duration: {result.narration.duration} seconds")
```

## 📋 Core Classes

### StoryProcessor

The main entry point for story creation and processing.

```python
class StoryProcessor:
    def __init__(self, config_file=None, config_dict=None):
        """Initialize the story processor
        
        Args:
            config_file (str): Path to configuration file
            config_dict (dict): Configuration as dictionary
        """
        
    def create_story(self, content, **kwargs) -> ProcessedStory:
        """Create a complete multimedia story
        
        Args:
            content (str): Raw story text
            title (str): Story title
            target_age (str): Target age range (e.g., "5-8")
            themes (list): Story themes
            output_formats (list): Desired output formats
            
        Returns:
            ProcessedStory: Complete processed story object
        """
        
    def enhance_text(self, text, metadata) -> EnhancedText:
        """Enhance story text using AI"""
        
    def generate_illustrations(self, text, scene_count=None) -> List[Illustration]:
        """Generate illustrations for the story"""
        
    def create_narration(self, text, voice_config=None) -> Narration:
        """Generate audio narration"""
        
    def add_background_music(self, story_metadata) -> BackgroundMusic:
        """Generate background music"""
        
    def export_story(self, story, formats, output_dir) -> ExportResult:
        """Export story in specified formats"""
```

### Story and ProcessedStory

Core data structures for representing stories.

```python
class Story:
    """Raw story data structure"""
    def __init__(self, content, title=None, metadata=None):
        self.content = content
        self.title = title
        self.metadata = metadata or {}
        
    @classmethod
    def from_file(cls, file_path):
        """Load story from file"""
        
    @classmethod  
    def from_markdown(cls, markdown_content):
        """Parse story from markdown"""

class ProcessedStory:
    """Complete processed story with all generated content"""
    def __init__(self):
        self.original_text = ""
        self.enhanced_text = ""
        self.illustrations = []
        self.narration = None
        self.background_music = None
        self.metadata = {}
        
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        
    def save(self, file_path):
        """Save processed story to file"""
        
    @classmethod
    def load(cls, file_path):
        """Load processed story from file"""
```

### Configuration Management

```python
class Config:
    """Configuration management"""
    def __init__(self, config_file=None, config_dict=None):
        self.text_model = TextModelConfig()
        self.image_model = ImageModelConfig()
        self.audio_model = AudioModelConfig()
        self.processing = ProcessingConfig()
        self.output = OutputConfig()
        
    @classmethod
    def load(cls, file_path):
        """Load configuration from YAML file"""
        
    def save(self, file_path):
        """Save configuration to YAML file"""
        
    def validate(self):
        """Validate configuration settings"""

class TextModelConfig:
    def __init__(self):
        self.provider = "openai"
        self.model = "gpt-4"
        self.temperature = 0.7
        self.max_tokens = 2000
        self.safety_filter = True

class ImageModelConfig:
    def __init__(self):
        self.provider = "openai"
        self.model = "dall-e-3"
        self.style = "digital art"
        self.quality = "hd"
        self.size = "1024x1024"

class AudioModelConfig:
    def __init__(self):
        self.provider = "elevenlabs"
        self.voice_id = "narrator"
        self.stability = 0.75
        self.similarity_boost = 0.8
```

## 🎨 Model Interfaces

### Text Processing

```python
from fable_flow.models import TextModel

class TextModel:
    """Abstract base class for text processing models"""
    
    def enhance_story(self, text, metadata) -> str:
        """Enhance raw story text"""
        raise NotImplementedError
        
    def generate_scenes(self, text) -> List[Scene]:
        """Extract scenes from story text"""
        raise NotImplementedError
        
    def create_discussion_questions(self, text, age_group) -> List[str]:
        """Generate educational discussion questions"""
        raise NotImplementedError

# Example implementation
class OpenAITextModel(TextModel):
    def __init__(self, api_key, model="gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    def enhance_story(self, text, metadata):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._create_system_prompt(metadata)},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
        
    def _create_system_prompt(self, metadata):
        return f"""
        Enhance this story for children aged {metadata.get('target_age', '5-10')}.
        Themes: {', '.join(metadata.get('themes', []))}
        Make it engaging, age-appropriate, and educational.
        """
```

### Image Generation

```python
from fable_flow.models import ImageModel

class ImageModel:
    """Abstract base class for image generation"""
    
    def generate_illustration(self, prompt, style_config=None) -> bytes:
        """Generate single illustration"""
        raise NotImplementedError
        
    def generate_batch(self, prompts, style_config=None) -> List[bytes]:
        """Generate multiple illustrations"""
        raise NotImplementedError
        
    def ensure_consistency(self, prompts, character_descriptions) -> List[str]:
        """Modify prompts to ensure character consistency"""
        raise NotImplementedError

class DALLEImageModel(ImageModel):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        
    def generate_illustration(self, prompt, style_config=None):
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=self._enhance_prompt(prompt, style_config),
            size="1024x1024",
            quality="hd",
            n=1
        )
        
        # Download and return image data
        image_url = response.data[0].url
        return self._download_image(image_url)
```

### Audio Synthesis

```python
from fable_flow.models import AudioModel

class AudioModel:
    """Abstract base class for audio generation"""
    
    def synthesize_speech(self, text, voice_config=None) -> bytes:
        """Convert text to speech"""
        raise NotImplementedError
        
    def generate_music(self, style, duration, metadata=None) -> bytes:
        """Generate background music"""
        raise NotImplementedError
        
    def combine_audio(self, speech, music, balance=0.8) -> bytes:
        """Combine speech and music"""
        raise NotImplementedError

class ElevenLabsAudioModel(AudioModel):
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        
    def synthesize_speech(self, text, voice_config=None):
        voice_id = voice_config.get('voice_id', 'default')
        
        response = requests.post(
            f"{self.base_url}/text-to-speech/{voice_id}",
            headers={"xi-api-key": self.api_key},
            json={
                "text": text,
                "voice_settings": {
                    "stability": voice_config.get('stability', 0.75),
                    "similarity_boost": voice_config.get('similarity_boost', 0.8)
                }
            }
        )
        
        return response.content
```

## 📤 Output Generation

### Export Formats

```python
from fable_flow.outputs import OutputGenerator

class OutputGenerator:
    """Base class for output format generation"""
    
    def generate(self, story: ProcessedStory, output_path: str):
        """Generate output in specific format"""
        raise NotImplementedError

class PDFGenerator(OutputGenerator):
    def generate(self, story, output_path):
        """Generate PDF version of the story"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf = canvas.Canvas(output_path, pagesize=letter)
        
        # Add title
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawString(100, 750, story.title)
        
        # Add content
        pdf.setFont("Helvetica", 12)
        y_position = 700
        
        for paragraph in story.enhanced_text.split('\n\n'):
            pdf.drawString(100, y_position, paragraph[:80])
            y_position -= 20
            
        # Add illustrations
        for i, illustration in enumerate(story.illustrations):
            if i < 5:  # Limit for demo
                pdf.drawImage(illustration.image_path, 100, y_position - 200, 
                            width=200, height=150)
                y_position -= 220
                
        pdf.save()

class EPUBGenerator(OutputGenerator):
    def generate(self, story, output_path):
        """Generate EPUB version of the story"""
        from ebooklib import epub
        
        book = epub.EpubBook()
        book.set_identifier(f"story_{story.metadata.get('id', 'unknown')}")
        book.set_title(story.title)
        book.set_language('en')
        
        # Add chapters
        chapter = epub.EpubHtml(
            title=story.title,
            file_name='chapter_1.xhtml',
            lang='en'
        )
        
        chapter.content = self._create_html_content(story)
        book.add_item(chapter)
        
        # Add images
        for illustration in story.illustrations:
            img = epub.EpubImage()
            img.file_name = f'image_{illustration.scene_number}.jpg'
            img.content = illustration.image_data
            book.add_item(img)
            
        # Define Table of Contents
        book.toc = (epub.Link("chapter_1.xhtml", story.title, "chapter_1"),)
        
        # Add navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # Write EPUB file
        epub.write_epub(output_path, book, {})
```

## 🔧 Advanced API Usage

### Custom Processing Pipeline

```python
from fable_flow.pipeline import ProcessingPipeline, PipelineStep

class CustomProcessingPipeline(ProcessingPipeline):
    def __init__(self, config):
        super().__init__(config)
        
    def build_pipeline(self):
        """Build custom processing pipeline"""
        return [
            PipelineStep("validate_input", self.validate_input),
            PipelineStep("enhance_text", self.enhance_text),
            PipelineStep("extract_scenes", self.extract_scenes),
            PipelineStep("generate_illustrations", self.generate_illustrations),
            PipelineStep("create_narration", self.create_narration),
            PipelineStep("add_music", self.add_background_music),
            PipelineStep("generate_metadata", self.generate_metadata),
            PipelineStep("export_outputs", self.export_outputs)
        ]
        
    def validate_input(self, story_data):
        """Custom input validation"""
        if len(story_data.content) < 100:
            raise ValueError("Story too short")
        return story_data
        
    def generate_metadata(self, processed_story):
        """Generate custom metadata"""
        processed_story.metadata.update({
            'word_count': len(processed_story.enhanced_text.split()),
            'reading_time': self.estimate_reading_time(processed_story.enhanced_text),
            'illustration_count': len(processed_story.illustrations),
            'narration_duration': processed_story.narration.duration if processed_story.narration else 0
        })
        return processed_story

# Usage
pipeline = CustomProcessingPipeline(config)
result = pipeline.process(story_input)
```

### Async Processing

```python
import asyncio
from fable_flow.async_processor import AsyncStoryProcessor

async def process_multiple_stories(story_list):
    """Process multiple stories concurrently"""
    processor = AsyncStoryProcessor(config_file='config/async_config.yaml')
    
    # Process stories concurrently
    tasks = [
        processor.create_story_async(
            content=story['content'],
            title=story['title'],
            target_age=story['target_age']
        )
        for story in story_list
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle results and exceptions
    successful_results = []
    failed_results = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_results.append({'story': story_list[i], 'error': result})
        else:
            successful_results.append(result)
            
    return successful_results, failed_results

# Usage
stories = [
    {'content': 'Story 1...', 'title': 'Adventure 1', 'target_age': '5-8'},
    {'content': 'Story 2...', 'title': 'Adventure 2', 'target_age': '6-9'},
]

successful, failed = asyncio.run(process_multiple_stories(stories))
```

### Plugin System

```python
from fable_flow.plugins import Plugin, register_plugin

class CustomEnhancementPlugin(Plugin):
    """Example custom plugin for story enhancement"""
    
    name = "custom_enhancement"
    version = "1.0.0"
    description = "Custom story enhancement plugin"
    
    def __init__(self, config):
        self.config = config
        
    def enhance_story(self, story_text, metadata):
        """Custom story enhancement logic"""
        # Add custom enhancements
        enhanced = story_text
        
        # Example: Add educational callouts
        if 'science' in metadata.get('themes', []):
            enhanced = self.add_science_callouts(enhanced)
            
        # Example: Adjust reading level
        target_age = metadata.get('target_age', '5-10')
        enhanced = self.adjust_reading_level(enhanced, target_age)
        
        return enhanced
        
    def add_science_callouts(self, text):
        """Add science fact callouts"""
        # Implementation here
        return text
        
    def adjust_reading_level(self, text, target_age):
        """Adjust text for target reading level"""
        # Implementation here
        return text

# Register the plugin
register_plugin(CustomEnhancementPlugin)

# Use in configuration
config = {
    'plugins': {
        'custom_enhancement': {
            'enabled': True,
            'priority': 10
        }
    }
}
```

## 🧪 Testing and Validation

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from fable_flow import StoryProcessor, Config

class TestStoryProcessor(unittest.TestCase):
    def setUp(self):
        self.config = Config({
            'text_model': {'provider': 'mock'},
            'image_model': {'provider': 'mock'},
            'audio_model': {'provider': 'mock'}
        })
        self.processor = StoryProcessor(config_dict=self.config.to_dict())
        
    def test_story_creation(self):
        """Test basic story creation"""
        story_content = "Once upon a time, there was a brave little mouse."
        
        result = self.processor.create_story(
            content=story_content,
            title="Mouse Adventure",
            target_age="5-7"
        )
        
        self.assertIsNotNone(result)
        self.assertIn("mouse", result.enhanced_text.lower())
        self.assertEqual(result.title, "Mouse Adventure")
        
    @patch('fable_flow.models.OpenAITextModel.enhance_story')
    def test_text_enhancement(self, mock_enhance):
        """Test text enhancement with mocking"""
        mock_enhance.return_value = "Enhanced story text"
        
        result = self.processor.enhance_text("Original text", {})
        
        self.assertEqual(result.text, "Enhanced story text")
        mock_enhance.assert_called_once()
        
    def test_configuration_validation(self):
        """Test configuration validation"""
        invalid_config = Config({'text_model': {'provider': 'invalid'}})
        
        with self.assertRaises(ValueError):
            invalid_config.validate()

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
import pytest
from fable_flow import StoryProcessor
import tempfile
import os

@pytest.fixture
def temp_output_dir():
    """Create temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def sample_story():
    """Sample story for testing"""
    return {
        'content': """
        Emma was excited about her first day at the new school. 
        She packed her favorite book and walked through the colorful doors.
        """,
        'title': "Emma's First Day",
        'target_age': "6-8",
        'themes': ["school", "confidence"]
    }

def test_end_to_end_story_creation(temp_output_dir, sample_story):
    """Test complete story creation pipeline"""
    processor = StoryProcessor(config_file='config/test_config.yaml')
    
    # Create story
    result = processor.create_story(**sample_story)
    
    # Validate results
    assert result is not None
    assert len(result.enhanced_text) > len(sample_story['content'])
    assert len(result.illustrations) > 0
    assert result.narration is not None
    
    # Export story
    export_result = processor.export_story(
        result, 
        formats=['pdf', 'html'],
        output_dir=temp_output_dir
    )
    
    # Verify files were created
    assert os.path.exists(os.path.join(temp_output_dir, "Emma's First Day.pdf"))
    assert os.path.exists(os.path.join(temp_output_dir, "Emma's First Day.html"))

def test_error_handling(sample_story):
    """Test error handling in story processing"""
    # Test with invalid configuration
    processor = StoryProcessor(config_dict={'invalid': 'config'})
    
    with pytest.raises(Exception):
        processor.create_story(**sample_story)
```

## 📊 Monitoring and Analytics

### Usage Tracking

```python
from fable_flow.analytics import UsageTracker

class UsageTracker:
    def __init__(self, config):
        self.config = config
        self.metrics = {}
        
    def track_story_creation(self, story_metadata):
        """Track story creation metrics"""
        self.metrics['stories_created'] = self.metrics.get('stories_created', 0) + 1
        self.metrics['total_words'] = self.metrics.get('total_words', 0) + story_metadata.get('word_count', 0)
        
    def track_api_usage(self, provider, model, tokens_used):
        """Track API usage and costs"""
        key = f"{provider}_{model}"
        if key not in self.metrics:
            self.metrics[key] = {'calls': 0, 'tokens': 0, 'cost': 0}
            
        self.metrics[key]['calls'] += 1
        self.metrics[key]['tokens'] += tokens_used
        self.metrics[key]['cost'] += self.calculate_cost(provider, model, tokens_used)
        
    def get_usage_report(self):
        """Generate usage report"""
        return {
            'summary': self.metrics,
            'timestamp': datetime.now().isoformat(),
            'period': 'session'
        }
```

## 🚀 Production Deployment

### API Server

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fable_flow import StoryProcessor
import asyncio

app = FastAPI(title="FableFlow API", version="1.0.0")

class StoryRequest(BaseModel):
    content: str
    title: str = None
    target_age: str = "5-10"
    themes: list = []
    output_formats: list = ["pdf", "html"]

class StoryResponse(BaseModel):
    id: str
    status: str
    enhanced_text: str = None
    illustrations: list = []
    download_urls: dict = {}

processor = StoryProcessor(config_file='config/production.yaml')

@app.post("/stories", response_model=StoryResponse)
async def create_story(request: StoryRequest):
    """Create a new story"""
    try:
        result = await processor.create_story_async(
            content=request.content,
            title=request.title,
            target_age=request.target_age,
            themes=request.themes
        )
        
        return StoryResponse(
            id=result.id,
            status="completed",
            enhanced_text=result.enhanced_text,
            illustrations=[ill.to_dict() for ill in result.illustrations],
            download_urls=result.download_urls
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stories/{story_id}")
async def get_story(story_id: str):
    """Get story by ID"""
    # Implementation here
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

This comprehensive API documentation provides everything you need to integrate FableFlow into your applications. For more examples and advanced usage patterns, check out our [GitHub repository](https://github.com/suneeta-mall/fable-flow) and [community discussions](https://github.com/suneeta-mall/fable-flow/discussions)!