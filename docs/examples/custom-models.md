# Custom Models Guide 🤖

This guide shows you how to integrate your own AI models with FableFlow, giving you complete control over the story generation process while leveraging the platform's workflow management.

## 🎯 Why Use Custom Models?

### Benefits of Custom Integration
- **Specialized Content**: Models trained on specific educational content or subjects
- **Brand Consistency**: Maintain your organization's voice and style
- **Language Support**: Models optimized for specific languages or cultures
- **Cost Control**: Use your own infrastructure and model licenses
- **Privacy**: Keep sensitive content within your own systems

### Supported Model Types
- **Text Generation**: Custom language models for story enhancement
- **Image Generation**: Specialized illustration models
- **Audio Generation**: Custom voice and music models
- **Video Generation**: Proprietary video creation systems

## 🔧 Integration Architecture

FableFlow supports custom models through a plugin architecture:

```
FableFlow Core
├── Story Processing Pipeline
├── Configuration Management
├── Output Generation
└── Plugin System
    ├── Text Processors
    ├── Image Generators
    ├── Audio Synthesizers
    └── Custom Integrations
```

## 📝 Text Model Integration

### Creating a Custom Text Processor

```python
# custom_text_model.py
from fable_flow.processors import BaseTextProcessor
from your_model_library import YourCustomModel

class CustomTextProcessor(BaseTextProcessor):
    def __init__(self, config):
        super().__init__(config)
        self.model = YourCustomModel(
            model_path=config.get('model_path'),
            api_key=config.get('api_key'),
            custom_params=config.get('model_params', {})
        )
    
    def enhance_story(self, raw_text, metadata):
        """Enhance the story text using your custom model"""
        enhanced = self.model.process_text(
            text=raw_text,
            target_age=metadata.get('target_age'),
            reading_level=metadata.get('reading_level'),
            themes=metadata.get('themes', [])
        )
        
        return {
            'enhanced_text': enhanced,
            'metadata': self.extract_metadata(enhanced),
            'quality_score': self.assess_quality(enhanced)
        }
    
    def extract_metadata(self, text):
        """Extract story metadata from enhanced text"""
        return {
            'word_count': len(text.split()),
            'reading_time': self.estimate_reading_time(text),
            'key_concepts': self.identify_concepts(text),
            'emotional_tone': self.analyze_tone(text)
        }

# Register your custom processor
from fable_flow.registry import register_processor
register_processor('custom_text', CustomTextProcessor)
```

### Configuration for Custom Text Model

```yaml
# config/custom_text_config.yaml
processors:
  text:
    type: custom_text
    model_path: "/path/to/your/model"
    api_key: "your-api-key"
    model_params:
      temperature: 0.7
      max_tokens: 2000
      style_guidance: "educational_narrative"
      safety_level: "strict"
    
enhancement:
  preserve_structure: true
  maintain_theme: true
  age_appropriate_language: true
  reading_level_target: "auto"
```

## 🎨 Custom Image Generation

### Image Model Integration

```python
# custom_image_model.py
from fable_flow.processors import BaseImageProcessor
import requests
import base64

class CustomImageProcessor(BaseImageProcessor):
    def __init__(self, config):
        super().__init__(config)
        self.api_endpoint = config.get('api_endpoint')
        self.api_key = config.get('api_key')
        self.style_config = config.get('style_config', {})
    
    def generate_illustrations(self, story_text, scene_descriptions):
        """Generate illustrations using your custom model"""
        illustrations = []
        
        for i, scene in enumerate(scene_descriptions):
            prompt = self.create_prompt(scene, story_text)
            image_data = self.call_custom_api(prompt)
            
            illustrations.append({
                'scene_number': i + 1,
                'image_data': image_data,
                'alt_text': scene.get('alt_text'),
                'caption': scene.get('caption'),
                'style_metadata': self.extract_style_info(image_data)
            })
        
        return illustrations
    
    def create_prompt(self, scene, context):
        """Create a detailed prompt for your image model"""
        base_prompt = scene.get('description', '')
        
        # Add style consistency
        if self.style_config:
            base_prompt += f" Style: {self.style_config.get('style_type', 'cartoon')}"
            base_prompt += f" Color palette: {self.style_config.get('colors', 'warm')}"
        
        # Add character consistency
        characters = self.extract_characters(context)
        if characters:
            base_prompt += f" Characters: {', '.join(characters)}"
        
        return base_prompt
    
    def call_custom_api(self, prompt):
        """Call your custom image generation API"""
        response = requests.post(
            self.api_endpoint,
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={
                'prompt': prompt,
                'style': self.style_config,
                'size': '1024x1024',
                'quality': 'high'
            }
        )
        
        if response.status_code == 200:
            return response.json()['image_data']
        else:
            raise Exception(f"Image generation failed: {response.text}")

register_processor('custom_image', CustomImageProcessor)
```

### Image Model Configuration

```yaml
# config/custom_image_config.yaml
processors:
  image:
    type: custom_image
    api_endpoint: "https://your-api.example.com/generate"
    api_key: "your-image-api-key"
    style_config:
      style_type: "watercolor_illustration"
      colors: "pastel_warm"
      character_style: "friendly_cartoon"
      background_detail: "detailed"
      consistency_model: "character_aware"
    
    generation_params:
      resolution: "1024x1024"
      quality: "premium"
      batch_size: 4
      safety_filter: true
```

## 🎵 Custom Audio Models

### Voice Synthesis Integration

```python
# custom_audio_model.py
from fable_flow.processors import BaseAudioProcessor
import torch
import torchaudio

class CustomAudioProcessor(BaseAudioProcessor):
    def __init__(self, config):
        super().__init__(config)
        self.voice_model = self.load_voice_model(config.get('voice_model_path'))
        self.music_model = self.load_music_model(config.get('music_model_path'))
        self.voice_config = config.get('voice_config', {})
    
    def generate_narration(self, text_segments, character_mapping):
        """Generate narration using custom voice synthesis"""
        audio_segments = []
        
        for segment in text_segments:
            voice_id = self.get_voice_for_character(
                segment.get('character', 'narrator'),
                character_mapping
            )
            
            audio_data = self.synthesize_speech(
                text=segment['text'],
                voice_id=voice_id,
                emotion=segment.get('emotion', 'neutral'),
                pace=segment.get('pace', 'normal')
            )
            
            audio_segments.append({
                'audio_data': audio_data,
                'duration': self.get_duration(audio_data),
                'character': segment.get('character'),
                'timing_marks': self.extract_timing(audio_data, segment['text'])
            })
        
        return audio_segments
    
    def synthesize_speech(self, text, voice_id, emotion='neutral', pace='normal'):
        """Use your custom TTS model"""
        with torch.no_grad():
            audio_tensor = self.voice_model.generate(
                text=text,
                voice_id=voice_id,
                emotion_embedding=self.get_emotion_embedding(emotion),
                speed_factor=self.get_speed_factor(pace)
            )
        
        # Convert to appropriate format
        audio_np = audio_tensor.cpu().numpy()
        return self.format_audio(audio_np)
    
    def generate_background_music(self, story_metadata, scene_emotions):
        """Generate custom background music"""
        music_prompt = self.create_music_prompt(story_metadata, scene_emotions)
        
        music_data = self.music_model.generate(
            prompt=music_prompt,
            duration=story_metadata.get('estimated_duration', 300),
            style=story_metadata.get('music_style', 'gentle'),
            instruments=story_metadata.get('instruments', ['piano', 'strings'])
        )
        
        return {
            'music_data': music_data,
            'fade_points': self.calculate_fade_points(scene_emotions),
            'volume_curve': self.generate_volume_curve(scene_emotions)
        }

register_processor('custom_audio', CustomAudioProcessor)
```

## 🔗 API Integration Examples

### REST API Integration

```python
# api_integration.py
import requests
import asyncio
import aiohttp

class APIBasedProcessor:
    def __init__(self, config):
        self.base_url = config.get('api_base_url')
        self.api_key = config.get('api_key')
        self.timeout = config.get('timeout', 30)
    
    async def process_with_api(self, data, endpoint):
        """Async API call for better performance"""
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(
                f"{self.base_url}/{endpoint}",
                json=data,
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API call failed: {await response.text()}")
    
    def process_batch(self, items, endpoint, batch_size=5):
        """Process multiple items efficiently"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = asyncio.run(self.process_batch_async(batch, endpoint))
            results.extend(batch_results)
        
        return results
    
    async def process_batch_async(self, batch, endpoint):
        """Process batch of items concurrently"""
        tasks = [
            self.process_with_api(item, endpoint) 
            for item in batch
        ]
        return await asyncio.gather(*tasks)
```

### WebSocket Integration for Real-time Processing

```python
# websocket_integration.py
import websocket
import json
import threading

class RealtimeProcessor:
    def __init__(self, config):
        self.ws_url = config.get('websocket_url')
        self.api_key = config.get('api_key')
        self.ws = None
        self.results = {}
        
    def connect(self):
        """Establish WebSocket connection"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=[f"Authorization: Bearer {self.api_key}"],
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run in separate thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
    
    def process_realtime(self, data, callback):
        """Send data for real-time processing"""
        request_id = self.generate_request_id()
        
        message = {
            'request_id': request_id,
            'type': 'process',
            'data': data
        }
        
        self.ws.send(json.dumps(message))
        
        # Wait for response
        self.wait_for_response(request_id, callback)
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        data = json.loads(message)
        request_id = data.get('request_id')
        
        if request_id in self.results:
            self.results[request_id] = data.get('result')
```

## 🛠️ Configuration Management

### Environment-Specific Configurations

```yaml
# config/production.yaml
models:
  text:
    type: custom_text
    endpoint: "https://prod-api.yourcompany.com/text"
    model_version: "v2.1"
    rate_limit: 100
    
  image:
    type: custom_image  
    endpoint: "https://prod-api.yourcompany.com/image"
    gpu_cluster: "high-performance"
    batch_processing: true
    
  audio:
    type: custom_audio
    endpoint: "https://prod-api.yourcompany.com/audio"
    voice_models: ["narrator", "child", "adult"]
    quality: "premium"

# config/development.yaml
models:
  text:
    type: mock_text  # Use mock for development
    response_delay: 1
    
  image:
    type: mock_image
    placeholder_images: true
    
  audio:
    type: mock_audio
    synthesized_samples: true
```

### Model Fallback Configuration

```yaml
# config/fallback_config.yaml
fallback_strategy:
  enabled: true
  retry_attempts: 3
  timeout_seconds: 30
  
fallback_models:
  text:
    primary: custom_text
    fallback: openai_gpt4
    emergency: built_in_text
    
  image:
    primary: custom_image
    fallback: dall_e_3
    emergency: placeholder_images
    
  audio:
    primary: custom_audio
    fallback: eleven_labs
    emergency: system_tts
```

## 📊 Monitoring and Analytics

### Custom Model Performance Tracking

```python
# monitoring.py
import time
import logging
from functools import wraps

class ModelMonitor:
    def __init__(self, config):
        self.metrics = {}
        self.logger = logging.getLogger('fable_flow_custom')
        
    def track_performance(self, model_name):
        """Decorator to track model performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    self.record_success(model_name, time.time() - start_time)
                    return result
                except Exception as e:
                    self.record_failure(model_name, str(e))
                    raise
                    
            return wrapper
        return decorator
    
    def record_success(self, model_name, duration):
        """Record successful model execution"""
        if model_name not in self.metrics:
            self.metrics[model_name] = {
                'successes': 0,
                'failures': 0,
                'avg_duration': 0,
                'total_duration': 0
            }
        
        metrics = self.metrics[model_name]
        metrics['successes'] += 1
        metrics['total_duration'] += duration
        metrics['avg_duration'] = metrics['total_duration'] / metrics['successes']
        
        self.logger.info(f"{model_name} completed in {duration:.2f}s")
    
    def record_failure(self, model_name, error_message):
        """Record model execution failure"""
        if model_name not in self.metrics:
            self.metrics[model_name] = {
                'successes': 0,
                'failures': 0,
                'avg_duration': 0,
                'total_duration': 0
            }
        
        self.metrics[model_name]['failures'] += 1
        self.logger.error(f"{model_name} failed: {error_message}")
```

## 🚀 Deployment Considerations

### Docker Integration

```dockerfile
# Dockerfile for custom model integration
FROM python:3.9-slim

# Install FableFlow
RUN pip install fable-flow

# Copy custom model files
COPY custom_models/ /app/custom_models/
COPY config/ /app/config/

# Install custom dependencies
COPY requirements-custom.txt /app/
RUN pip install -r /app/requirements-custom.txt

# Set up model paths
ENV CUSTOM_MODEL_PATH=/app/custom_models
ENV FABLE_FLOW_CONFIG=/app/config

WORKDIR /app
CMD ["fable-flow", "serve", "--config", "config/production.yaml"]
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fable-flow-custom
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fable-flow-custom
  template:
    metadata:
      labels:
        app: fable-flow-custom
    spec:
      containers:
      - name: fable-flow
        image: your-registry/fable-flow-custom:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_API_KEY
          valueFrom:
            secretKeyRef:
              name: model-secrets
              key: api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

## 🧪 Testing Custom Models

### Unit Testing Framework

```python
# test_custom_models.py
import unittest
from unittest.mock import Mock, patch
from custom_text_model import CustomTextProcessor

class TestCustomModels(unittest.TestCase):
    def setUp(self):
        self.config = {
            'model_path': '/path/to/test/model',
            'api_key': 'test-key'
        }
        self.processor = CustomTextProcessor(self.config)
    
    def test_text_enhancement(self):
        """Test custom text enhancement"""
        raw_text = "Once upon a time, there was a little girl."
        metadata = {'target_age': '5-7', 'themes': ['friendship']}
        
        result = self.processor.enhance_story(raw_text, metadata)
        
        self.assertIn('enhanced_text', result)
        self.assertIn('metadata', result)
        self.assertGreater(len(result['enhanced_text']), len(raw_text))
    
    @patch('requests.post')
    def test_api_integration(self, mock_post):
        """Test API integration with mocking"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'result': 'enhanced text'}
        
        # Test your API integration here
        result = self.processor.call_external_api('test input')
        
        self.assertEqual(result, 'enhanced text')
        mock_post.assert_called_once()

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
# test_integration.py
import pytest
from fable_flow import create_story
from custom_models import register_all_custom_processors

class TestIntegration:
    def setup_method(self):
        """Set up test environment"""
        register_all_custom_processors()
        self.test_config = 'config/test_custom.yaml'
    
    def test_end_to_end_custom_models(self):
        """Test complete story creation with custom models"""
        story_input = {
            'title': 'Test Story',
            'content': 'This is a test story for custom models.',
            'target_age': '6-8',
            'themes': ['testing', 'technology']
        }
        
        result = create_story(
            input_data=story_input,
            config_file=self.test_config,
            processors=['custom_text', 'custom_image', 'custom_audio']
        )
        
        assert result['status'] == 'success'
        assert 'enhanced_text' in result
        assert 'illustrations' in result
        assert 'narration' in result
    
    def test_fallback_behavior(self):
        """Test fallback to default models when custom models fail"""
        # Simulate custom model failure
        with patch.object(CustomTextProcessor, 'enhance_story', side_effect=Exception('Model failed')):
            result = create_story(
                input_data={'content': 'test'},
                config_file='config/fallback_test.yaml'
            )
            
            # Should still succeed with fallback models
            assert result['status'] == 'success'
```

## 📚 Best Practices

### Model Selection Guidelines
- **Accuracy First**: Choose models that produce high-quality, educational content
- **Consistency**: Ensure character and style consistency across generated content
- **Safety**: Implement appropriate content filtering and safety measures
- **Performance**: Balance quality with processing speed for your use case

### Integration Best Practices
- **Error Handling**: Implement robust error handling and fallback mechanisms
- **Monitoring**: Track model performance and usage patterns
- **Versioning**: Maintain version control for your custom models and configurations
- **Testing**: Thoroughly test custom integrations before production deployment

### Security Considerations
- **API Keys**: Securely store and rotate API keys
- **Data Privacy**: Ensure sensitive story content is handled appropriately
- **Access Control**: Implement proper authentication for custom model endpoints
- **Audit Logging**: Track all model usage for security and compliance

---

Ready to integrate your custom models? Start with the [basic workflow example](basic-workflow.md) and then adapt it using the patterns shown in this guide. Join our [community discussions](https://github.com/suneeta-mall/fable-flow/discussions) for help and to share your custom model experiences!