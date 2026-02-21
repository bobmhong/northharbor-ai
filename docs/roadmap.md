# Roadmap

This document outlines the current and planned work for NorthHarbor AI.

## Current Phase: Foundation

Building core infrastructure and baseline capabilities.

### In Progress

- [ ] Core interview flow (income, expenses, goals, risk tolerance)
- [ ] Monte Carlo projection engine (1K-10K simulations)
- [ ] Provider-agnostic authentication ([Design 002](design/002-provider-agnostic-auth-with-cloudflare-access.md))
- [ ] Conversational interview UI

### Completed

- [x] Project scaffolding
- [x] Basic FastAPI backend structure
- [x] React frontend setup (Vite, TypeScript, Tailwind)
- [x] Auth0 integration setup

---

## Upcoming Work

### Phase 2: Core Features

**Interview & Planning**

- [ ] Complete interview question set (assets, Social Security, pensions)
- [ ] Multi-scenario comparison (what-if analysis)

**Output & Export**

- [ ] PDF report generation
- [ ] Excel export

**Infrastructure**

- [ ] Local MongoDB persistence ([Design 001](design/001-local-mongodb-homelab.md))

### Phase 3: Enhanced Capabilities

**Tax-Aware Modeling**

- [ ] Qualified vs Roth portfolio allocation
  - Track pre-tax and Roth balances independently
  - Tax-aware withdrawal ordering
- [ ] RMD (Required Minimum Distribution) simulation
  - Age-based RMD rules with life-expectancy divisors
  - RMD impact on tax brackets and cashflow

**Document Ingestion**

- [ ] Brokerage statement parsing (PDF)
- [ ] Tax form extraction (1040, W-2 basics)

**Visualization**

- [ ] Projection charts (wealth over time, success probability)
- [ ] Income vs. expense breakdown
- [ ] Side-by-side plan comparison

### Phase 4: Production Readiness

- [ ] Projection API response < 2s (p95) for 10K simulations
- [ ] Test coverage: 80%+ on interview, projection, and auth flows
- [ ] Security review: OWASP Top 10 checklist pass
- [ ] User-facing documentation (getting started guide)
- [ ] CI/CD pipeline with staging environment

---

## Future Considerations

Items under consideration for future phases:

- Mobile-responsive design improvements
- Couples/family planning support

---

## How to Contribute

See [CONTRIBUTING.md](../CONTRIBUTING.md) for how to get involved. For significant features, please create a design document first — see [docs/design/README.md](design/README.md).

---

_Last updated: 2026-02-20_
