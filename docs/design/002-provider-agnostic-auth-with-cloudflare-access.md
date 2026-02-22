# Design: Provider-Agnostic Auth with Cloudflare Access Option

**Status:** Draft  
**Author:** @bobmhong  
**Created:** 2026-02-20  
**Updated:** 2026-02-20  

## Summary

Introduce a provider-agnostic authentication layer in the backend so NorthHarbor Sage can accept tokens from Auth0 (current) and Cloudflare Access (alternate), while preserving existing role-based authorization behavior and tenant scoping.

## Motivation

NorthHarbor Sage currently assumes Auth0-specific configuration, token verification, and claim naming across multiple modules. This creates provider lock-in and makes it harder to support teams that already use Cloudflare Zero Trust for access control. Adding a Cloudflare Access option enables lower-friction deployment in Cloudflare-centric environments while keeping Auth0 as the default path.

## Goals

- Support Auth0 and Cloudflare Access token verification behind one backend auth interface.
- Preserve existing RBAC behavior (`client` and `admin`) and tenant isolation by `owner_id`.
- Keep Auth0-compatible behavior as default with no breaking API changes.
- Add clear operator configuration for selecting allowed token issuers.

## Non-Goals

- Replacing Auth0 as the only supported identity provider.
- Building a full custom CIAM system on Cloudflare Workers.
- Redesigning frontend login UX in this phase.

## Detailed Design

### Overview

Refactor auth verification and claim models to remove Auth0-specific naming from core interfaces. Add provider-specific verifiers and claim mappers:

1. Parse bearer token from request.
2. Determine provider by issuer (`iss`) and configured issuer allowlist.
3. Verify JWT signature and claims with provider-specific JWKS/audience settings.
4. Map provider claims to a unified `IdentityClaims` model.
5. Reuse existing RBAC and tenant scoping with `claims.sub` and normalized roles.

### Component Changes

- `backend/auth/models.py`
  - Introduce provider-neutral `IdentityClaims` model.
  - Keep compatibility alias for `Auth0Claims` during migration if needed.
- `backend/auth/jwt.py`
  - Split into provider-agnostic orchestration and provider-specific verification functions.
  - Add Cloudflare Access verifier using team-domain certs endpoint.
- `backend/auth/deps.py`
  - Depend on unified claims model.
- `backend/config.py`
  - Add provider-neutral auth settings plus Cloudflare-specific settings.
- `backend/security/headers.py`
  - Update CSP `connect-src` configuration to avoid hard-coded Auth0-only host.
- Tests
  - Add unit tests for issuer routing and Cloudflare token verification paths.
  - Keep existing Auth0 tests passing.

### Cross-Design Integration

This design integrates with [Design 001](001-local-mongodb-homelab.md) to keep auth and persistence changes aligned:

- Shared config surface in `backend/config.py`:
  - Auth provider selection (`AUTH_ALLOWED_ISSUERS`, provider-specific settings)
  - Store backend selection (`STORE_BACKEND`, Mongo settings)
- Auth persistence model compatibility:
  - Existing `auth0_sub` fields remain temporarily, but all new auth flows must treat `sub` as provider-neutral identity key.
  - When `STORE_BACKEND=mongodb`, user/audit writes continue through existing store interfaces without provider-specific branching in handlers.
- Rollout sequencing:
  - Land provider-neutral `IdentityClaims` and verifier routing first.
  - Enable Cloudflare Access in staging with `memory` backend.
  - Validate Cloudflare + MongoDB together in homelab profile before broader rollout.

### Data Model

```python
class IdentityClaims(BaseModel):
    sub: str
    email: EmailStr | None = None
    name: str | None = None
    roles: list[UserRole] = Field(default_factory=lambda: [UserRole.CLIENT])
    email_verified: bool = False
    iss: str
    aud: str | list[str]
    exp: int
    iat: int
    provider: Literal["auth0", "cloudflare_access"]
```

No database schema migration is required in this phase. Existing stored `auth0_sub` fields remain as-is, but follow-up work should rename this field to a provider-neutral key.

### API Changes

No external API contract changes are required. Protected endpoints continue to use bearer authentication and existing role guards.

Operational/config API changes (environment variables):

```
AUTH_ALLOWED_ISSUERS=auth0,cloudflare_access
AUTH0_DOMAIN=...
AUTH0_API_AUDIENCE=...
CLOUDFLARE_ACCESS_TEAM_DOMAIN=https://<team>.cloudflareaccess.com
CLOUDFLARE_ACCESS_AUDIENCE=<access-app-aud-tag>
```

### Key Flows

```
1. Client sends Authorization: Bearer <token>.
2. Backend decodes unverified token header/payload to inspect issuer.
3. Backend selects verifier based on issuer and configured providers.
4. Backend verifies signature + issuer + audience via provider JWKS/certs.
5. Backend maps claims to IdentityClaims and enforces RBAC.
6. Request proceeds with tenant scope owner_id = claims.sub.
```

### Error Handling

- Unknown or disallowed issuer: `401 Invalid or expired token`.
- Signature/key lookup failure: `401 Invalid or expired token`.
- Missing required claims (`sub`, `iss`, `aud`, `exp`): `401 Invalid or expired token`.
- Unsupported role values: ignore unknown roles and default to `client` when none valid.

## Alternatives Considered

### Alternative 1: Keep Auth0-only backend

Lowest short-term effort but preserves provider lock-in and blocks Cloudflare-first deployments.

### Alternative 2: Replace Auth0 entirely with Cloudflare Access

Simpler runtime path but too risky and restrictive. It would force migration for existing users and remove flexibility where Auth0 is a better CIAM fit.

## Security Considerations

- Enforce strict issuer and audience checks per provider.
- Validate JWTs against remote JWKS/certs with key rotation support.
- Do not trust role claims from unknown namespaces or unapproved issuers.
- Keep audit logging provider-aware by including normalized provider field.

## Performance Considerations

- Continue in-memory JWKS/certs caching with TTL.
- Add per-provider cache keys to avoid repeated remote key fetches.
- Keep verification path O(1) by issuer routing before deep validation.

## Testing Strategy

- Unit tests for issuer detection and verifier selection.
- Unit tests for Auth0 and Cloudflare token validation success/failure cases.
- Unit tests for role claim mapping and fallback role behavior.
- Integration tests for protected endpoint access across both providers.
- Manual testing against a Cloudflare Access-protected dev application.

## Migration / Rollout

1. Refactor to provider-neutral models while keeping Auth0 default enabled.
2. Add Cloudflare verification path behind config flag/issuer allowlist.
3. Deploy to staging and test Auth0 regression + Cloudflare login flow.
4. Validate Cloudflare + local MongoDB combination using [Design 001](001-local-mongodb-homelab.md) profile.
5. Enable in production for selected environments.
6. Follow-up: rename persistent `auth0_sub` fields to provider-neutral naming.

## Open Questions

- [ ] Should Cloudflare Access user groups map directly to `admin` role, or require explicit mapping config?
- [ ] Should we support multiple Cloudflare Access applications/audiences per environment?
- [ ] Do we need a frontend auth-provider selector now, or backend-only support first?

## References

- [Design 001: Local MongoDB Option for Homelab Deployments](001-local-mongodb-homelab.md)
- [Cloudflare Access identity providers](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/)
- [Cloudflare Access token validation](https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/)
- [Auth0 setup guide](../admin/auth0_setup.md)
