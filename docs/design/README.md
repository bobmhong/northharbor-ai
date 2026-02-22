# Design Documents

This folder contains technical design documents for significant features and architectural decisions in NorthHarbor Sage.

## When to Write a Design Doc

Create a design document when:

- Adding a new major feature or component
- Making architectural changes that affect multiple parts of the system
- Introducing new dependencies or external integrations
- Changes that would benefit from team review before implementation

For small changes, bug fixes, or straightforward enhancements, a design doc is not required.

## Process

1. **Copy the template:** `cp template.md 00X-your-feature-name.md`
2. **Fill in the sections:** Complete all relevant sections
3. **Open a PR:** Submit the design doc for review
4. **Iterate:** Address feedback and update the document
5. **Implement:** Once approved, proceed with implementation
6. **Update status:** Mark as "Implemented" when complete

## Naming Convention

Use sequential numbering with descriptive names:

```
001-interview-engine.md
002-monte-carlo-simulation.md
003-document-ingestion.md
```

## Status Values

- **Draft** — Work in progress, not ready for review
- **In Review** — Open for feedback
- **Approved** — Ready for implementation
- **Implemented** — Design has been built
- **Superseded** — Replaced by a newer design (link to replacement)
- **Rejected** — Not moving forward (document why)

## Index

<!-- Update this list as designs are added -->

| # | Title | Status | Date |
|---|-------|--------|------|
| 001 | [Local MongoDB Option for Homelab Deployments](001-local-mongodb-homelab.md) | Draft | 2026-02-20 |
| 002 | [Provider-Agnostic Auth with Cloudflare Access Option](002-provider-agnostic-auth-with-cloudflare-access.md) | Draft | 2026-02-20 |
| 003 | [Async MongoDB Stores for Plans and Sessions](003-async-mongo-plan-session-stores.md) | Draft | 2026-02-21 |

<!-- Example:
| 001 | [Interview Engine](001-interview-engine.md) | Implemented | 2026-02-20 |
| 002 | [Monte Carlo Simulation](002-monte-carlo-simulation.md) | In Review | 2026-02-25 |
-->
