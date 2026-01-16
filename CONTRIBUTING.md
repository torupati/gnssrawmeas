# Contributing to gnssraw

Thank you for your interest in contributing to gnssraw! This guide will help you get started.

## Getting Started

### Prerequisites

1. Install [uv](https://astral.sh/uv) for Python dependency management:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/torupati/gnssraw.git
   cd gnssraw
   ```

3. Sync dependencies:
   ```bash
   uv sync
   ```

## Development Workflow

### 1. Create a Feature Branch

Always create a new branch for your changes:

```bash
git checkout main
git pull origin main
git checkout -b feature/<issue-number>-<description>
```

Branch naming conventions:
- `feature/<issue-number>-<description>` - New features
- `bugfix/<issue-number>-<description>` - Bug fixes  
- `docs/<description>` - Documentation updates
- `enhancement/<issue-number>-<description>` - Improvements

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style and patterns
- Add tests for new functionality (when applicable)
- Update documentation as needed

### 3. Test Your Changes

Before committing, run the linter and type checker:

```bash
# Install dev dependencies if not already installed
uv sync

# Run ruff linter
uv run ruff check .

# Run ruff formatter check
uv run ruff format --check .

# Run mypy type checker
uv run mypy --explicit-package-bases app --pretty
```

Fix any issues reported by these tools.

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Brief description of changes"
```

Good commit message examples:
- `Add support for GLONASS constellation`
- `Fix pytest assertion in test_ambiguity`
- `Update API documentation for process endpoint`

### 5. Push and Create Pull Request

```bash
git push origin feature/<your-branch-name>
```

Then:
1. Go to the repository on GitHub
2. Click "Compare & pull request"
3. Fill in the PR template:
   - Describe what changes you made
   - Reference related issues (e.g., "Fixes #8")
   - Explain why the changes are needed
4. Submit the pull request

### 6. Address Review Feedback

- Respond to reviewer comments
- Make requested changes
- Push updates to your branch (they'll automatically appear in the PR)
- Request re-review when ready

## Code Style Guidelines

This project uses:

- **Ruff** for linting and formatting (configuration in `pyproject.toml`)
- **Mypy** for static type checking
- **Python 3.8+** compatibility

### Key Points

- Use type hints for function parameters and return values
- Follow PEP 8 naming conventions
- Keep functions focused and concise
- Add docstrings to public functions/classes
- Prefer explicit over implicit code

## Pull Request Guidelines

### Good PR Practices

✅ **DO**:
- Keep PRs focused on a single issue/feature
- Write a clear description of changes
- Include tests for new functionality
- Update documentation
- Ensure CI checks pass
- Link related issues

❌ **DON'T**:
- Mix unrelated changes in one PR
- Submit PRs with failing tests
- Include large formatting-only changes with logic changes
- Commit sensitive data or credentials

### PR Review Process

1. Automated CI checks must pass (linting, type checking)
2. At least one approving review required
3. Address all review comments
4. Maintain clean commit history
5. Merge after approval

## Issue Guidelines

### Reporting Bugs

When reporting bugs, include:
- Description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Sample RINEX files (if applicable)

### Suggesting Features

When suggesting features:
- Explain the use case
- Describe expected behavior
- Consider implementation approach
- Check if similar feature exists

## Testing

Currently, the project is working on improving test coverage (see issue #8).

When tests are fully implemented:
```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

## Getting Help

- Check existing issues and PRs
- Review documentation (README.md, API_README.md)
- Open a new issue for questions
- Tag maintainers if needed

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help newcomers learn and contribute

## Branch Protection Rules

The `main` branch is protected with the following rules:
- Pull requests required for all changes
- CI status checks must pass
- At least one approving review needed
- No force pushes allowed

See [BRANCH_PROTECTION.md](BRANCH_PROTECTION.md) for complete details.

## Recognition

Contributors are recognized through:
- Git commit history
- Pull request credits
- Release notes (for significant contributions)

Thank you for contributing to gnssraw! 🛰️
