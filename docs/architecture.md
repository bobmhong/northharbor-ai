# Architecture

This document provides a high-level overview of the NorthHarbor Sage system architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              React SPA (TypeScript/Tailwind)             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Backend                       │   │
│  │    • Authentication (Auth0)                              │   │
│  │    • Request routing                                     │   │
│  │    • Rate limiting                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Interview       │ │ Projection      │ │ Rendering       │
│ Engine          │ │ Engine          │ │ Engine          │
│                 │ │                 │ │                 │
│ • Guided flow   │ │ • Monte Carlo   │ │ • PDF generation│
│ • AI responses  │ │ • Simulations   │ │ • Excel export  │
│ • State mgmt    │ │ • Scenarios     │ │ • Markdown      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Database    │  │  File Store  │  │  Cache       │          │
│  │  [TBD]       │  │  [TBD]       │  │  [TBD]       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (React SPA)

The user interface is a single-page application built with React and TypeScript.

**Key modules:**
- `pages/` — Page components (Interview, Dashboard, Reports)
- `components/` — Reusable UI components
- `stores/` — State management (interview state, user context)
- `api/` — API client and hooks

### API Gateway (FastAPI)

The backend API handles authentication, request routing, and orchestrates the core services.

**Key modules:**
- `api/` — Route handlers and middleware
- `security/` — Auth, rate limiting, sanitization, audit logging

### Interview Engine

Manages the guided interview flow, including:
- Question sequencing
- AI-powered responses and follow-ups
- Interview state persistence

<!-- TODO: Link to design doc when available -->

### Projection Engine

Runs financial calculations:
- Monte Carlo simulations
- Scenario modeling
- Outcome probability analysis

<!-- TODO: Link to design doc when available -->

### Rendering Engine

Generates deliverables in multiple formats:
- PDF reports
- Excel workbooks
- Markdown documents
- JSON exports

<!-- TODO: Link to design doc when available -->

## Key Flows

### Interview Flow

```
User → Chat UI → API → Interview Engine → AI Service
                           │
                           ▼
                    State Store (interview progress)
```

### Report Generation Flow

```
User requests report → API → Projection Engine → Rendering Engine
                                    │                    │
                                    ▼                    ▼
                           Run simulations        Generate PDF/Excel
                                    │                    │
                                    └────────────────────┘
                                             │
                                             ▼
                                    Return deliverable
```

## Security Model

- **Authentication:** Auth0 (JWT tokens)
- **Authorization:** Role-based access control (TBD)
- **Input validation:** Request sanitization
- **Audit logging:** Security-relevant events logged

See [docs/admin/auth0_setup.md](admin/auth0_setup.md) for Auth0 configuration.

## Deployment

<!-- TODO: Document deployment architecture -->

- Containerized with Docker
- Orchestration: TBD
- Hosting: TBD

## Related Documents

- [Overview](overview.md) — Product capabilities
- [Roadmap](roadmap.md) — Planned work
- [Design Documents](design/README.md) — Detailed technical designs
