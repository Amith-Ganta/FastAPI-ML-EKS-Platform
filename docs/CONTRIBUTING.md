# Contributing Guidelines

Thank you for your interest in contributing to the Insurance Premium Predictor! This document provides guidelines for participating in the project.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create** a feature branch for your changes
4. **Follow** the guidelines below
5. **Submit** a pull request

## Development Workflow

### 1. Set Up Local Environment

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/FastAPI-ML-Docker-AWS.git
cd FastAPI-ML-Docker-AWS

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

#### Backend Changes (`backend/`)
- Update `backend/app.py` for API logic
- Add models in appropriate modules
- Update `backend/requirements.txt` if adding dependencies

#### Frontend Changes (`frontend/`)
- Update `frontend/frontend.py` for UI changes
- Update `frontend/requirements.txt` if adding dependencies

#### Documentation
- Update relevant `.md` files in `docs/`
- Keep docs in sync with code changes

### 3. Test Locally

```bash
# Using Docker Compose
docker-compose up --build
# Test at http://localhost:8000/docs and http://localhost:8501

# Or without Docker
cd backend && python -m pytest
cd ../frontend && streamlit run frontend.py
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: descriptive message of your changes"
git push origin feature/your-feature-name
```

## Commit Message Format

Follow conventional commits format:

```
<type>: <description>

<optional body>
<optional footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Build, dependencies, CI/CD

### Examples

```
feat: add confidence score to predictions

fix: correct BMI calculation edge case

docs: update API documentation with examples

refactor: reorganize project structure for clarity
```

## Pull Request Process

### Before Submitting

- [ ] Code follows project style
- [ ] Changes are tested locally
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No breaking changes (or documented)

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
Describe testing performed:
- Tested with Docker Compose
- Tested API endpoints at /docs
- Tested Streamlit UI with sample inputs

## Related Issues
Fixes #(issue number)

## Additional Notes
Any additional context or notes
```

## Code Style

### Python

- **Formatter**: Follow PEP 8 style guide
- **Line Length**: 100 characters max
- **Type Hints**: Use type hints for function arguments and returns
- **Imports**: Organize imports (standard library, third-party, local)

Example:

```python
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI

from .models import UserInput

def predict_premium(data: UserInput) -> dict[str, str]:
    """Predict insurance premium category."""
    # Implementation
    return {"predicted_category": result}
```

### Documentation

- Use clear, concise language
- Include code examples where appropriate
- Keep README and docs up-to-date
- Use markdown formatting

## Areas for Contribution

### High Priority
- Unit tests for API endpoints
- Error handling improvements
- Input validation enhancements
- Performance optimizations

### Medium Priority
- Documentation improvements
- Code refactoring
- UI/UX enhancements
- Docker optimization

### Low Priority (Nice to Have)
- Additional prediction features
- Advanced logging
- Monitoring/observability
- Frontend polish

## Bug Reports

Found an issue? Please create a GitHub Issue with:

1. **Title**: Clear, descriptive title
2. **Description**: What happened and what should happen
3. **Steps to Reproduce**: Exact steps to reproduce
4. **Environment**: OS, Docker version, Python version
5. **Expected vs Actual**: What you expected vs what occurred
6. **Logs**: Relevant error messages or logs

### Example

```
## Description
The API returns 422 error when city contains numbers

## Steps to Reproduce
1. Navigate to http://localhost:8501
2. Enter age: 30, city: "Mumbai123", occupation: "private_job"
3. Click "Predict Premium Category"
4. Observe error response

## Expected Behavior
Accept city names with alphanumeric characters

## Actual Behavior
Returns validation error: "value is not a valid string"

## Environment
- OS: Windows 10
- Docker: 24.0
- Python: 3.11
```

## Feature Requests

Have an idea? Create a GitHub Issue with:

1. **Title**: Clear feature description
2. **Problem**: What problem does this solve?
3. **Proposed Solution**: How should it work?
4. **Alternatives**: Any alternatives considered?
5. **Impact**: Who benefits? How does it improve the project?

### Example

```
## Problem
Users want to see prediction confidence scores, not just categories

## Proposed Solution
Return additional `confidence_score` (0-1) with predictions

## Implementation
- Modify model inference to return probabilities
- Update Pydantic response model
- Display scores in Streamlit UI

## Example Response
{
  "predicted_category": "premium_standard",
  "confidence_score": 0.87
}
```

## Questions & Support

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Use GitHub Issues for bugs and features
- **Contact**: Email for sensitive inquiries

## Recognition

Contributors will be recognized in:
- GitHub commit history
- Project CONTRIBUTORS file
- Release notes

## Code of Conduct

This project adheres to the Contributor Covenant. By participating, you agree to:
- Be respectful and inclusive
- Welcome all backgrounds and experiences
- Focus on constructive criticism
- Report concerns to project maintainers

## Review Process

1. Maintainers review PR within 3-7 days
2. Feedback provided (if needed)
3. Contributor updates code
4. Maintainers merge when ready

## Questions?

Feel free to:
- Comment on issues/PRs
- Open a discussion
- Email the maintainer

Thank you for contributing! 🎉
