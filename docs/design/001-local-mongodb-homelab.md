# Design: Local MongoDB Option for Homelab Deployments

**Status:** Draft  
**Author:** @bobmhong  
**Created:** 2026-02-20  
**Updated:** 2026-02-20  

## Summary

This design adds a first-class local MongoDB runtime option for homelab users while preserving the existing in-memory mode for fast development and tests. It introduces a configurable store backend, a Docker Compose profile for local MongoDB, startup checks and index initialization, and operational guidance for backups and secure local deployment.

## Motivation

NorthHarbor AI currently uses in-memory runtime stores in API dependency wiring, which is convenient for development but does not persist data across restarts. Homelab users need a local, self-hosted persistence option that is easy to run, secure by default, and aligned with the existing MongoDB store implementations already present in the backend.

## Goals

- Provide a supported local MongoDB mode for self-hosted and homelab use.
- Keep `memory` mode available for tests and low-friction development.
- Make backend store selection explicit and environment-driven.
- Add a minimal operational baseline (indexes, health checks, backup guidance).

## Non-Goals

- Multi-node MongoDB cluster orchestration.
- Managed cloud database provisioning.
- Database migrations beyond current store schemas.

## Detailed Design

### Overview

Introduce `STORE_BACKEND` runtime selection with two backends:

- `memory` (default for tests and minimal local setup)
- `mongodb` (persistent local/homelab mode)

When `mongodb` is selected, the API initializes MongoDB clients and concrete store implementations at startup, ensures required indexes, and surfaces connection state through health checks. A Docker Compose profile provides a one-command local database option with durable volumes.

### Component Changes

- `backend/config.py`
  - Add `store_backend` setting (`memory` or `mongodb`).
  - Add optional Mongo settings for auth-ready deployment docs (username/password/auth source).
- `backend/api/deps.py`
  - Add store factory functions keyed by `store_backend`.
  - Replace in-memory-only globals with backend-aware providers.
- `backend/api/app.py`
  - Add startup lifecycle hook to initialize Mongo dependencies and indexes.
  - Expand `/api/health` payload with backend mode and datastore readiness.
- `backend/stores/mongodb.py`
  - Reuse existing stores and `ensure_indexes()` methods; no major API changes.
- `docker-compose.yml` (new)
  - Add `mongo` service and persistent volume.
  - Add optional hardened profile notes for auth-enabled homelab setups.
- `README.md` and `docs/admin/` (new guide)
  - Document setup, environment variables, backup/restore, and troubleshooting.

### Data Model

No canonical schema changes are required. Existing collections remain:

- `user_profiles`
- `audit_log`

New configuration model fields:

```python
class Settings(BaseSettings):
    store_backend: Literal["memory", "mongodb"] = "memory"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "northharbor_ai"
```

### API Changes

No breaking API contract changes are required for business endpoints.

`GET /api/health` response is extended with diagnostics:

```
GET /api/health
Response: {
  "status": "ok",
  "store_backend": "memory|mongodb",
  "mongodb": {
    "connected": true|false,
    "database": "northharbor_ai"
  }
}
```

### Key Flows

```
1. Operator sets STORE_BACKEND=mongodb and MONGODB_URI in .env
2. API starts and initializes Mongo client + stores
3. API ensures indexes (user_profiles, audit_log)
4. Requests use Mongo-backed stores for persistence
5. /api/health exposes backend mode and datastore readiness
```

### Error Handling

- Invalid `STORE_BACKEND` value: fail fast on startup with clear config error.
- Mongo unavailable while `STORE_BACKEND=mongodb`: startup fails with actionable message.
- Index creation failure: startup fails and logs index name + cause.
- Runtime operation failure: return typed API error and audit-safe log message.

## Alternatives Considered

### Alternative 1: Keep Memory-Only Runtime

Rejected because it does not satisfy persistence requirements for homelab users and blocks realistic operational validation.

### Alternative 2: Require MongoDB for All Environments

Rejected because it increases local setup complexity and slows tests that do not need persistence.

## Security Considerations

- Default docs recommend localhost-only binding for local single-host deployments.
- Hardened profile requires credentials and non-default secrets.
- No secrets committed to repo; all credentials come from `.env`.
- Backup artifacts should be protected and excluded from public shares.

## Performance Considerations

- Mongo-backed stores add network and serialization overhead versus memory mode.
- Indexes on `auth0_sub`, `timestamp`, and query fields reduce lookup cost.
- Health check should use lightweight ping to avoid startup latency.

## Testing Strategy

- Unit tests for backend selection and settings validation.
- Integration tests for Mongo store initialization and index creation.
- Manual testing with Docker Compose: create/read/update profile and audit entries.

## Migration / Rollout

1. Merge config and dependency wiring with default `memory` backend unchanged.
2. Add `docker-compose.yml` Mongo service and local run instructions.
3. Enable `STORE_BACKEND=mongodb` in homelab environments.
4. Validate with health check and CRUD smoke tests.
5. Add backup runbook (`mongodump` / `mongorestore`) for operators.

## Open Questions

- [ ] Should `store_backend` default to `memory` or `mongodb` in non-test development?
- [ ] Do we need a dedicated `docs/admin/mongodb_homelab.md` runbook now or after first implementation PR?

## References

- [Design 002: Provider-Agnostic Auth with Cloudflare Access Option](002-provider-agnostic-auth-with-cloudflare-access.md)
- Existing Mongo stores: `backend/stores/mongodb.py`
- Existing config: `backend/config.py`
- Existing API dependencies: `backend/api/deps.py`
- MongoDB backup/restore tools: https://www.mongodb.com/docs/manual/tutorial/backup-and-restore-tools/
