# Architecture

> Describes the architecture chosen for the system, the internal organization of the project, the path of a typical request through the layers and the boundaries that are consciously assumed.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Architectural Style and Principles](#architectural-style-and-principles)
- [Project Organization](#project-organization)
    - [Overall Structure](#overall-structure)
    - [Architecture Layers](#architecture-layers)
    - [Project Structure](#project-structure)
- [Typical Request Flow](#typical-request-flow)
- [Security and Multi-Tenancy](#security-and-multi-tenancy)
    - [Row-Level Security (RLS)](#row-level-security-rls)
    - [Connection Pool Hygiene](#connection-pool-hygiene)
    - [Controlled SECURITY DEFINER Boundaries](#controlled-security-definer-boundaries)
    - [Authentication and Token Boundaries](#authentication-and-token-boundaries)
- [Consistency, Concurrency and Events](#consistency-concurrency-and-events)
    - [Transaction Boundaries](#transaction-boundaries)
    - [Database-Enforced Invariants](#database-enforced-invariants)
    - [Locking and Idempotency](#locking-and-idempotency)
    - [Transactional Outbox](#transactional-outbox)
- [Observability and Health](#observability-and-health)
- [Failure Handling and Degradation](#failure-handling-and-degradation)
    - [Redis Unavailability Behavior](#redis-unavailability-behavior)
- [Known Boundaries and Assumptions](#known-boundaries-and-assumptions)

---

## Architecture Overview

Sturdy Parakeet is a **modular monolith** organized around explicit business modules. Each module is implemented with **hexagonal architecture (Ports & Adapters)** and **tactical Domain-Driven Design**, so the domain and application rules do not depend on FastAPI, SQLAlchemy, Redis, Celery or SMTP.

The modules are:

| Module          | Responsibility                                                                       |
|-----------------|--------------------------------------------------------------------------------------|
| `auth`          | Registration, email verification, login and access-token validation.                 |
| `complexes`     | Complex creation, memberships and invitations.                                       |
| `zones`         | Sports zones, operating hours, slot duration and zone status.                        |
| `bookings`      | Availability, booking creation, rescheduling and cancellation.                       |
| `notifications` | Asynchronous email delivery for verification, invitations and booking cancellations. |

A **shared kernel** provides cross-cutting infrastructure: configuration, database and Redis clients, logging, correlation IDs, response schemas and exception handling.

```text
┌────────────────────────────────────────────────────────────────────┐
│ Presentation / API                                                 │
│ FastAPI routers · Pydantic schemas · auth and rate-limit deps      │
├────────────────────────────────────────────────────────────────────┤
│ Application                                                        │
│ Use cases · Dtos                                                   │
├────────────────────────────────────────────────────────────────────┤
│ Domain                                                             │
│ Entities · value objects · policies · domain services · ports ·    │
│ unit of work                                                       │
├────────────────────────────────────────────────────────────────────┤
│ Infrastructure                                                     │
│ SQLAlchemy repositories · Redis · Celery · SMTP · security ·       │
│ Adapters                                                           │
└────────────────────────────────────────────────────────────────────┘
```

The synchronous write path is transactional. Side effects that do not need to block the response, such as sending an email, are recorded in the **transactional Outbox** and published after the commit:

```text
HTTP request
    │
    ▼
Module use case ──► Unit of Work ──► PostgreSQL transaction
    │                                   ├── business writes
    │                                   └── outbox_events row
    ▼
HTTP response

Outbox dispatcher ──► Celery / Redis broker ──► notification worker ──► SMTP
```

This keeps the API responsive while preserving the guarantee that no event is published for a transaction that was rolled back.

---

## Architectural Style and Principles

1. **The domain is independent.** Domain objects contain business invariants and time rules without importing framework or persistence code.
2. **Ports belong to the application.** Repositories, clocks, token signers, email senders and rate-limit stores are defined as interfaces owned by the use cases.
3. **Adapters live in infrastructure.** SQLAlchemy, Redis, Celery, SMTP and cryptographic implementations are replaceable adapters.
4. **Dependencies point inward.** Presentation depends on application; application depends on domain; infrastructure implements application ports; domain depends on nothing external.
5. **The database is the consistency authority.** Uniqueness, non-overlap, tenancy and referential integrity are enforced with PostgreSQL constraints, not only with in-memory checks.
6. **Tenant context is explicit.** Every tenant-scoped transaction sets `app.user_id` before querying, and RLS policies restrict rows by complex.
7. **Asynchronous delivery is at-least-once.** Outbox publication and email workers are designed to tolerate duplicates instead of pretending to provide exactly-once delivery.
8. **Failures are observable and boring.** Expected failures become typed domain errors mapped to stable HTTP responses; unexpected failures return a generic `500` and are logged with structured context.

---

## Project Organization

### Overall Structure

The codebase is divided into business modules under `src/modules` and a shared kernel under `src/shared`. Modules do not import each other's infrastructure or presentation layers. Cross-module collaboration happens through application ports, shared domain value objects or events.

### Architecture Layers

| Layer          | Contents                                                                                                   | Allowed dependencies                              |
|----------------|------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| Domain         | Entities, value objects, policies, domain services, domain errors, ports, unit-of-work contracts.          | Standard library only.                            |
| Application    | Use cases, DTOs, orchestration.                                                                            | Domain.                                           |
| Infrastructure | Repository implementations, transactions, Redis adapters, Celery tasks, SMTP clients, security primitives. | Application, domain, shared infrastructure.       |
| Presentation   | FastAPI routers, request/response schemas, dependencies, exception mapping.                                | Application, domain errors, shared API utilities. |

### Project Structure

```text
src/
├── main.py                         # FastAPI app, lifespan, middleware, handlers
├── config.py                       # Environment-backed settings
├── modules/
│   ├── auth/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── complexes/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── zones/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   ├── bookings/
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   └── notifications/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       └── presentation/
└── shared/
    ├── domain/
    ├── application/
    ├── infrastructure/
    │   ├── alembic/                # Migrations
    │   ├── models/                 # Shared SQLAlchemy base/model helpers
    │   ├── logging/                # Structlog configuration and wrapper
    │   ├── database.py             # Async engine, sessions and pool
    │   └── redis_client.py         # Async Redis client and pool
    └── presentation/
    │   ├── api/
    │   ├── exceptions/             # Global exception handlers
    │   ├── middleware/             # Correlation ID middleware
    │   └── schemas/                # Common response envelopes
```

The repository currently contains the shared kernel and the application bootstrap. The `modules/*` tree describes the target organization for the business capabilities defined in the requirements specification.

---

## Typical Request Flow

The following walkthrough uses `POST /api/v1/complexes/{complex_id}/zones/{zone_id}/bookings` as a representative write request.

1. **Uvicorn and FastAPI** receive the request. CORS is evaluated first, then `CorrelationIdMiddleware` reuses or generates `X-Correlation-ID`, binds it to the Structlog context and returns it in the response.
2. **Rate limiting** runs after optional authentication. It builds a policy key from the user ID, the SHA-256 hash of the normalized email, or the client IP. The counter increment and TTL assignment are executed atomically in Redis. If Redis is unavailable, the request follows the fail-open behavior described below.
3. **Authentication** validates the bearer token: signature, `exp`, `iss`, `aud` and `type = "access"`. The user identity comes only from the token's `sub`; no identity is accepted from the body.
4. **Input validation** runs in the presentation layer. Additional fields, wrong types, invalid identifiers, missing time zones and malformed timestamps are rejected before the use case starts.
5. **The use case** opens a unit of work and a database transaction. The transaction sets the RLS context (`app.user_id`) before any tenant-scoped query.
6. **Repositories** load the complex, zone, operating hours and policies through RLS-protected queries. The use case resolves the local slot, applies advance-notice and policy rules, and checks idempotency.
7. **Concurrency control** is delegated to PostgreSQL: the zone row is locked with `FOR SHARE`, an advisory transaction lock protects the per-client limit, and the exclusion constraint on `(zone_id, tstzrange(starts_at, ends_at))` prevents overlap. A `SECURITY DEFINER` trigger verifies that the zone is still `ACTIVE` at insert time.
8. **Business writes and Outbox rows** are committed in the same transaction. A booking by a client does not publish an event; a staff cancellation inserts `booking.cancelled` in the same transaction as the status update.
9. **The response** is mapped from the domain result. Domain errors become the documented HTTP status and error code; unexpected errors are logged by the global handler and returned as a generic `500` without internals.
10. **After the commit**, the Outbox dispatcher selects pending rows with `FOR UPDATE SKIP LOCKED`, publishes them to the Celery/Redis broker, marks them `PUBLISHED` on success and applies backoff on failure. Notification workers consume the events and send emails.

---

## Security and Multi-Tenancy

### Row-Level Security (RLS)

Tenant isolation is enforced in PostgreSQL with Row-Level Security. Every tenant-scoped transaction must set `app.user_id` before querying; policies compare that value against memberships and ownership.

- `users` is a global table and has no per-complex RLS.
- Complex-owned tables include `complex_id` in their policies.
- Staff can only read and write data for complexes where they have an `ACTIVE` membership with the required role.
- Clients only see and create their own bookings.
- The catalog and availability queries expose only public columns and active zones.
- Client data used by staff is read through a restricted view (`complex_booking_clients`) rather than through direct access to `users`.

RLS is a defense-in-depth control. The application also filters by tenant and user, so a query is safe only when both layers agree.

### Connection Pool Hygiene

`app.user_id` is transaction-local. It must be set with transaction scope (`SET LOCAL`) and must not leak to the next request that reuses the same pooled connection.

- The context is established when the unit of work starts.
- The context is cleared or rolled back with the transaction.
- No session-level setting survives a returned connection.
- Integration tests explicitly reuse a pooled connection across two users and assert that the second user cannot see the first user's rows.

### Controlled SECURITY DEFINER Boundaries

Two operations cannot rely on ordinary RLS because the user is not yet a member of the complex or because the check must run inside a trigger:

- Accepting an invitation.
- Validating that a booking is created or updated only on an `ACTIVE` zone.

These functions are narrowly scoped, use a fixed `search_path = pg_catalog, public`, do not use dynamic SQL and expose only the minimum required behavior. They are treated as security-sensitive code and require dedicated tests.

### Authentication and Token Boundaries

- Passwords are stored only as Argon2id hashes with a per-user salt. Plaintext passwords never reach storage, logs, responses or traces.
- Access tokens are JWTs signed with `HS256`. Protected endpoints validate signature, expiration, issuer, audience and token type.
- Email verification and invitation tokens are HMAC-SHA256 signed, compared in constant time, kept only in memory when needed and never persisted or returned.
- Rate-limit keys for email-based policies use the SHA-256 hash of the normalized email, never the plaintext address.
- Logs redact passwords, hashes, access tokens, invitation tokens, verification tokens and unnecessary personal data.

---

## Consistency, Concurrency and Events

### Transaction Boundaries

Each use case defines a single unit of work. Multi-row operations that must be all-or-nothing run in one transaction:

- Registration plus the verification-email Outbox row.
- Complex creation plus the owner membership plus booking policies.
- Invitation creation plus the invitation Outbox row.
- Invitation acceptance plus membership creation or reactivation.
- Booking creation, rescheduling and cancellation.
- Staff cancellation plus the `booking.cancelled` Outbox row.

The API never publishes an event before the business transaction commits.

### Database-Enforced Invariants

The database is responsible for the invariants that must survive concurrent requests and multiple API instances:

| Invariant                                    | Mechanism                                                                    |
|----------------------------------------------|------------------------------------------------------------------------------|
| Unique user email                            | `UNIQUE` constraint on the normalized email.                                 |
| Unique complex slug                          | `UNIQUE` constraint on `slug`.                                               |
| Unique zone name per complex                 | Unique index on `(complex_id, lower(name))`.                                 |
| One membership per user and complex          | `UNIQUE (complex_id, user_id)`.                                              |
| One pending invitation per email and complex | Partial unique index on `(complex_id, email)` where `status = 'PENDING'`.    |
| No overlapping operating windows             | `EXCLUDE USING gist` with `int4range(..., '[)')` and `btree_gist`.           |
| No overlapping bookings                      | `EXCLUDE USING gist` with `tstzrange(..., '[)')` for non-cancelled bookings. |
| Valid booking interval                       | `CHECK (ends_at > starts_at)`.                                               |
| Tenant consistency of child rows             | Composite foreign keys such as `(zone_id, complex_id)`.                      |
| Non-empty booking window                     | `CHECK (min_advance_minutes < max_advance_days * 1440)`.                     |

The half-open `[start, end)` interval is deliberate: it allows contiguous bookings and operating windows while still rejecting real overlaps.

### Locking and Idempotency

- Zone status changes lock the zone with `FOR UPDATE`.
- Booking creation and rescheduling lock the zone with `FOR SHARE` through the trigger, so a booking cannot be confirmed while the zone is being deactivated.
- The per-client active-booking limit is protected with `pg_advisory_xact_lock` on the `(client_id, complex_id)` pair.
- Invitation acceptance uses `SELECT ... FOR UPDATE` or a conditional update guarded by `status = 'PENDING'`.
- Cancellation and rescheduling use conditional updates that re-check the current status, so only one concurrent operation wins.
- Locks are acquired in a stable order (zones before bookings) to reduce deadlocks; a detected deadlock is retried once.
- Idempotency is explicit: retrying the same booking returns the existing equivalent booking, a duplicate registration returns `409`, and a duplicate pending invitation returns `409`.

### Transactional Outbox

`outbox_events` is written in the same transaction as the business change. A dispatcher publishes events after the commit:

- Pending rows are selected with `FOR UPDATE SKIP LOCKED`, so multiple dispatchers do not process the same row.
- `next_attempt_at` enables exponential backoff and recovery of stuck events.
- `attempts` and `last_error` provide traceability without sensitive data.
- After the configured retries, the event is marked `FAILED`.
- Delivery is at-least-once. Consumers must tolerate duplicates; notification tasks therefore check the current database state and produce idempotent email content.

If the process crashes after the commit and before publishing, the event remains in `outbox_events` and is recovered by the dispatcher.

---

## Observability and Health

- **Structured logs:** Structlog emits JSON with timestamp, level, logger name and context.
- **Correlation:** `X-Correlation-ID` is accepted or generated per request, bound to the logging context and returned to the caller.
- **Request context:** logs include method, route, status, duration, `user_id`, `complex_id`, `zone_id` or `booking_id` when applicable.
- **Sensitive data:** passwords, hashes, tokens, credentials, raw email addresses and unnecessary personal data are never logged.
- **Unexpected errors:** the global exception handler logs the exception with its type and message but returns only a generic `500` response without stack traces or internal details.
- **Liveness:** `/health` confirms that the process is serving. It deliberately does not touch PostgreSQL or Redis, so a dependency outage does not cause unnecessary restarts.
- **Readiness:** `/health/ready` reports whether PostgreSQL and Redis are reachable and returns `503` when a dependency is down, so orchestrators can stop routing new traffic to an unhealthy instance. This is an orchestration signal; it is separate from the per-request rate-limit decision described below.

---

## Failure Handling and Degradation

The system distinguishes between failures that affect correctness and failures that affect only protection or side effects.

- **PostgreSQL unavailable:** the request fails with a `5xx` response. No business invariant can be guaranteed without the database.
- **Redis unavailable:** the request continues. Redis is used for rate limiting, not as the source of truth for bookings or tenancy.
- **Outbox dispatcher or broker unavailable:** the business transaction still commits and the event stays pending until it is published.
- **SMTP unavailable:** the notification task retries with backoff according to the email rules; the business operation is not rolled back.

### Redis Unavailability Behavior

- `fail-open` is adopted for every MVP operation, including authentication, invitations, bookings and staff operations: if Redis does not respond, the request continues without applying the limit.
- The accepted risk is that, during the outage, rate limiting is temporarily disabled and a client could issue more requests than allowed. `fail-closed` is not implemented, and writes are not blocked for this reason in the MVP.
- Every degradation is logged with the `request_id`, policy, subject and cause, without tokens, credentials or personal data; it is not logged as if the limit had been applied.
- The response during the outage does not include headers indicating that the limit was evaluated correctly.
- The counter increment and its TTL assignment run in a single atomic operation (a Lua script through `EVAL`/`EVALSHA` or `MULTI/EXEC`), so a failure between both commands does not leave a key without an expiration.
- If the atomic operation does not complete, the counter is neither created nor modified; the request follows the `fail-open` behavior and the degradation is logged.

Redis is an abuse-control dependency, not a correctness dependency. During a Redis outage, availability and booking consistency continue to rely exclusively on PostgreSQL constraints, locks and transactions. The `subject` recorded in the degradation log is a non-sensitive identifier: a user ID, an email hash or an IP address. Raw emails, tokens and credentials are never written.

---

## Known Boundaries and Assumptions

- **Modular monolith, not microservices.** Modules are separated by code boundaries and transactions, not by network calls. A future split would require extracting modules and revisiting distributed consistency.
- **Single primary database.** The MVP assumes one PostgreSQL primary and one Redis deployment. Cross-region replication, failover orchestration and multi-primary writes are out of scope.
- **At-least-once events.** Outbox publication and email delivery may duplicate. Consumers tolerate duplicates and emails carry idempotent content; this is documented rather than hidden.
- **Rate limiting is not guaranteed during a Redis outage.** This is the explicit fail-open trade-off described above.
- **No refresh tokens or token revocation list.** Access tokens are valid until they expire; logout and immediate global revocation are not part of the MVP.
- **Expired invitations are persisted on demand.** There is no scheduler whose only job is to expire invitations; US-105, US-106 and US-108 update expired rows when they process them.
- **Zone deactivation does not cancel bookings.** Future and in-progress bookings keep their interval and status; staff must cancel them explicitly through US-408.
- **Schedule changes are not retroactive.** Existing bookings keep `starts_at` and `ends_at`; availability for new bookings always uses the current schedule.
- **Real PostgreSQL is required for critical tests.** SQLite cannot reproduce RLS, exclusion constraints, advisory locks, `FOR UPDATE SKIP LOCKED` or the Outbox recovery behavior.
- **Coverage target alignment is pending.** The normative requirement is 80%, while the current automation enforces 70%; the test strategy documents the target and the required follow-up.
- **No horizontal write scaling beyond PostgreSQL coordination.** Correctness relies on database constraints and locks; the API is stateless enough to run multiple instances, but every instance shares the same primary database.
