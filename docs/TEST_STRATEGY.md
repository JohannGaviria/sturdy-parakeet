# Test Strategy

> Defines the test levels applied to the project (unit, integration and end-to-end), their organization, the coverage target and the available commands to run them.

## Table of Contents

- [Overall Approach](#overall-approach)
- [Test Organization](#test-organization)
    - [Directory Layout](#directory-layout)
    - [Naming, Markers and Selection](#naming-markers-and-selection)
    - [Unit Tests](#unit-tests)
    - [Integration Tests](#integration-tests)
    - [End-to-End (E2E) Tests](#end-to-end-e2e-tests)
- [Critical Test Infrastructure](#critical-test-infrastructure)
    - [Real PostgreSQL Requirement](#real-postgresql-requirement)
    - [Redis and Degradation Tests](#redis-and-degradation-tests)
    - [Concurrency, Time and Isolation](#concurrency-time-and-isolation)
    - [Outbox and Notification Tests](#outbox-and-notification-tests)
- [Acceptance Test Suites](#acceptance-test-suites)
    - [P0 Acceptance Tests](#p0-acceptance-tests)
    - [P1 Acceptance Tests](#p1-acceptance-tests)
- [Coverage Target](#coverage-target)
- [Running the Tests](#running-the-tests)
    - [Tests with Docker (recommended)](#tests-with-docker-recommended)
    - [Tests without Docker (unit tests only)](#tests-without-docker-unit-tests-only)
    - [Combining the coverage reports](#combining-the-coverage-reports)
- [Continuous Integration](#continuous-integration)

---

## Overall Approach

The suite follows a practical test pyramid:

- **Many unit tests** cover domain rules, use-case orchestration and edge cases without external services.
- **Focused integration tests** verify the guarantees that only a real PostgreSQL and Redis can provide.
- **A smaller set of end-to-end tests** exercises complete HTTP flows through the application and its real dependencies.

The split is driven by the failure modes of this system, not by a desire for a specific ratio. Multi-tenant isolation, concurrency, exclusion constraints, Outbox recovery and daylight saving time behavior cannot be trusted to mocks or to SQLite. Those tests run against a **real PostgreSQL** instance from the dedicated test profile. Redis-backed rate limiting, TTL atomicity and fail-open behavior run against a **real Redis** instance.

The principles are:

1. Test behavior at the boundary that owns it.
2. Use real infrastructure for persistence, RLS, locking and event delivery.
3. Keep every test deterministic and isolated; no test depends on execution order or on data left by another test.
4. Prefer injected clocks and explicit fixtures over `sleep` and wall-clock assumptions.
5. Treat acceptance tests as release gates, not as documentation-only checklists.

---

## Test Organization

### Directory Layout

```text
tests/
├── conftest.py                 # Shared fixtures and db-test selection policy
├── helpers.py                  # Reachability helpers for test services
├── unit/                       # No PostgreSQL, Redis or network and adapters
├── integration/                # Real PostgreSQL and/or Redis
└── e2e/                        # Full HTTP flows against the ASGI application
```

The repository currently contains the shared infrastructure tests. Module-level tests follow the same structure as the business modules described in [ARCHITECTURE.md](ARCHITECTURE.md).

### Naming, Markers and Selection

- Test files use `test_<behavior>.py`.
- Test functions describe the expected behavior, for example `test_duplicate_registration_returns_conflict`.
- The `db` marker identifies tests that require a real PostgreSQL and/or Redis instance.
- The `e2e` marker identifies tests that exercise the complete HTTP application.
- `tests/conftest.py` skips `db` tests with an actionable reason when the configured services are unreachable from the host. Run the suite through the `test` profile to exercise them.
- Prefer selecting by behavior (`pytest -k "concurrent_booking"`) over selecting by file path when investigating a failure.

### Unit Tests

#### What is Analyzed?

- Domain entities, value objects, policies and domain services.
- Temporal rules: slot generation, `[start, end)` intervals, `24:00` conversion, `max_advance_days` as calendar days and DST resolution.
- Token signing and verification: JWT claims, HMAC verification tokens, constant-time comparisons.
- Password policy and Argon2id adapter behavior.
- Use cases with fake repositories, fake unit-of-work, fake clock, fake rate limiter and fake email sender.
- Error mapping from domain errors to application/API errors.

#### How is it Tested?

Unit tests import only the code under test and its in-memory collaborators. They do not open database connections, contact Redis, start an HTTP server or send email. Time-dependent code receives an injected clock. Random or generated data comes from `faker` and is constrained by the test case.

#### Objective

Provide fast feedback on business rules, algorithm edge cases and orchestration decisions, including the cases that are expensive to reproduce through the full stack.

### Integration Tests

#### What is Analyzed?

- SQLAlchemy repositories, transactions and unit-of-work behavior.
- Row-Level Security and tenant isolation.
- Unique, check and exclusion constraints.
- Composite foreign keys and migrations.
- Concurrency: duplicate memberships, duplicate pending invitations, competing booking intervals, double submission, booking versus zone deactivation and contiguous bookings.
- Outbox persistence, selection with `FOR UPDATE SKIP LOCKED`, retry state and crash recovery.
- Redis rate-limit counters, atomic increment plus TTL and fail-open behavior.

#### How is it Tested?

Integration tests run against the `postgres-test` and `redis-test` services from `docker-compose.yml`. Each test starts from a clean state, uses real migrations and sets the RLS context explicitly where required. Concurrency tests use independent sessions or connections and synchronization primitives such as events or barriers; they do not rely on timing sleeps. Tests that need to simulate a process crash after commit run the business transaction in one session and then verify that the Outbox row is still recoverable.

SQLite is not used as a substitute for these tests. It does not implement RLS, GiST exclusion constraints, advisory locks, `FOR UPDATE SKIP LOCKED` or the same transactional semantics as PostgreSQL.

#### Objective

Prove that the persistence layer and the database enforce the system's correctness guarantees, including under concurrent access and process failure.

### End-to-End (E2E) Tests

#### What is Analyzed?

- Registration, email verification and login.
- Invitation creation, acceptance, cancellation and membership activation/deactivation.
- Complex and zone creation, schedule configuration and zone status changes.
- Availability queries, booking creation, rescheduling and cancellation.
- Role-based authorization and cross-tenant isolation through the HTTP contract.
- Documented status codes, error codes, headers and response shapes.
- Rate limiting, including the fail-open path when Redis is unavailable.
- Notification flows triggered through the Outbox and a controlled worker/dispatcher.

#### How is it Tested?

E2E tests run the FastAPI application through an ASGI client with lifespan enabled, backed by the real test PostgreSQL and Redis instances. Test data is created through the API or through minimal fixtures, and each test cleans up its own records. External email delivery is replaced with a controlled adapter or fake SMTP boundary so the test can assert whether an email was produced without depending on a real mail server.

E2E tests validate the contract and the integration of all layers. They do not replace integration tests for concurrency, RLS or exclusion constraints.

#### Objective

Confirm that the externally observable API behavior matches the requirements and that the complete flow works with real infrastructure.

---

## Critical Test Infrastructure

### Real PostgreSQL Requirement

The following behaviors must be tested against PostgreSQL:

- Row-Level Security policies and `app.user_id` propagation.
- RLS context reset when a pooled connection is reused.
- Partial unique indexes, composite foreign keys and check constraints.
- `btree_gist` exclusion constraints for operating windows and bookings.
- `FOR UPDATE`, `FOR SHARE`, `pg_advisory_xact_lock` and `FOR UPDATE SKIP LOCKED`.
- `SECURITY DEFINER` functions and triggers with a fixed `search_path`.
- Outbox recovery and transactional visibility.
- Time-zone and DST behavior using `timestamptz`, `AT TIME ZONE` and calendar-day comparisons.

These tests run in the disposable `postgres-test` container, never against the development database.

### Redis and Degradation Tests

Redis tests cover both the healthy and the degraded path:

- The counter increment and TTL assignment are atomic; no key is created without an expiration.
- Exceeding a policy returns `429` with `Retry-After`.
- With Redis unavailable, the request continues (fail-open) and the degradation is logged with `request_id`, policy, subject and cause.
- The degraded response does not include headers implying that the limit was evaluated.
- No partial counter is left behind when the atomic operation fails.
- Logs do not contain tokens, credentials, raw emails or other personal data.

Failure injection must be explicit: point the adapter at an unreachable Redis instance, stop the test container, or inject a client that raises a connection error. Do not weaken the production code path to simulate the failure.

### Concurrency, Time and Isolation

- Concurrency tests use independent database sessions or connections so they exercise real PostgreSQL behavior.
- Synchronization uses deterministic barriers or events, not arbitrary delays.
- Tests assert the exact outcome: one winner and documented conflict responses for the losers.
- Deadlock retry behavior is tested when a transaction can be retried once.
- Time is injected through a clock port or controlled at the database boundary. Tests avoid depending on the machine's current date.
- DST tests use an IANA zone that actually observes DST, not `America/Bogota`, which does not. They cover nonexistent local times, ambiguous local times, `max_advance_days` as calendar days and the persistence of `24:00` as `1440`.
- Availability, booking creation and rescheduling must all use the same slot-generation function; tests assert that the same input produces the same interval in all three paths.

### Outbox and Notification Tests

- A transaction that inserts an Outbox event but fails afterwards leaves no event.
- If the process stops after commit and before publication, the event remains in `outbox_events` and is recovered.
- The dispatcher selects rows with `FOR UPDATE SKIP LOCKED` and does not publish the same row twice concurrently.
- Failed publication increments `attempts`, records `last_error` and schedules `next_attempt_at` with backoff.
- Exhausted retries mark the event `FAILED` without leaking sensitive data.
- A worker that processes an event twice controls or documents the duplicate email effect; delivery is at-least-once.
- Notification tasks re-check the current database state before sending and skip events that are no longer applicable.
- Email content is asserted through a fake SMTP boundary; tests never send real email.

---

## Acceptance Test Suites

The following suites are release gates. Every item requires automated evidence at the most appropriate level: unit for pure rules, integration for persistence and concurrency, and E2E for observable HTTP behavior.

### P0 Acceptance Tests

- [ ] A registration with an already-existing email responds `409` and does not create a second account.
- [ ] A login with a nonexistent email and one with an incorrect password return the same generic `401`.
- [ ] A user with `email_verified = false` cannot log in and receives `403`.
- [ ] The password is stored only as an Argon2id hash and never appears in plaintext in the database or in responses.
- [ ] An invalid or expired verification token does not change `email_verified`; a valid one marks it as true idempotently.
- [ ] An expired JWT, with an invalid signature or from another audience, does not access protected endpoints.
- [ ] Two concurrent requests do not create duplicate memberships for the same user and complex.
- [ ] Two concurrent requests do not create duplicate `PENDING` invitations for the same email and complex.
- [ ] Two clients competing for the same interval and zone produce a single confirmed booking.
- [ ] Double-submitting the same booking returns the existing equivalent booking.
- [ ] A booking concurrent with the deactivation of a zone produces a consistent result and is not confirmed on a deactivated zone.
- [ ] Two contiguous bookings that share the boundary instant are confirmed correctly because they use `[start, end)` intervals.
- [ ] A client does not read or modify another client's bookings.
- [ ] A member without an `ACTIVE` membership does not access a complex's bookings.
- [ ] A reused connection from the pool does not retain the RLS context of a previous user.
- [ ] If the process crashes after the commit and before publishing, the event remains in `outbox_events` and is recovered.
- [ ] A worker that processes an event twice controls or documents the duplicate email effect.
- [ ] RLS, locking, exclusion, concurrency and Outbox tests run against real PostgreSQL; SQLite does not replace these tests.

### P1 Acceptance Tests

- [ ] Overlapping windows cannot be persisted for the same zone and day; two contiguous windows are accepted.
- [ ] A window with a `24:00` closing time is stored as `1440` and returned as `24:00` in US-302 and US-305.
- [ ] Changing a zone's schedule with future bookings does not modify or cancel those bookings; new availability uses the current schedule.
- [ ] Moving a zone to `MAINTENANCE` does not automatically cancel bookings; US-408 can cancel them with a reason and notification.
- [ ] `max_advance_days` is evaluated as calendar days in the complex's time zone, also on dates with DST, and US-401, US-402 and US-403 apply the same limit.
- [ ] A nonexistent local time is resolved to the first valid instant after the gap and an ambiguous time to its first occurrence; availability, creation and rescheduling generate the same interval.
- [ ] An expired `PENDING` invitation is not accepted and its persisted status becomes `EXPIRED` when processed in US-202, US-203 or US-205.
- [ ] With Redis down, rate limiting is disabled (`fail-open`), the request continues, the degradation is logged and no counters remain without a TTL.
- [ ] A user without a membership can book as `CLIENT` and cannot access the complex's staff endpoints.
- [ ] The `complex_booking_clients` view does not return clients from another complex and does not return rows without an `ACTIVE` membership.

---

## Coverage Target

The normative target is **80% line coverage**, as required by RNF-006.

- Coverage is measured with `pytest-cov` and combined across the unit, integration and E2E suites.
- The CI pipeline must fail when the combined coverage falls below the configured threshold.
- Migration files and `conftest.py` are excluded from the report, as configured in `pyproject.toml`.
- A global percentage is not enough on its own: authentication, tenant isolation, booking concurrency, Outbox recovery and DST rules must have direct tests even if the global number is already above the target.

The current automation (`Makefile`, CI and README) still uses `--cov-fail-under=70`. The normative target is 80%, so raising the configured threshold is a pending alignment task and is not changed by this document.

---

## Running the Tests

### Tests with Docker (recommended)

Docker Compose runs the suite against the dedicated `postgres-test` and `redis-test` services, which have their own containers, volumes and ports. The development database and cache are never touched, so both profiles can run at the same time.

```shell
# Run all tests (unit + integration + e2e)
docker compose --profile test run --rm backend-test pytest tests -v # or: make test

# Run only unit tests
docker compose --profile test run --rm backend-test pytest tests/unit -v

# Run only integration tests
docker compose --profile test run --rm backend-test pytest tests/integration -v # or: make test-integration

# Run only e2e tests
docker compose --profile test run --rm backend-test pytest tests/e2e -v # or: make test-e2e

# Run with a coverage report (fails if the coverage drops below 70%)
docker compose --profile test run --rm backend-test pytest tests --cov=src --cov-report=term-missing --cov-fail-under=70 # or: make test-coverage

# Run a specific test by name
docker compose --profile test run --rm backend-test pytest -k "test_concurrent_book_confirmation"

# Stop on the first failure
docker compose --profile test run --rm backend-test pytest -x
```

`docker compose run` starts the `postgres-test` and `redis-test` dependencies automatically, so they do not need to be brought up beforehand. To keep them running in the background and then execute the suite against them:

```shell
docker compose --profile test up -d
docker compose --profile test run --rm backend-test pytest tests/integration -m db
docker compose --profile test run --rm backend-test pytest tests/e2e -m e2e
docker compose --profile test --profile dev down # or: make down
```

To discard the test database and start from a clean state, remove the test volumes:

```shell
docker compose --profile test down -v
```

> `make clean` removes the volumes of **both** profiles, so it also deletes the development database.

> The commands above enforce the currently configured 70% threshold. The normative target for this project is 80% (see [Coverage Target](#coverage-target)); raising the flag in `Makefile` and CI is a separate change.

### Tests without Docker (unit tests only)

Unit tests have no external dependencies and can be run directly with Poetry:

```shell
# Run only unit tests
poetry run pytest tests/unit -v # or: make test-unit

# Run the integration tests that do not require a database
poetry run pytest tests/integration -m "not db" -v # or: make test-integration-no-db

# Collect the unit coverage data into tests/.coverage.unit
COVERAGE_FILE=tests/.coverage.unit poetry run pytest tests/unit --cov=src --cov-report= # or: make test-coverage-unit
```

> Watch mode is not available out of the box: `pytest-watch` is not declared in `pyproject.toml`. Add it first with `poetry add --group test pytest-watch` and then run `poetry run ptw tests/unit/`.

### Combining the coverage reports

Each suite writes its own coverage data file, and the final step combines them and enforces the threshold:

```shell
# Build the testing image before running the containerized suites
docker compose build backend-test # or: make build-test

# Collect the integration coverage data into tests/.coverage.integration*
docker compose --profile test run --rm -e COVERAGE_FILE=tests/.coverage.integration backend-test pytest tests/integration --cov=src --cov-report= # or: make test-coverage-integration

# Collect the e2e coverage data into tests/.coverage.e2e*
docker compose --profile test run --rm -e COVERAGE_FILE=tests/.coverage.e2e backend-test pytest tests/e2e --cov=src --cov-report= # or: make test-coverage-e2e

# Combine tests/.coverage.unit*, tests/.coverage.integration* and tests/.coverage.e2e*
poetry run coverage combine tests/ # or: make test-coverage-report
```

---

## Continuous Integration

The CI pipeline runs the same verification steps used locally:

1. **Lint and type-check:** `make check` runs Ruff formatting, Ruff linting and Mypy.
2. **Unit tests:** `make test-unit` plus `make test-coverage-unit`.
3. **Integration tests:** `make test-integration` plus `make test-coverage-integration`, against the dedicated test services.
4. **E2E tests:** `make test-e2e` plus `make test-coverage-e2e`, against the dedicated test services.
5. **Coverage report:** the pipeline downloads the coverage artifacts, combines them and runs `make test-coverage-report`.

The pipeline fails early if any preceding job fails. The coverage job is the final gate and applies the configured threshold to the combined report.
