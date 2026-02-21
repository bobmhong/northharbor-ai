# Design: [Feature Name]

**Status:** Draft | In Review | Approved | Implemented | Superseded | Rejected  
**Author:** @username  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD  

## Summary

One paragraph summary of what this design proposes.

## Motivation

Why are we doing this? What problem does it solve? What use cases does it enable?

## Goals

- Goal 1
- Goal 2
- Goal 3

## Non-Goals

What is explicitly out of scope for this design?

- Non-goal 1
- Non-goal 2

## Detailed Design

### Overview

High-level description of the approach.

### Component Changes

What components are affected? What new components are needed?

### Data Model

Describe any data model changes (schemas, types, etc.).

```python
# Example schema
class ExampleModel:
    field1: str
    field2: int
```

### API Changes

Describe any API changes (endpoints, request/response formats).

```
POST /api/v1/example
Request: { ... }
Response: { ... }
```

### Key Flows

Describe the main flows or sequences.

```
1. User does X
2. System does Y
3. Result is Z
```

### Error Handling

How are errors handled? What failure modes exist?

## Alternatives Considered

### Alternative 1: [Name]

Description of the alternative and why it was not chosen.

### Alternative 2: [Name]

Description of the alternative and why it was not chosen.

## Security Considerations

Are there any security implications? How are they addressed?

## Performance Considerations

Are there any performance implications? How are they addressed?

## Testing Strategy

How will this be tested?

- Unit tests
- Integration tests
- Manual testing

## Migration / Rollout

How will this be deployed? Any migration steps needed?

## Open Questions

- [ ] Question 1
- [ ] Question 2

## References

- Link to related issues
- Link to related designs
- External documentation
