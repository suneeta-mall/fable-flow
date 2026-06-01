# Custom Models Guide 🤖

Integrate your own AI models with FableFlow while using the platform's workflow management.

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

FableFlow selects models through configuration (`config/default.yaml`) and environment variables (`.env`). The text model talks to any OpenAI-compatible server, while image, TTS, music, and video models are configured by their Hugging Face model IDs:

```
FableFlow Core
├── Story Generation Pipeline
├── Configuration (config/default.yaml + .env)
├── Model Wrappers
│   ├── EnhancedTextModel   (LLM, OpenAI-compatible server)
│   ├── EnhancedImageModel  (diffusion image generation)
│   ├── TTS / Music / Video models
└── Output Generation (PDF / EPUB / MP4)
```

## 📝 Text Model Integration

### Point the LLM at Your Own Server

The text model (`EnhancedTextModel`) calls any OpenAI-compatible endpoint. Configure it through environment variables in `.env`:

```bash
# .env
MODEL_SERVER_URL="https://your-llm-server.example.com/v1"
MODEL_API_KEY="your-api-key"
DEFAULT_MODEL="your-model-name"
```

You can also override the LLM per run with the `--model` flag:

```bash
fable-flow generate examples/cassie_beach_adventure_input.json --model your-model-name
```

### Using the Text Model Directly

```python
from fable_flow.models.text import EnhancedTextModel

model = EnhancedTextModel()
enhanced = await model.generate(
    prompt="Enhance this children's story...",
    system_message="You are an expert children's book editor.",
    temperature=0.7,
)
```

## 🎨 Custom Image Generation

### Select a Different Image Model

Image generation is configured by model ID in `config/default.yaml` under `model.image_generation`:

```yaml
# config/default.yaml
model:
  image_generation:
    model: "black-forest-labs/FLUX.2-dev"
```

Change `model.image_generation.model` to any compatible diffusion model ID to swap the illustration backend.

### Using the Image Model Directly

```python
from fable_flow.models.image import EnhancedImageModel

m = EnhancedImageModel()
image_bytes = await m.generate_image(
    prompt="A friendly robot in a sunlit laboratory, children's book illustration",
    width=1024,
    height=1024,
    seed=42,
    negative_prompt="blurry, low quality",
)
```

## 🎵 Custom Audio Models

### Select Different TTS and Music Models

Narration and background music are configured by model ID in `config/default.yaml`:

```yaml
# config/default.yaml
model:
  text_to_speech:
    voice_preset: "af_heart"
    sample_rate: 24000
  music_generation:
    model: "facebook/musicgen-small"
```

Change the `model.text_to_speech` settings (e.g. `voice_preset`) and `model.music_generation.model` to adjust the narration and music backends. Movie production (narration, music, and video) runs automatically as stages of `fable-flow generate`; use `--book-only` to skip it.

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

### Configuring Models

Model selection lives in `config/default.yaml` under the `model` section, with secrets and the LLM endpoint supplied via `.env`:

```yaml
# config/default.yaml
model:
  default: "google/gemma-4-31B-it"
  temperature: 0.8
  image_generation:
    model: "black-forest-labs/FLUX.2-dev"
  text_to_speech:
    voice_preset: "af_heart"
  music_generation:
    model: "facebook/musicgen-small"
  video_generation:
    model: "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers"
```

```bash
# .env
MODEL_SERVER_URL="https://your-llm-server.example.com/v1"
MODEL_API_KEY="your-api-key"
DEFAULT_MODEL="your-model-name"
```

### Loading Config Programmatically

```python
from fable_flow.config import config

print(config.model.default)
print(config.model.image_generation.model)
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

# Copy config and input specs
COPY config/ /app/config/
COPY examples/ /app/examples/

# Model selection comes from config/default.yaml and .env
ENV MODEL_SERVER_URL="https://your-llm-server.example.com/v1"

WORKDIR /app
CMD ["fable-flow", "generate", "examples/cassie_beach_adventure_input.json", "--output", "output/"]
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

### Unit Testing the Text Model

```python
# test_custom_text.py
import pytest
from unittest.mock import AsyncMock, patch
from fable_flow.models.text import EnhancedTextModel

@pytest.mark.asyncio
async def test_text_generation():
    """Test text generation against a mocked model server."""
    model = EnhancedTextModel()

    with patch.object(model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Enhanced story text."
        result = await model.generate(
            prompt="Enhance this children's story.",
            system_message="You are an expert children's book editor.",
            temperature=0.7,
        )

    assert result == "Enhanced story text."
    mock_gen.assert_awaited_once()
```

### Validating an Input Spec

```python
# test_input_spec.py
from fable_flow.schemas.input_spec import FableFlowInput

def test_example_spec_loads():
    """The bundled example spec parses into a valid FableFlowInput."""
    spec = FableFlowInput.from_json_file("examples/cassie_beach_adventure_input.json")
    assert spec.project.title
```

### Publishing a Book

```python
# test_publishers.py
from pathlib import Path
from fable_flow.publishers import generate_pdf, generate_epub
from fable_flow.schemas.book_content import BookContent

def test_publish(book: BookContent, tmp_path: Path):
    pdf_path = generate_pdf(book, tmp_path / "book.pdf")
    epub_path = generate_epub(book, tmp_path / "book.epub")
    assert pdf_path.exists()
    assert epub_path.exists()
```

## 📚 Best Practices

### Model Selection Guidelines
- **Accuracy First**: Choose models that produce high-quality, educational content
- **Consistency**: Ensure character and style consistency across generated content
- **Safety**: Implement content filtering and safety measures
- **Performance**: Balance quality with processing speed for your use case

### Integration Best Practices
- **Error Handling**: Implement robust error handling and fallback mechanisms
- **Monitoring**: Track model performance and usage patterns
- **Versioning**: Maintain version control for custom models and configurations
- **Testing**: Test custom integrations before production deployment

### Security Considerations
- **API Keys**: Securely store and rotate API keys
- **Data Privacy**: Handle sensitive story content appropriately
- **Access Control**: Implement authentication for custom model endpoints
- **Audit Logging**: Track model usage for security and compliance

---

Start with the [basic workflow example](basic-workflow.md), then adapt it using the patterns above. For help, see the [community discussions](https://github.com/suneeta-mall/fable-flow/discussions).
