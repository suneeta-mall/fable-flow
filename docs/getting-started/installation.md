# Installation Guide

This guide will help you install and set up Fable Flow on your system. Follow these steps to get up and running quickly.

## System Requirements

### Minimum Requirements
- **Operating System**: Linux, macOS, or Windows 10/11
- **Python**: 3.11 or higher
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10GB free space
- **GPU**: Optional but recommended for faster AI processing

### Recommended Requirements
- **Python**: 3.11
- **RAM**: 16GB or more
- **GPU**: NVIDIA GPU with 8GB+ VRAM for local AI models
- **Storage**: 50GB+ for models and generated content

## Prerequisites

Before installing Fable Flow, ensure you have the following tools installed:

### 1. Python 3.11+

=== "Linux (Ubuntu/Debian)"
    ```bash
    sudo apt update
    sudo apt install python3.11 python3.11-venv python3.11-dev
    ```

=== "macOS"
    ```bash
    # Using Homebrew
    brew install python@3.11
    
    # Or download from python.org
    # https://www.python.org/downloads/macos/
    ```

=== "Windows"
    Download and install Python from [python.org](https://www.python.org/downloads/windows/)
    
    Make sure to check "Add Python to PATH" during installation.

### 2. Git

=== "Linux (Ubuntu/Debian)"
    ```bash
    sudo apt install git
    ```

=== "macOS"
    ```bash
    # Git comes with Xcode Command Line Tools
    xcode-select --install
    
    # Or using Homebrew
    brew install git
    ```

=== "Windows"
    Download and install Git from [git-scm.com](https://git-scm.com/download/win)

### 3. Make (Build Tools)

=== "Linux (Ubuntu/Debian)"
    ```bash
    sudo apt install build-essential
    ```

=== "macOS"
    ```bash
    # Included with Xcode Command Line Tools
    xcode-select --install
    ```

=== "Windows"
    Install using one of these options:
    
    **Option 1: Chocolatey**
    ```powershell
    choco install make
    ```
    
    **Option 2: Windows Subsystem for Linux (WSL)**
    ```powershell
    wsl --install
    ```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/suneeta-mall/fable-flow.git
cd fable-flow
```

### 2. Create Virtual Environment

Creating a virtual environment isolates Fable Flow's dependencies from your system Python:

```bash
python3.11 -m venv .venv
```

### 3. Activate Virtual Environment

=== "Linux/macOS"
    ```bash
    source .venv/bin/activate
    ```

=== "Windows (Command Prompt)"
    ```cmd
    .venv\Scripts\activate.bat
    ```

=== "Windows (PowerShell)"
    ```powershell
    .venv\Scripts\Activate.ps1
    ```

You should see `(.venv)` in your terminal prompt, indicating the virtual environment is active.

### 4. Install Dependencies

Use the provided Makefile to install all required dependencies:

```bash
make install
```

This command will:
- Install the UV package manager for faster dependency resolution
- Install all Python dependencies from `requirements.txt`
- Install Fable Flow in editable mode
- Verify all dependencies are correctly installed

### 5. Verify Installation

Test that Fable Flow is correctly installed:

```bash
fable-flow --help
```

You should see the Fable Flow help message with available commands.

## Optional: GPU Setup

For better performance with AI models, set up GPU acceleration:

### NVIDIA GPU (CUDA)

1. **Install NVIDIA Drivers**
   - Download from [NVIDIA's website](https://www.nvidia.com/drivers/)
   - Or use your system's package manager

2. **Install CUDA Toolkit**
   ```bash
   # Ubuntu/Debian
   wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
   sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
   wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda-repo-ubuntu2004-12-1-local_12.1.1-530.30.02-1_amd64.deb
   sudo dpkg -i cuda-repo-ubuntu2004-12-1-local_12.1.1-530.30.02-1_amd64.deb
   sudo cp /var/cuda-repo-ubuntu2004-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
   sudo apt-get update
   sudo apt-get -y install cuda
   ```

3. **Verify CUDA Installation**
   ```bash
   nvidia-smi
   nvcc --version
   ```

### Apple Silicon (MPS)

For M1/M2 Macs, PyTorch automatically uses Metal Performance Shaders (MPS):

```bash
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

## Configuration

### Environment Variables

Create a `.env` file in the project root to configure Fable Flow:

```bash
# API Configuration
MODEL_SERVER_URL="https://api.openai.com/v1"
MODEL_API_KEY="your-api-key-here"
DEFAULT_MODEL="gpt-4"

# Optional: Local Model Server
# MODEL_SERVER_URL="http://localhost:8000/v1"
# MODEL_API_KEY="local-dev-key"
# DEFAULT_MODEL="meta-llama/Llama-3.2-3B-Instruct"

# Output Configuration
OUTPUT_DIR="./output"
TEMP_DIR="./temp"

# Processing Configuration
MAX_WORKERS=4
BATCH_SIZE=8

# Optional: Hugging Face Token (for model downloads)
# HUGGINGFACE_TOKEN="your-token-here"
```

> Note: Models will be downloaded automatically when needed. If you're using models from Hugging Face, you may need to set your Hugging Face token in the `.env` file.

### Configuration File

Create a `config.yaml` file in the project root to customize Fable Flow's behavior:

```yaml
# Model Configuration
model:
  video_generation:
    model: "stabilityai/stable-video-diffusion-img2vid-xt"
    min_dim: 768
    max_dim: 1360
    fps: 8

# Processing Configuration
processing:
  max_workers: 4
  batch_size: 8

# Output Configuration
output:
  dir: "./output"
  temp_dir: "./temp"
```

> Note: The `config.yaml` file is optional. If not provided, Fable Flow will use default values. See the [Configuration Guide](configuration.md) for all available options.

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'fable_flow'`
**Solution**: Ensure your virtual environment is activated and run `make install` again.

**Issue**: Permission denied errors on Linux/macOS
**Solution**: Don't use `sudo` with pip. Use virtual environments instead.

**Issue**: CUDA out of memory errors
**Solution**: Reduce batch size in configuration or use CPU-only mode.

**Issue**: Slow model loading
**Solution**: Use local model servers or reduce model size.

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](../troubleshooting.md)
2. Search [GitHub Issues](https://github.com/suneeta-mall/fable-flow/issues)
3. Create a new issue with:
   - Your operating system and Python version
   - Complete error messages
   - Steps to reproduce the problem

## Next Steps

Now that Fable Flow is installed, you're ready to:

- **[Quick Start Tutorial](quick-start.md)** - Create your first multimedia story
- **[Configuration Guide](configuration.md)** - Customize Fable Flow for your needs
- **[Feature Overview](../features/story-processing.md)** - Explore all capabilities

Congratulations! 🎉 You've successfully installed Fable Flow and are ready to transform your stories with AI-powered multimedia creation. 