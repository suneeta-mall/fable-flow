# Configuration Management

This directory contains configuration files for the Fable Flow project. The configuration system uses YAML files and Pydantic for type safety and validation.

## Configuration Structure

The configuration is organized into several sections:

- `model`: Model-related settings
  - `server`: Model server configuration
  - `default`: Default model to use
  - `text_generation`: Text generation model settings
  - `image_generation`: Image generation model settings
  - `text_to_speech`: Text-to-speech model settings
  - `music_generation`: Music generation model settings
  - `video_generation`: Video generation model settings
  - `content_safety`: Content safety model settings

- `api`: API keys and endpoints
  - `keys`: Dictionary of API keys

- `paths`: File system paths
  - `base`: Base directory
  - `data`: Data directory
  - `output`: Output directory
  - `cache`: Cache directory

- `style`: Style configurations
  - `illustration`: Illustration style settings
  - `music`: Music style settings
  - `video`: Video style settings

## Usage

The configuration is automatically loaded from `config/default.yaml` when the application starts. You can access the configuration in your code like this:

```python
from fable_flow.config import config

# Access model configuration
model_name = config.model.default
server_url = config.model.server.url

# Access API keys
openai_key = config.api.keys["openai"]

# Access paths
output_dir = config.paths.output

# Access style settings
illustration_style = config.style.illustration
```

## Environment Variables

The configuration system supports environment variables. You can override configuration values using environment variables with the following format:

```
MODEL__DEFAULT=google/gemma-3-27b-it
MODEL__SERVER__URL=http://localhost:8000/v1
API__KEYS__OPENAI=your-api-key
```

## Configuration Files

- `default.yaml`: Default configuration file
- `development.yaml`: Development environment configuration
- `production.yaml`: Production environment configuration

## Validation

The configuration system uses Pydantic for validation. This ensures that:

1. All required fields are present
2. Values are of the correct type
3. Values meet any specified constraints
4. Environment variables are properly loaded and validated

## Adding New Configuration

To add new configuration options:

1. Add the new fields to the appropriate Pydantic model in `producer/fable_flow/config.py`
2. Add the corresponding values to `config/default.yaml`
3. Update this documentation if necessary 