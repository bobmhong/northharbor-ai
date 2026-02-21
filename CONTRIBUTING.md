# Contributing to NorthHarbor AI

Thank you for your interest in contributing to NorthHarbor AI!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/northharbor-ai.git`
3. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
4. Install dependencies: `pip install -r backend/requirements.txt`
5. Install frontend dependencies: `cd frontend && npm install`

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run linting and tests (see below)
4. Commit with a clear message
5. Push and open a PR

## Running the Application

```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints for function signatures
- Format with `ruff format`
- Lint with `ruff check`

### TypeScript (Frontend)
- Use TypeScript strict mode
- Format with Prettier
- Lint with ESLint

## Running Tests

```bash
# Backend tests
pytest

# Frontend tests
cd frontend && npm test
```

## Commit Messages

Use conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Example: `feat: add Monte Carlo simulation visualization`

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Fill out the PR template
4. Request review from a maintainer
5. Address review feedback
6. Squash commits on merge

## Reporting Issues

- Use the issue templates provided
- Include reproduction steps for bugs
- Check existing issues before creating new ones

## Design Documents

For significant changes, please create a design document in `docs/design/` using the template provided. See [docs/design/README.md](docs/design/README.md) for the process.

## Questions?

Open a GitHub Discussion or reach out to the maintainers.
