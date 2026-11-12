# Technical Decisions

> Collects the technical and architectural decisions adopted for the system, expressed through Architecture Decision Records (ADR), documenting the context, the alternatives evaluated, the decision made, the trade-offs assumed and the possible future evolution.

---

## ADR-001: Adopt Vertical Slice Architecture over Hexagonal Architecture

- **Status:** Accepted
- **Date:** 2026-11-12

### Context

The initial architecture was a modular monolith implemented with hexagonal architecture (Ports & Adapters) and tactical Domain-Driven Design. Every new feature had to follow a rigid flow that crossed several technical layers: domain entities and value objects, application use cases and DTOs, ports, infrastructure adapters, presentation routers and schemas, plus the corresponding tests.

That structure provided strong separation of concerns, but it also introduced a high amount of ceremony and bureaucracy for each feature. A single use case required touching many files and respecting a very specific pattern before it could deliver value. As the number of business capabilities grew, this overhead slowed down the development flow and made small changes more expensive than necessary.

The team still wants a modular monolith with explicit business boundaries and database-enforced consistency, but it needs a structure that gives more freedom when adding a new feature and reduces the number of files involved in a typical change.

### Alternatives Considered

1. **Keep hexagonal architecture.** Preserve the existing Ports & Adapters layout and continue enforcing the layer-by-layer flow. This maintains strict boundaries, but keeps the high ceremony that slows down feature delivery.
2. **Adopt a classic layered architecture.** Organize code into controllers, services, repositories and models. This is simpler than hexagonal, but it still spreads each feature across horizontal layers and tends to produce large, generic services and repositories.
3. **Adopt Vertical Slice Architecture.** Organize each use case as an independent slice that contains its own route, schemas, orchestration, business rules, persistence and errors. Cross-cutting concerns remain in a shared kernel.

### Decision

Adopt **Vertical Slice Architecture** for the business modules.

Each use case becomes a slice under `src/modules/<module>/<use_case>/`, with its own `router.py`, `schemas.py`, `service.py`, `repository.py` and `errors.py`. Code that several slices of the same module genuinely share lives directly in the module folder, without a nested `shared/` directory. Cross-cutting infrastructure remains in the global `src/shared/` kernel, organized by capability: `database`, `redis`, `logging`, `security`, `outbox`, `exceptions`, `middleware`, `dependencies` and `schemas`.

The main reason for the change is development speed: a new feature is implemented in one place, with fewer files and fewer mandatory abstractions, instead of following a predefined layer-by-layer ceremony.

The trade-offs are accepted explicitly:

- Slices may duplicate small queries, validation or mapping code to stay independent.
- Boundaries are enforced by conventions and dependency rules rather than by a rigid folder hierarchy.
- Shared abstractions are introduced only when reuse is proven, which delays some refactors but avoids premature coupling.
- Tactical DDD concepts remain useful inside a slice, but they are no longer organized as horizontal layers.

### Future Evolution

- Extract code into the module folder or the shared kernel only when reuse is demonstrated by real slices.
- If a module grows too large or its slices become tightly coupled, evaluate splitting it into a separate module or service.
- Revisit this decision if duplication becomes unmanageable or if the team needs stronger architectural enforcement.
- Keep the transactional Outbox, PostgreSQL constraints and RLS as the correctness guarantees; the architectural change does not relax consistency or multi-tenancy.
