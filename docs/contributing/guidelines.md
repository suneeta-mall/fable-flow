# Contributing Guidelines

Thank you for your interest in contributing to Fable Flow! 🎉 We welcome contributions from developers, writers, designers, and storytellers who want to help make AI-powered storytelling accessible to everyone.

## 🌟 Ways to Contribute

### 🐛 Bug Reports
- Report issues you encounter
- Provide detailed reproduction steps
- Include system information and error messages

### 💡 Feature Requests
- Suggest new capabilities
- Propose improvements to existing features
- Share your use cases and requirements

### 🔧 Code Contributions
- Fix bugs and improve performance
- Add new features and capabilities
- Enhance documentation and examples

### 📚 Documentation
- Improve guides and tutorials
- Add examples and use cases
- Translate documentation

### 🎨 Creative Contributions
- Share example stories and projects
- Create templates and presets
- Design better user interfaces

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

We follow these coding standards to maintain code quality:

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

All contributions must include appropriate tests:

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
- **Docstrings**: Use Google-style docstrings for all public functions
- **Type Hints**: Include comprehensive type annotations
- **Examples**: Provide usage examples in docstrings

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
- **Markdown**: Use clear, well-structured Markdown
- **Code Examples**: Include working, tested examples
- **Cross-references**: Link related documentation sections

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

Use descriptive branch names with prefixes:

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

When creating a PR, include:

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

1. **Automated Checks**: CI/CD pipeline runs tests and quality checks
2. **Code Review**: Maintainers review code for quality and design
3. **Testing**: Manual testing of new features if needed
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to main branch

## 🎯 Development Focus Areas

### Current Priorities

1. **Performance Optimization**
   - Faster model loading and inference
   - Memory usage optimization
   - Parallel processing improvements

2. **Model Integration**
   - Support for more AI models
   - Local model deployment
   - Custom model fine-tuning

3. **User Experience**
   - Better error messages and debugging
   - Improved CLI interface
   - Web interface development

4. **Content Quality**
   - Better story enhancement algorithms
   - Improved illustration consistency
   - Advanced music generation

### Future Roadmap

- **Multi-language Support**: Internationalization and localization
- **Collaborative Features**: Real-time collaboration and sharing
- **Cloud Integration**: Hosted services and API endpoints
- **Educational Tools**: Curriculum integration and assessment

## 🏆 Recognition

Contributors are recognized in several ways:

### Contributors Wall
All contributors are listed in our [Contributors](../contributors.md) page with:
- Profile links and contributions
- Special recognition for major contributions
- Annual contributor highlights

### Contributor Levels
- **🌱 New Contributor**: First contribution merged
- **🌿 Regular Contributor**: Multiple contributions over time
- **🌳 Core Contributor**: Significant ongoing contributions
- **🏆 Maintainer**: Leadership and project maintenance

### Swag and Rewards
- Contributor stickers and swag
- Conference speaking opportunities
- LinkedIn recommendations
- Resume reference letters

## 🤝 Community Guidelines

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). Key points:

- **Be Respectful**: Treat all community members with respect
- **Be Inclusive**: Welcome people of all backgrounds and experience levels
- **Be Collaborative**: Work together constructively
- **Be Patient**: Help newcomers learn and grow

### Communication Channels

- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests
- **Discord** (coming soon): Real-time chat and collaboration
- **Email**: Direct contact for sensitive issues

### Getting Help

- **New Contributors**: Tag issues with `good-first-issue`
- **Documentation**: Comprehensive guides and examples
- **Mentorship**: Experienced contributors willing to help
- **Office Hours**: Regular community sessions (announced on Discord)

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

## 🎉 Thank You!

Your contributions make Fable Flow better for everyone. Whether you're fixing a typo, adding a feature, or sharing your story creations, every contribution matters.

**Questions?** Don't hesitate to ask! We're here to help and excited to see what you'll create with Fable Flow.

---

*Happy Contributing! 🚀* 