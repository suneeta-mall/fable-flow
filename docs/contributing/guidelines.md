# Contributing Guidelines

Thank you for your interest in contributing to Fable Flow! We welcome developers, writers, designers, and storytellers.

## 🌟 Ways to Contribute

### 🐛 Bug Reports
- Report issues with detailed reproduction steps
- Include system information and error messages

### 💡 Feature Requests
- Suggest new capabilities or improvements
- Share your use cases

### 🔧 Code Contributions
- Fix bugs and improve performance
- Add new features
- Enhance documentation and examples

### 📚 Documentation
- Improve guides and tutorials
- Add examples and use cases
- Translate documentation

### 🎨 Creative Contributions
- Share example stories and projects
- Create templates and presets

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/fable-flow.git
cd fable-flow

# Add the original repository as upstream
git remote add upstream https://github.com/suneeta-mall/fable-flow.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install development dependencies
make install

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Feature Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create a new branch for your feature
git checkout -b feature/your-feature-name
```

## 🛠️ Development Workflow

### Code Standards

#### Python Code Style
- **Formatter**: Black (line length: 100)
- **Linter**: Ruff with strict settings
- **Type Hints**: MyPy for type checking
- **Import Organization**: isort

#### Code Quality Checks
```bash
# Format code
make fmt

# Run all tests
make test

# Check code quality
ruff check .
mypy producer/
```

#### Pre-commit Hooks
Our pre-commit hooks automatically:

- Format code with Black
- Sort imports with isort
- Lint with Ruff
- Check type hints with MyPy
- Validate commit messages

### Testing Requirements

All contributions must include appropriate tests.

#### Unit Tests
```bash
# Run unit tests only
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_story.py -v
```

#### Integration Tests
```bash
# Run integration tests
pytest tests/integration/ -v
```

#### Test Coverage
```bash
# Generate coverage report
make test-cov

# View HTML coverage report
make test-cov-html
```

**Coverage Requirements:**

- Minimum 80% overall coverage
- New code should have 90%+ coverage
- Critical paths must have 100% coverage

### Documentation Standards

#### Code Documentation
- **Docstrings**: Google-style for all public functions
- **Type Hints**: Comprehensive annotations
- **Examples**: Usage examples in docstrings

```python
def process_story(story_text: str, options: StoryOptions) -> ProcessedStory:
    """Process a story using FableFlow.
    
    Args:
        story_text: The input story text to process
        options: Configuration options for processing
        
    Returns:
        ProcessedStory object with enhanced content
        
    Raises:
        ValidationError: If story_text is empty or invalid
        
    Example:
        ```python
        story = "Once upon a time..."
        options = StoryOptions(style="children")
        result = process_story(story, options)
        ```
    """
```

#### Documentation Files
- **Markdown**: Clear, well-structured
- **Code Examples**: Working, tested examples
- **Cross-references**: Link related sections

## 📝 Commit Guidelines

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix  
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples
```
feat(story): add support for multiple languages

fix(illustrator): resolve memory leak in image generation

docs(api): update configuration guide with new options

test(integration): add tests for video generation pipeline
```

### Branch Naming

Use descriptive prefixes:

```
feature/story-language-support
fix/memory-leak-illustrator
docs/update-api-guide
refactor/config-system
```

## 🔄 Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run quality checks**:
   ```bash
   make fmt
   make test
   ruff check .
   mypy src/
   ```

3. **Update documentation** if needed

4. **Add tests** for new functionality

### Pull Request Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated documentation

## Screenshots/Examples
If applicable, add screenshots or examples.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and quality checks
2. **Code Review**: Maintainers review for quality and design
3. **Testing**: Manual testing of new features if needed
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main

## 🎯 Development Focus Areas

### Current Priorities

1. **Performance Optimization** - faster model loading and inference, memory and parallel processing
2. **Model Integration** - more AI models, local deployment, custom fine-tuning
3. **User Experience** - better error messages, improved CLI, web interface
4. **Content Quality** - story enhancement, illustration consistency, music generation

### Future Roadmap

- **Multi-language Support**: Internationalization and localization
- **Collaborative Features**: Real-time collaboration and sharing
- **Cloud Integration**: Hosted services and API endpoints
- **Educational Tools**: Curriculum integration and assessment

## 🏆 Recognition

### Contributors Wall
All contributors are listed on our [Contributors](../contributors.md) page.

### Contributor Levels
- **🌱 New Contributor**: First contribution merged
- **🌿 Regular Contributor**: Multiple contributions over time
- **🌳 Core Contributor**: Significant ongoing contributions
- **🏆 Maintainer**: Leadership and project maintenance

## 🤝 Community Guidelines

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Key points:

- **Be Respectful**: Treat all members with respect
- **Be Inclusive**: Welcome all backgrounds and experience levels
- **Be Collaborative**: Work together constructively
- **Be Patient**: Help newcomers learn

### Communication Channels

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Discord** (coming soon): Real-time chat
- **Email**: Direct contact for sensitive issues

### Getting Help

- **New Contributors**: Look for `good-first-issue` labels
- **Documentation**: Guides and examples
- **Mentorship**: Experienced contributors willing to help

## 📋 Issue Guidelines

### Bug Reports

Use the bug report template and include:

```markdown
**Describe the bug**
Clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g. Ubuntu 20.04]
- Python version: [e.g. 3.11]
- Fable Flow version: [e.g. 0.1.0]

**Additional context**
Add any other context about the problem here.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
Clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Use cases**
How would this feature be used?

**Additional context**
Add any other context or screenshots.
```

---

**Questions?** Ask in GitHub Discussions. We're happy to help.
