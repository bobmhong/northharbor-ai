# Contributing to NorthHarbor AI

Thank you for your interest in contributing to NorthHarbor AI!

## Getting Started

1. Choose one clone workflow:
   - Clone the canonical upstream repository:
     `git clone https://github.com/bobmhong/northharbor-ai.git`
   - Or fork first, then clone your fork:
     `git clone https://github.com/YOUR_USERNAME/northharbor-ai.git`
2. If you forked, add upstream so you can sync future changes:
   `git remote add upstream https://github.com/bobmhong/northharbor-ai.git`
3. Ensure prerequisites are installed:
   - Python 3.11+
   - Node.js 20+ and npm
   - `task` from [taskfile.dev](https://taskfile.dev/)
   - Docker Desktop (recommended for MongoDB/Redis workflows)
   - `direnv` (recommended for loading local secrets)
4. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
5. Install dependencies: `task setup`
6. Configure runtime environment:
   - OpenAI path: set `NORTHHARBOR_OPENAPI_KEY` (for `LLM_PROVIDER=openai`)
   - Ollama path: run local Ollama and set `LLM_PROVIDER=ollama`
7. Validate environment wiring: `task env:check`

## Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run linting and tests (see below)
4. Commit with a clear message
5. Push and open a PR

## Running the Application

```bash
# Backend
task dev:backend

# Frontend
task dev:frontend
```

For all common operations, prefer `task` commands over ad-hoc shell commands.

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
task test
```

Additional useful commands:

```bash
task lint
task format
task db:up
task db:down
task interview:smoke
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
3. Update `Taskfile.yml` when operating procedures or recurring workflows change
4. Fill out the PR template
5. Request review from a maintainer
6. Address review feedback
7. Squash commits on merge

## Reporting Issues

- Use the issue templates provided
- Include reproduction steps for bugs
- Check existing issues before creating new ones

## Design Documents

For significant changes, please create a design document in `docs/design/` using the template provided. See [docs/design/README.md](docs/design/README.md) for the process.

## Questions?

Open a GitHub Discussion or reach out to the maintainers.
