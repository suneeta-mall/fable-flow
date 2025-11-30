# Troubleshooting Guide 🔧

This guide helps you resolve common issues when installing, configuring, and using FableFlow. Most problems have straightforward solutions!

## 🚀 Installation Issues

### Python Version Problems

**Problem**: "FableFlow requires Python 3.8 or higher"
```bash
ERROR: fable-flow requires Python >=3.8, but you have Python 3.7
```

**Solutions**:
```bash
# Check your Python version
python --version
python3 --version

# Install Python 3.8+ using pyenv (recommended)
pyenv install 3.9.16
pyenv global 3.9.16

# Or use system package manager
# Ubuntu/Debian
sudo apt update && sudo apt install python3.9 python3.9-pip

# macOS with Homebrew
brew install python@3.9
```

### Dependency Installation Failures

**Problem**: "Failed building wheel for [package]"

**Solutions**:
```bash
# Update pip and setuptools first
pip install --upgrade pip setuptools wheel

# Install build dependencies
# Ubuntu/Debian
sudo apt install build-essential python3-dev

# macOS
xcode-select --install

# Install with verbose output to see specific errors
pip install fable-flow -v
```

### Virtual Environment Issues

**Problem**: "Command 'fable-flow' not found after installation"

**Solutions**:
```bash
# Make sure you're in the correct virtual environment
which python
which pip

# Reinstall in the correct environment
pip uninstall fable-flow
pip install fable-flow

# Check if it's in PATH
pip show -f fable-flow

# Try running as module
python -m fable_flow --help
```

## ⚙️ Configuration Problems

### Missing Configuration File

**Problem**: "Configuration file not found"
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/default.yaml'
```

**Solutions**:
```bash
# Create default configuration
fable-flow init

# Or copy from examples
cp examples/config/basic.yaml config/my_config.yaml

# Specify config file explicitly
fable-flow create --config /path/to/your/config.yaml
```

### API Key Issues

**Problem**: "Invalid API key" or "Authentication failed"

**Solutions**:
```bash
# Check if API keys are set
echo $OPENAI_API_KEY
echo $REPLICATE_TOKEN

# Set API keys in environment
export OPENAI_API_KEY="your-key-here"
export REPLICATE_TOKEN="your-token-here"

# Or set in configuration file
# config/your_config.yaml
api_keys:
  openai: "your-key-here"
  replicate: "your-token-here"

# Test API connectivity
fable-flow test-api --provider openai
```

### Configuration Validation Errors

**Problem**: "Invalid configuration" or schema validation errors

**Solutions**:
```bash
# Validate your configuration
fable-flow validate-config config/your_config.yaml

# Use the configuration wizard
fable-flow config-wizard

# Check against example configurations
diff config/your_config.yaml examples/config/basic.yaml
```

## 🎨 Story Generation Issues

### Text Enhancement Problems

**Problem**: Generated text is poor quality or inappropriate

**Solutions**:
```yaml
# Adjust text generation parameters
text_generation:
  model: "gpt-4"  # Use higher quality model
  temperature: 0.3  # Lower for more consistent output
  max_tokens: 2000
  safety_filter: strict
  
enhancement:
  preserve_structure: true
  maintain_theme: true
  age_appropriate: true
  reading_level: "elementary"  # Specify target level
```

**Debugging steps**:
```bash
# Test text generation in isolation
fable-flow generate text --input "test story" --debug

# Review intermediate outputs
fable-flow create --save-intermediate --output debug/
```

### Image Generation Failures

**Problem**: "Image generation failed" or poor quality images

**Solutions**:
```yaml
# Adjust image generation settings
image_generation:
  model: "dall-e-3"  # Use higher quality model
  style: "digital art, children's book illustration"
  quality: "hd"
  safety_filter: true
  
  # Improve prompts
  prompt_enhancement: true
  character_consistency: true
  scene_coherence: true
```

**Debugging steps**:
```bash
# Test image generation separately
fable-flow generate images --story-file your_story.md --debug

# Review generated prompts
fable-flow create --save-prompts --output debug/
```

### Audio Generation Issues

**Problem**: "Audio synthesis failed" or poor audio quality

**Solutions**:
```yaml
# Audio configuration adjustments
audio_generation:
  voice_model: "eleven-labs"  # Try different providers
  voice_settings:
    stability: 0.75
    similarity_boost: 0.8
    style: 0.2
  
  # Improve audio quality
  sample_rate: 44100
  format: "wav"
  enhancement: true
```

**Debugging steps**:
```bash
# Test audio generation
fable-flow generate audio --text "test narration" --debug

# Check audio file properties
file output/narration.wav
ffprobe output/narration.wav
```

## 🔧 Performance Issues

### Slow Processing

**Problem**: Story generation takes too long

**Solutions**:
```yaml
# Performance optimization
processing:
  parallel_generation: true
  batch_size: 4
  cache_enabled: true
  
  # Use faster models for development
  development_mode: true
  quick_generation: true
```

**System optimization**:
```bash
# Check system resources
htop
nvidia-smi  # For GPU usage

# Increase memory allocation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Use SSD for temporary files
export TMPDIR=/path/to/fast/storage
```

### Memory Issues

**Problem**: "Out of memory" errors during generation

**Solutions**:
```yaml
# Memory management
memory:
  max_image_batch: 2  # Reduce batch size
  clear_cache_interval: 5
  model_offloading: true
  
processing:
  sequential_mode: true  # Process one at a time
  memory_efficient: true
```

**System fixes**:
```bash
# Increase swap space
sudo swapon --show
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Monitor memory usage
watch -n 1 free -h
```

## 🌐 Network and API Issues

### Connection Timeouts

**Problem**: "Request timeout" or "Connection failed"

**Solutions**:
```yaml
# Increase timeout settings
api_settings:
  timeout: 120  # seconds
  retry_count: 3
  retry_delay: 5
  
  # Use different endpoints
  use_fallback_endpoints: true
```

**Network debugging**:
```bash
# Test connectivity
curl -I https://api.openai.com/
ping api.replicate.com

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Test with different DNS
nslookup api.openai.com 8.8.8.8
```

### Rate Limiting

**Problem**: "Rate limit exceeded" or "Too many requests"

**Solutions**:
```yaml
# Rate limiting configuration
rate_limiting:
  requests_per_minute: 10
  backoff_factor: 2
  max_retries: 5
  
  # Distribute across multiple keys
  api_key_rotation: true
```

**Implementation**:
```python
# Add delays between requests
import time
time.sleep(1)  # Wait 1 second between requests

# Use exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def make_api_call():
    # Your API call here
    pass
```

## 📁 File and Output Issues

### Output Format Problems

**Problem**: Generated files are corrupted or wrong format

**Solutions**:
```bash
# Check file permissions
ls -la output/
chmod 755 output/
chmod 644 output/*

# Validate file formats
file output/story.pdf
pdfinfo output/story.pdf

# Regenerate with different format
fable-flow create --output-format pdf,epub,html
```

### Missing Output Files

**Problem**: Some output files are not generated

**Solutions**:
```yaml
# Ensure all outputs are enabled
output:
  formats: ["pdf", "epub", "html", "markdown"]
  include_assets: true
  include_metadata: true
  
generation:
  skip_on_error: false  # Don't skip failed components
  continue_on_warning: true
```

**Debugging**:
```bash
# Check logs for errors
fable-flow create --log-level debug --log-file generation.log
tail -f generation.log

# Verify intermediate files
ls -la output/intermediate/
```

## 🐛 Debug Mode and Logging

### Enable Debug Output

```bash
# Run with full debugging
fable-flow create --debug --verbose --log-level debug

# Save all intermediate outputs
fable-flow create --save-intermediate --output debug/

# Generate detailed report
fable-flow create --generate-report --report debug/report.html
```

### Log Analysis

```bash
# View recent logs
tail -100 ~/.fable-flow/logs/latest.log

# Search for specific errors
grep -i error ~/.fable-flow/logs/latest.log
grep -i "failed" ~/.fable-flow/logs/latest.log

# Monitor logs in real-time
tail -f ~/.fable-flow/logs/latest.log
```

## 🔍 Getting Help

### Before Asking for Help

1. **Check the logs**: Look for specific error messages
2. **Try minimal example**: Test with simple input
3. **Check dependencies**: Ensure all requirements are met
4. **Update software**: Make sure you have the latest version

```bash
# Get version information
fable-flow --version
fable-flow info

# Run system check
fable-flow doctor

# Generate diagnostic report
fable-flow diagnose --output diagnostic_report.txt
```

### Community Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/suneeta-mall/fable-flow/issues)
- **Discussions**: [Get help from the community](https://github.com/suneeta-mall/fable-flow/discussions)
- **Documentation**: [Browse complete documentation](getting-started/installation.md)

### Creating Bug Reports

Include this information:
```
FableFlow Version: [version]
Python Version: [version]
Operating System: [OS and version]
Configuration: [relevant config sections]
Error Message: [exact error text]
Steps to Reproduce: [detailed steps]
Expected Behavior: [what should happen]
Actual Behavior: [what actually happens]
```

## 🔄 Common Fixes

### Reset Everything

```bash
# Complete reset (nuclear option)
pip uninstall fable-flow
rm -rf ~/.fable-flow/
rm -rf venv/  # if using virtual environment

# Fresh installation
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install --upgrade pip
pip install fable-flow
fable-flow init
```

### Update Everything

```bash
# Update FableFlow
pip install --upgrade fable-flow

# Update all dependencies
pip install --upgrade -r requirements.txt

# Clear caches
pip cache purge
fable-flow clear-cache
```

### Verify Installation

```bash
# Test basic functionality
fable-flow --help
fable-flow init
fable-flow test-system

# Create a simple test story
echo "Once upon a time..." > test_story.txt
fable-flow create --input test_story.txt --config config/minimal.yaml
```

---

## 💡 Prevention Tips

### Regular Maintenance
- Keep FableFlow and dependencies updated
- Monitor disk space and memory usage  
- Regularly backup your configuration and stories
- Test your setup with simple examples

### Best Practices
- Use virtual environments for isolation
- Version control your configuration files
- Monitor API usage and costs
- Keep API keys secure and rotate them regularly

Still having issues? Don't hesitate to reach out to our [community](https://github.com/suneeta-mall/fable-flow/discussions) - we're here to help! 🤝