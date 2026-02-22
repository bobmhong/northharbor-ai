# NorthHarbor Sage

**Your AI-powered guide to a confident retirement.**

Retirement planning shouldn't feel overwhelming. NorthHarbor Sage walks you through the process conversationally, builds a personalized plan based on your goals, and helps you understand your options with clear, probability-based projections.

## Why NorthHarbor?

- **Have a real conversation** — No confusing forms. Just talk through your situation with an AI advisor that asks the right questions and adapts to your needs.

- **See your future clearly** — Monte Carlo simulations show you the range of possible outcomes, not just best-case scenarios. Understand the trade-offs before you decide.

- **Explore what-if scenarios** — Retiring earlier? Working part-time? Different withdrawal strategies? Compare plans side-by-side and see how changes affect your outlook.

- **Get a plan you can use** — Walk away with professional deliverables in PDF, Excel, or Markdown — ready to share with your advisor or keep for your records.

## Try It

Visit [sage.northharbor.dev](https://sage.northharbor.dev) to start your plan.

## Documentation

- [Overview](docs/overview.md) — Product capabilities and use cases
- [Architecture](docs/architecture.md) — System design
- [Roadmap](docs/roadmap.md) — Current and planned work
- [Contributing](CONTRIBUTING.md) — Local setup, workflows, and quality checks

## Getting Started (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- `task` from [taskfile.dev](https://taskfile.dev/)
- Docker Desktop (recommended for local MongoDB/Redis)
- `direnv` (recommended for local secret loading)

Optional LLM providers:
- OpenAI API key via `NORTHHARBOR_OPENAPI_KEY`
- Ollama running locally (for offline/local model development)

### Setup

```bash
# Clone upstream
git clone https://github.com/bobmhong/northharbor-sage.git

# Or fork first, then clone your fork
# git clone https://github.com/YOUR_USERNAME/northharbor-sage.git

# Enter repo
cd northharbor-sage

# Install backend + frontend dependencies
task setup

# Check env wiring (provider/model/key visibility)
task env:check
```

### Run the app

```bash
# Terminal 1
task dev:backend

# Terminal 2
task dev:frontend
```

Frontend: `http://localhost:5173`  
Backend health: `http://localhost:8000/api/health`

Note: `task dev:frontend` runs frontend lint + typecheck before launching Vite, so accessibility/type issues are caught early in the dev loop.

### Common operations

```bash
task lint
task test
task db:up
task db:down
task interview:smoke
```

### LLM analytics persistence

- LLM analytics events are captured in all environments and persisted via the store layer.
- Default backend is MongoDB (`llm_usage_events` collection).
- Indexes are ensured automatically on startup for `timestamp`, `model+timestamp`, and `session_id+timestamp`.
- If Mongo initialization fails, analytics falls back to in-memory storage and logs a warning.

## Development

Use `task --list` to see available workflows. For routine developer/operator operations, prefer `task` commands over ad-hoc shell commands.

## Disclaimer

NorthHarbor Sage is an educational tool designed to help you explore retirement planning concepts and scenarios. **It is not a substitute for professional financial advice.**

- This application does not provide financial, investment, tax, or legal advice.
- Projections are based on assumptions and historical data; actual results may vary significantly.
- Past performance does not guarantee future results.
- Users assume all risk associated with decisions made based on information provided by this tool.
- Consult a qualified financial advisor before making any financial decisions.

By using NorthHarbor Sage, you acknowledge that the developers and operators are not liable for any losses or damages arising from your use of this tool.

## License

[Apache License 2.0](LICENSE)
