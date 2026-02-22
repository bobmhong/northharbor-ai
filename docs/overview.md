# NorthHarbor Sage Overview

NorthHarbor Sage is an AI-powered retirement planning assistant that guides users through a comprehensive intake process, runs financial projections with Monte Carlo simulations, and generates personalized retirement plan deliverables.

## Key Capabilities

### Guided Interview Process
An AI assistant conducts a conversational intake, asking standard retirement planning questions and following up for clarification. The process adapts to each client's situation.

### Financial Projections & Monte Carlo Analysis
The system models retirement outcomes using Monte Carlo simulations, accounting for market variability, inflation, and withdrawal strategies to provide probability-based projections.

### Interactive Plan Review
After initial projections, the assistant reviews findings with the client, addresses concerns, and allows assumption adjustments. Revised plans are generated with side-by-side comparisons.

### Multi-Format Report Generation
Final deliverables are produced in multiple formats:
- Markdown (for web/documentation)
- PDF (for printing/sharing)
- JSON (for integrations)
- Excel (for detailed analysis)

### Document Ingestion
Structured client documents (statements, tax forms) can be ingested, mapped to the data model, and logged for schema evolution tracking.

## Target Users

- **Individuals** planning for retirement

## Use Cases

1. **Self-Service Planning** — Individuals work through the guided interview independently
2. **Scenario Comparison** — Users explore "what-if" scenarios with different assumptions
3. **Document Generation** — Produce professional deliverables for client records

## Technology Stack

<!-- TODO: Update with actual stack details -->

- **Frontend:** React, TypeScript, Tailwind CSS
- **Backend:** Python, FastAPI
- **AI/ML:** [placeholder]
- **Database:** In-memory (dev default) / MongoDB (local Docker or Atlas)
- **Authentication:** Auth0
