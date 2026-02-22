# Design: Async MongoDB Stores for Plans and Sessions

**Status:** Draft  
**Author:** @bobmhong  
**Created:** 2026-02-21  
**Updated:** 2026-02-21  

## Summary

Migrate plan and session persistence from the current `runtime_state.json` flat file to MongoDB using the Motor async driver. This also retrofits the existing synchronous PyMongo stores (`MongoDBUserProfileStore`, `MongoDBAuditStore`, `MongoLLMAnalyticsStore`) to use Motor, adds optimistic concurrency control on plan writes, and provides targeted (partial) updates for high-frequency status and field changes.

## Motivation

Plans and sessions are currently persisted via a single JSON file (`.data/runtime_state.json`). Every call to `store_plan()` or `store_session()` serializes the entire plan and session corpus to disk. This approach has caused concrete problems:

- **Stale data on schema evolution** — Plans persisted before a code change load with old values. A status field (`intake_in_progress`) remained stale after the status-update logic was introduced because the data was loaded from a file written by older code.
- **No atomic writes** — A crash or concurrent request mid-write can corrupt the file.
- **O(n) serialization on every write** — Every single-field update serializes all plans and sessions.
- **No query capability** — `list_plans()` loads everything into memory and filters in Python.

Separately, the existing MongoDB stores use synchronous PyMongo inside `async def` methods, blocking the FastAPI event loop. This must be fixed before adding more MongoDB-backed stores.

## Goals

- Replace `runtime_state.json` with MongoDB-backed plan and session stores.
- Use Motor (async MongoDB driver) to avoid blocking the event loop.
- Retrofit existing PyMongo stores to use Motor.
- Add optimistic concurrency control (`version` field) on plan writes.
- Support targeted updates (`$set` on specific paths) for status changes and field edits.
- Preserve the in-memory backend option for tests and fast development (per design 001).
- Migrate existing `runtime_state.json` data on first startup with the new backend.

## Non-Goals

- Changing the `CanonicalPlanSchema` Pydantic model structure beyond adding a `version` field.
- Multi-collection transactions or cross-document consistency guarantees.
- Sharding or replica set configuration.
- Replacing the in-memory store for tests.

## Detailed Design

### Overview

```
                 ┌─────────────────────────────┐
                 │    Store Protocol Layer      │
                 │  PlanStore / SessionStore    │
                 └─────────┬───────────────────┘
                           │
              ┌────────────┼────────────────┐
              ▼                             ▼
   ┌──────────────────┐         ┌───────────────────────┐
   │ InMemoryPlanStore │         │  MongoPlanStore        │
   │ InMemorySessionSt │         │  MongoSessionStore     │
   │ (dev / tests)     │         │  (Motor async driver)  │
   └──────────────────┘         └───────────────────────┘
```

The store layer is selected at startup via `STORE_BACKEND` (per design 001). All stores expose `async` methods. In-memory stores are trivially async. Motor stores use the async MongoDB driver natively.

### Component Changes

#### `backend/config.py`

Add `store_backend` setting (already planned in design 001):

```python
store_backend: Literal["memory", "mongodb"] = "memory"
```

#### `backend/requirements.txt`

Add Motor alongside PyMongo:

```
motor>=3.3
```

Motor depends on PyMongo, so `pymongo[srv]>=4.6` stays for its type definitions and BSON support.

#### `backend/stores/protocols.py` (new)

Define abstract protocols for plan and session stores:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PlanStore(Protocol):
    async def get(self, plan_id: str) -> CanonicalPlanSchema | None: ...
    async def save(self, plan: CanonicalPlanSchema) -> None: ...
    async def list_by_owner(self, owner_id: str) -> list[CanonicalPlanSchema]: ...
    async def delete(self, plan_id: str) -> bool: ...
    async def update_fields(
        self, plan_id: str, updates: dict[str, Any], expected_version: int | None = None
    ) -> CanonicalPlanSchema | None: ...

@runtime_checkable
class SessionStore(Protocol):
    async def get(self, session_id: str) -> SessionDocument | None: ...
    async def save(self, session: SessionDocument) -> None: ...
    async def get_for_plan(self, plan_id: str) -> SessionDocument | None: ...
    async def delete_for_plan(self, plan_id: str) -> int: ...
```

#### `backend/stores/memory.py` (new)

In-memory implementations of `PlanStore` and `SessionStore`, replacing the current dict globals in `deps.py`. These wrap the existing logic but conform to the protocol.

#### `backend/stores/mongo_plans.py` (new)

Motor-based `MongoPlanStore`:

```python
from motor.motor_asyncio import AsyncIOMotorDatabase

class MongoPlanStore:
    COLLECTION = "plans"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    async def get(self, plan_id: str) -> CanonicalPlanSchema | None:
        doc = await self._col.find_one({"plan_id": plan_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return CanonicalPlanSchema.model_validate(doc)

    async def save(self, plan: CanonicalPlanSchema) -> None:
        data = plan.model_dump(mode="json")
        data["version"] = plan.version
        await self._col.update_one(
            {"plan_id": plan.plan_id},
            {"$set": data},
            upsert=True,
        )

    async def update_fields(
        self, plan_id: str, updates: dict[str, Any], expected_version: int | None = None
    ) -> CanonicalPlanSchema | None:
        query: dict[str, Any] = {"plan_id": plan_id}
        if expected_version is not None:
            query["version"] = expected_version
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await self._col.find_one_and_update(
            query,
            {"$set": updates, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            return None
        result.pop("_id", None)
        return CanonicalPlanSchema.model_validate(result)

    async def list_by_owner(self, owner_id: str) -> list[CanonicalPlanSchema]:
        plans = []
        async for doc in self._col.find({"owner_id": owner_id}):
            doc.pop("_id", None)
            plans.append(CanonicalPlanSchema.model_validate(doc))
        return plans

    async def delete(self, plan_id: str) -> bool:
        result = await self._col.delete_one({"plan_id": plan_id})
        return result.deleted_count > 0

    def ensure_indexes(self) -> None:
        self._col.create_index("plan_id", unique=True)
        self._col.create_index("owner_id")
        self._col.create_index([("owner_id", 1), ("status", 1)])
```

#### `backend/stores/mongo_sessions.py` (new)

Motor-based `MongoSessionStore`. Sessions are stored as serializable documents (not live `InterviewSession` objects, which hold an `LLMClient` reference):

```python
class SessionDocument(BaseModel):
    session_id: str
    plan_id: str
    model: str
    history: list[dict[str, Any]]
    created_at: datetime

class MongoSessionStore:
    COLLECTION = "sessions"

    async def get(self, session_id: str) -> SessionDocument | None: ...
    async def save(self, session: SessionDocument) -> None: ...
    async def get_for_plan(self, plan_id: str) -> SessionDocument | None:
        doc = await self._col.find_one(
            {"plan_id": plan_id},
            sort=[("created_at", -1)],
        )
        ...
    async def delete_for_plan(self, plan_id: str) -> int:
        result = await self._col.delete_many({"plan_id": plan_id})
        return result.deleted_count
```

Indexes: `session_id` (unique), `plan_id`, `created_at`.

#### `backend/api/deps.py`

- Remove `_plans`, `_sessions`, `_runtime_loaded`, `_RUNTIME_STATE_PATH`, `_ensure_runtime_loaded()`, `_persist_runtime_state()`.
- Replace `get_plan()`, `store_plan()`, `list_plans()`, `delete_plan()`, `get_session()`, `store_session()`, `get_session_for_plan()` with thin wrappers that delegate to the active `PlanStore` / `SessionStore` instance.
- The active store is initialized at startup based on `STORE_BACKEND`.

```python
_plan_store: PlanStore | None = None
_session_store: SessionStore | None = None

def get_plan_store() -> PlanStore:
    assert _plan_store is not None
    return _plan_store

def init_stores(settings: Settings) -> None:
    global _plan_store, _session_store
    if settings.store_backend == "mongodb":
        db = get_motor_database()
        _plan_store = MongoPlanStore(db)
        _session_store = MongoSessionStore(db)
    else:
        _plan_store = InMemoryPlanStore()
        _session_store = InMemorySessionStore()
```

#### Existing PyMongo stores retrofit

`MongoDBUserProfileStore`, `MongoDBAuditStore`, and `MongoLLMAnalyticsStore` are updated to accept a Motor `AsyncIOMotorDatabase` and use `await` on all collection operations. The method signatures stay the same (already `async def`), so callers don't change.

### Data Model

#### `CanonicalPlanSchema` — add `version` field

```python
class CanonicalPlanSchema(BaseModel):
    # ... existing fields ...
    version: int = 1
```

The `version` field enables optimistic concurrency. It is incremented atomically by `$inc` on every write. Callers performing read-modify-write pass their known version; if it doesn't match, the write is rejected with a conflict error.

#### MongoDB collection: `plans`

```json
{
  "_id": ObjectId,
  "plan_id": "uuid-string",
  "owner_id": "anonymous",
  "version": 3,
  "status": "intake_complete",
  "schema_version": "1.0",
  "scenario_name": "Default",
  "created_at": "2026-02-21T...",
  "updated_at": "2026-02-21T...",
  "client": { "name": { "value": "Bob", "confidence": 1.0, ... }, ... },
  ...
}
```

Indexes: `plan_id` (unique), `owner_id`, compound `(owner_id, status)`.

#### MongoDB collection: `sessions`

```json
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "plan_id": "uuid-string",
  "model": "gpt-4o-mini",
  "history": [ { "role": "user", "content": "...", "timestamp": "..." }, ... ],
  "created_at": "2026-02-21T..."
}
```

Indexes: `session_id` (unique), `plan_id`, `created_at`.

#### MongoDB collection: `snapshots`

Existing `MemorySnapshotStore` is also migrated to a `MongoSnapshotStore`:

```json
{
  "_id": ObjectId,
  "snapshot_id": "sha256-hex",
  "plan_id": "uuid-string",
  "owner_id": "anonymous",
  "schema_version": "1.0",
  "data": { ... },
  "created_at": "2026-02-21T..."
}
```

Indexes: `snapshot_id` (unique), compound `(plan_id, owner_id, created_at)`.

### API Changes

No external API contract changes. All endpoints continue to accept and return the same request/response shapes. The only observable difference is data durability across restarts.

Internal signature changes:

- `store_plan()`, `get_plan()`, etc. in `deps.py` become `async`. Callers in `interview/router.py` and `pipelines/router.py` already run inside `async def` endpoint handlers, so adding `await` is straightforward.
- `_reconcile_stale_statuses()` in `pipelines/router.py` is removed — the staleness bug it worked around no longer exists when the source of truth is the database, not a file loaded at startup.

### Key Flows

#### Plan save (full document)

```
1. Caller modifies plan in memory
2. Caller calls await plan_store.save(plan)
3. MongoPlanStore serializes plan via model_dump()
4. Upsert with {"plan_id": plan.plan_id}, $set full document
5. Single document write, acknowledged
```

#### Plan update (targeted fields)

```
1. Caller identifies changed fields (e.g. status change, field edit)
2. Caller calls await plan_store.update_fields(plan_id, {"status": "intake_complete"}, expected_version=3)
3. MongoPlanStore issues find_one_and_update with version guard
4. MongoDB atomically checks version, applies $set, and $inc version
5. Returns updated document or None (version conflict)
```

#### Session hydration

```
1. Router calls await session_store.get(session_id)
2. MongoSessionStore returns SessionDocument (data only)
3. Router reconstructs InterviewSession from SessionDocument + live LLMClient
4. InterviewSession is used for the request, then saved back
```

### Error Handling

| Scenario | Behavior |
|---|---|
| Version conflict on `update_fields` | Return `None`, caller retries or returns 409 Conflict |
| Plan not found | Return `None`, caller returns 404 |
| MongoDB unreachable at startup | Fail fast with actionable error message |
| MongoDB unreachable at runtime | Motor raises `ServerSelectionTimeoutError`, caught and returned as 503 |
| Malformed document in DB | `model_validate` raises `ValidationError`, logged and skipped |

## Alternatives Considered

### Alternative 1: Keep PyMongo with `asyncio.to_thread()` wrappers

Wrapping every synchronous PyMongo call in `asyncio.to_thread()` avoids importing a new driver. However, this adds boilerplate to every method, doesn't benefit from Motor's connection pooling optimizations, and is considered a stopgap by the PyMongo maintainers. Motor is the officially recommended async driver and shares the same BSON/type infrastructure as PyMongo.

### Alternative 2: SQLite for local persistence

SQLite avoids the MongoDB dependency entirely and works well for single-process apps. However, `CanonicalPlanSchema` is a deeply nested document with optional sub-models and `ProvenanceField` wrappers — this maps naturally to a document store but would require significant flattening or JSON-column workarounds in SQL. The project also already has MongoDB infrastructure, Docker Compose services, and connection configuration in place.

### Alternative 3: Drop persistence entirely (pure in-memory)

Removing `runtime_state.json` and keeping only in-memory dicts eliminates all staleness and corruption bugs. This is viable for development but doesn't address the homelab persistence requirement from design 001.

## Security Considerations

- Plan documents contain personal financial data (income, balances, SSA estimates). MongoDB access should be restricted to the application process. The `mongodb_uri` with credentials should be in `.env`, never committed.
- `owner_id` filtering on all queries enforces tenant isolation at the application layer. A future enhancement could add MongoDB field-level encryption for PII fields.
- Session history contains user messages which may include sensitive information. Same access controls apply.

## Performance Considerations

- **Write frequency**: During an interview, `store_plan()` and `store_session()` are called on every user message (~10-15 times per interview). With Motor, each is a single async upsert — well within MongoDB's throughput capabilities. The current approach writes the entire corpus each time, so this is a net improvement.
- **Full vs. partial updates**: Status changes and single-field edits via Quick Review use `update_fields()` with targeted `$set`, avoiding full document serialization. Full `save()` is reserved for interview responses where many fields may change.
- **Read patterns**: `list_by_owner()` with an index on `owner_id` replaces the current Python list filter. `get()` on `plan_id` is an indexed unique lookup.
- **Connection pooling**: Motor's `AsyncIOMotorClient` maintains a connection pool (default 100 connections). A single shared client instance is sufficient for the expected load.
- **Document size**: A fully populated `CanonicalPlanSchema` serializes to ~3-5KB JSON. Sessions with full interview history reach ~10-20KB. Both are well under MongoDB's 16MB document limit.

## Testing Strategy

- **Unit tests**: In-memory store implementations tested directly (no MongoDB dependency). Validates protocol compliance, version increment logic, conflict detection.
- **Integration tests**: Motor stores tested against a real MongoDB instance (Docker). Validates upsert behavior, index creation, version conflicts, and `find_one_and_update` atomicity.
- **Existing test compatibility**: All existing tests that use `store_plan()` / `get_plan()` continue to work unchanged against the in-memory backend. No test requires MongoDB unless it explicitly opts in.
- **Migration test**: Validate that a `runtime_state.json` file is correctly imported into MongoDB on first startup with `STORE_BACKEND=mongodb`.

## Migration / Rollout

### Phase 1: Driver and protocol layer

1. Add `motor>=3.3` to `backend/requirements.txt`.
2. Create `stores/protocols.py` with `PlanStore` and `SessionStore` protocols.
3. Create `stores/memory.py` with in-memory implementations extracted from current `deps.py` globals.
4. Retrofit existing PyMongo stores to use Motor `AsyncIOMotorDatabase`.
5. Wire up `init_stores()` in app startup.
6. Default `STORE_BACKEND=memory` — no behavior change for existing users.

### Phase 2: MongoDB plan and session stores

1. Create `stores/mongo_plans.py` and `stores/mongo_sessions.py`.
2. Add `version` field to `CanonicalPlanSchema` (default `1`).
3. Add `MongoSnapshotStore` for snapshots.
4. Update `deps.py` to route through store instances.
5. Make `store_plan()`, `get_plan()`, etc. async; add `await` at call sites.
6. Remove `_persist_runtime_state()`, `_ensure_runtime_loaded()`, and `_reconcile_stale_statuses()`.

### Phase 3: Data migration and cleanup

1. Add one-time migration: on startup with `STORE_BACKEND=mongodb`, if `runtime_state.json` exists, import its plans and sessions into MongoDB, then rename the file to `.data/runtime_state.json.migrated`.
2. Remove JSON file read/write code from `deps.py`.
3. Update `docs/admin/` with MongoDB operational guidance (per design 001).

## Open Questions

- [ ] Should `update_fields` accept dot-notation paths for nested ProvenanceField values (e.g., `client.name.value`), or should it always replace the entire ProvenanceField object at the section level?
- [ ] Should the version conflict on `update_fields` return a 409 to the client, or silently re-read and retry once?
- [ ] Should sessions be stored indefinitely or have a TTL? An interview session for a completed plan may never be needed again, but retaining history supports the "resume" flow.
- [ ] Should the Motor client be initialized lazily (first use) or eagerly (app startup)? Eager is safer for fail-fast behavior; lazy avoids slowing startup when MongoDB isn't needed.

## References

- [Design 001: Local MongoDB Option for Homelab Deployments](001-local-mongodb-homelab.md) — establishes `STORE_BACKEND` selection and Docker Compose infrastructure
- [Motor documentation](https://motor.readthedocs.io/en/stable/) — official async MongoDB driver for Python
- [MongoDB `findOneAndUpdate`](https://www.mongodb.com/docs/manual/reference/method/db.collection.findOneAndUpdate/) — atomic conditional update used for optimistic concurrency
- Existing stores: `backend/stores/mongodb.py`, `backend/analytics/store.py`
- Existing deps: `backend/api/deps.py`
- Schema: `backend/schema/canonical.py`, `backend/schema/provenance.py`
