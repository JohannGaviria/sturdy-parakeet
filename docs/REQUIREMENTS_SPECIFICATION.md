# Requirements Specification - Sturdy Parakeet

> Defines the functionalities offered by the system, organized by modules and expressed through functional requirements and their respective user stories, establishing the expected behavior of the application from the business perspective.

## Table of Contents

- [Project Summary](#project-summary)
- [System Requirements](#system-requirements)
	- [Non-Functional Requirements](#non-functional-requirements)
	- [Functional Requirements](#functional-requirements)
- [User Stories](#user-stories)
- [Data Models](#data-models)
	- [Persistence Models](#persistence-models)
	- [Cache Structures - Redis](#cache-structures---redis)

---

## Project Summary

- **Project name:** Sturdy Parakeet

- **Short description:** Multi-tenant REST API to administer sports complexes and manage the availability and booking of their zones, with its own authentication through registration, login and email verification, and roles `OWNER`, `MANAGER` and `CLIENT`.

- **Detailed description:** Sturdy Parakeet is a platform that facilitates the administration and booking of sports complexes. It brings together in a single place the catalog of complexes and zones, operating hours, availability and booking policies, so that administrators can operate their facilities and clients can book quickly and without conflicts. The system protects the information of each complex, controls access according to each user's role and notifies relevant changes by email. Technically, it relies on a multi-tenant REST API with data isolation in PostgreSQL and asynchronous services for notification tasks.

- **Main objective:** Centralize the operation and booking of sports complexes in a secure, consistent and multi-tenant API that reduces manual management and prevents availability conflicts.

- **Real problem it solves:** Manual management of schedules, zones and bookings generates overlaps, availability errors, poor traceability and risks of access to information from other complexes. Sturdy Parakeet unifies these processes with business rules, per-complex isolation and access control.

- **Actors involved:**
    - `CLIENT`: browses the catalog and availability, and creates, reschedules, cancels and queries their own bookings.
    - `MANAGER`: administers zones, schedules, availability and bookings of the complex to which they belong.
    - `OWNER`: registers and administers the complex, its zones, booking policies and memberships; invites, activates/deactivates and cancels invitations; can also cancel bookings.

- **Architecture type:** Modular monolith based on hexagonal architecture (Ports & Adapters) and tactical DDD.

- **Initial technology stack:**
    - Language: Python
    - Framework: FastAPI
    - Database: PostgreSQL
    - Others: SQLAlchemy · Alembic · Uvicorn · Redis · Celery · Argon2id · PyJWT · SMTP· Structlog · Poetry · Ruff · Mypy · Pytest · pytest-asyncio · pytest-cov · Docker · GitHub Actions · OpenAPI/Swagger UI · PostgreSQL RLS · btree_gist

---

## System Requirements

### Non-Functional Requirements

#### RNF-001: Multi-tenant isolation

**Description:** The API must guarantee that the data of each sports complex is isolated from that of the others: no user can query or modify information from a complex to which they do not belong, even if they manipulate identifiers in the request. Isolation must be enforced in the application and reinforced in the persistence layer through PostgreSQL Row-Level Security (RLS).

#### RNF-002: Data consistency and integrity

**Description:** The API must maintain data consistency and integrity. Operations that modify multiple records (for example, accepting an invitation or cancelling a booking and recording its event in Outbox) must execute atomically: they either complete entirely or are not applied. Integrity rules (uniqueness, valid relationships, allowed states and non-overlapping bookings) must be guaranteed in the database through constraints, and not only in the application logic.

#### RNF-003: Concurrency management

**Description:** The API must guarantee that simultaneous requests do not generate overlapping bookings on the same sports zone and time slot, nor the multiple acceptance of the same invitation. If several requests compete for the same time slot, exactly one must succeed and the others must receive a conflict response (HTTP 409), without leaving inconsistent data. The guarantee must rely on the database and not depend on the application's in-memory state, so that it holds with multiple API instances.

#### RNF-004: Observability and event logging

**Description:** The API must record relevant execution events and errors through structured logs with Structlog. Each log entry must include a correlation identifier per request, which allows tracing its path, and the minimum context for diagnosis (level, timestamp, route, method, status code, duration and, when applicable, sports complex and user). Logs must not contain credentials, passwords, access tokens, invitation tokens, email verification tokens or unnecessary personal data; sensitive values must be redacted before being written.

#### RNF-005: Rate limiting

**Description:** The API must limit the number of requests per client within a time window, identifying the client by authenticated user, by the hash of the normalized email in registration and login, or, failing that, by IP address, to prevent abuse and protect availability. Public endpoints (such as availability queries) and sensitive ones (registration, login, email verification, catalog queries, booking creation, complex creation and invitation creation) must have stricter and configurable limits. When exceeded, the API must respond HTTP 429 with the `Retry-After` header. Counters must be stored in Redis so that the limit is enforced consistently across instances. For the MVP, `fail-open` is adopted in all operations: if Redis is unavailable, the request continues without rate limiting, the degradation is logged and the risk is explicitly accepted; the system must not present the limit as applied during the outage. Counter increments and TTL assignment must be atomic so as not to leave keys without expiration.

#### RNF-006: Automated testing

**Description:** The API must have automated tests with a minimum code coverage of 80%, including authentication (registration, login and email verification), business rules, role-based authorization, isolation between sports complexes and critical booking operations. Persistence, Row-Level Security (RLS), concurrency, Outbox recovery and daylight saving time (DST) tests must run against a real PostgreSQL instance in an isolated, disposable environment. Coverage must be measured automatically with Pytest and `pytest-cov`, and continuous integration must fail if it falls below the threshold.

### Functional Requirements

#### Module 1 – Authentication

- **RF-101:** The API must allow anyone to register with their email address and a password, creating an account with the email pending verification.
- **RF-102:** The API must allow a user to verify their email address through a signed token with an expiration.
- **RF-103:** The API must allow a user to log in with their email and password, and issue a JWT access token to authenticate requests.

#### Module 2 – Complexes and memberships

- **RF-201:** The API must allow an authenticated user to register a sports complex and be automatically assigned as its `OWNER`.
- **RF-202:** The API must allow an `OWNER` to invite, through their email address, a person to operate as `MANAGER` of their sports complex.
- **RF-203:** The API must allow an authenticated user to accept a valid invitation and become `MANAGER` of the sports complex that issued it.
- **RF-204:** The API must allow an `OWNER` to activate or deactivate a `MANAGER`'s participation in their sports complex.
- **RF-205:** The API must allow an `OWNER` to cancel a pending invitation of their sports complex, preventing it from being accepted.

#### Module 3 – Complexes and sports zones

- **RF-301:** The API must allow an `OWNER` or `MANAGER` to create sports zones associated with the sports complex to which they belong.
- **RF-302:** The API must allow any authenticated user to query, in a single endpoint, the catalog of sports complexes with all public data of each complex, including its active sports zones, operating hours and booking policies.
- **RF-303:** The API must allow an `OWNER` or `MANAGER` to update the sports zones of the complex to which they belong.
- **RF-304:** The API must allow an `OWNER` or `MANAGER` to change the status of a sports zone of their complex to: active, inactive or under maintenance.
- **RF-305:** The API must allow an `OWNER` or `MANAGER` to configure the operating hours (days and time slots) and the booking slot duration of a sports zone of their complex.

#### Module 4 – Bookings

- **RF-401:** The API must allow a `CLIENT` to book an active sports zone at an available time, preventing overlapping bookings.
- **RF-402:** The API must allow anyone to query the availability of a complex's sports zones for a given date, with an optional filter by sport or sports zone.
- **RF-403:** The API must allow a `CLIENT` to reschedule their own booking (date, time or sports zone), subject to availability and the sports complex's policy.
- **RF-404:** The API must allow a `CLIENT` to cancel their own booking in accordance with the sports complex's cancellation policy.
- **RF-405:** The API must allow a `CLIENT` to query their own bookings, filtering by date, sports zone and status.
- **RF-406:** The API must allow an `OWNER` or `MANAGER` to query the bookings of their sports complex, filtering by date, sports zone, status and client.
- **RF-407:** The API must allow an `OWNER` to configure the booking policies of their sports complex: minimum and maximum advance notice for booking, cancellation deadline and maximum number of active bookings per client.
- **RF-408:** The API must allow an `OWNER` or `MANAGER` to cancel a booking of their sports complex without being subject to the cancellation deadline, indicating the reason.

#### Module 5 – Notifications

- **RF-501:** The API must send an email with the verification link when an account is registered.
- **RF-502:** The API must send an email with the invitation link to the invited person when an `OWNER` creates an invitation to be `MANAGER`.
- **RF-503:** The API must send an email to the `CLIENT` when their booking is cancelled by an `OWNER` or `MANAGER` through US-408, informing the reason.

---

## User Stories

### Module 1 – Authentication

#### US-101: Register with email and password

**As** a person who wants to use the system,
**I want** to create an account with my email address and a password,
**So that** I can authenticate later and operate in the API.

**Endpoint:** `POST /api/v1/auth/register`
**Publishes Event:** `user.verification_email.created`
**Rate limit:** `rl:auth-register:ip:{ip}:{window}`: 5 requests per IP every 3600 s; `rl:auth-register:email:{email_hash}:{window}`: 3 requests per email every 3600 s.

**Priority:** High (P0)
**Size:** XL
**Estimate:** 5

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `email`, `password` and, optionally, `full_name`. Additional fields, incorrect types or `null` in required fields respond `422`; strings are trimmed before validation, except `password`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `email`: required, with a valid email format and a maximum of 320 characters; spaces are removed and it is normalized to lowercase before being stored.
- [ ] `password`: required, between 12 and 128 characters; it is not trimmed or normalized.
- [ ] `full_name`: optional; if sent, it must be a string between 2 and 150 characters after removing leading and trailing spaces.

**Business rules**

- [ ] If a user with the same normalized email already exists, it responds `409` (`EMAIL_ALREADY_IN_USE`), without modifying the existing record and without revealing data from that account.
- [ ] The password is stored only as an Argon2id hash with a per-user salt; it is never persisted or returned in plaintext.
- [ ] The account is created with `email_verified = false`, `email_verified_at = NULL` and `last_login_at = NULL`.
- [ ] Registration does not assign roles or memberships; the user will be able to act as `CLIENT` once authenticated.
- [ ] Registration does not issue an access token; the user must verify their email and then log in.
- [ ] The registration inserts the `user.verification_email.created` event into `outbox_events`, with only `user_id` and `request_id`, within the same transaction; if the event insertion fails, the registration is rolled back.
- [ ] The notification task of RF-501 sends the verification email after the commit, without blocking the `201` response.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`.
- [ ] `users` is a global table (without per-complex RLS); the email is stored normalized in lowercase and its uniqueness is guaranteed by a database constraint.
- [ ] The user registration and the event insertion into `outbox_events` execute in an atomic transaction.
- [ ] If two simultaneous registrations use the same email, exactly one responds `201` and the other `409`; the uniqueness violation is translated to `409`, never to `500`.
- [ ] `created_at` and `updated_at` are assigned with the current database date.

**Security**

- [ ] The rate limit is evaluated after validating the input and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged.
- [ ] Rate-limit keys per email use the SHA-256 of the normalized email, never the plaintext email.
- [ ] The password is never written to logs, responses, traces or error messages.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id` when applicable; they never include passwords, hashes, tokens or email addresses.
- [ ] Unexpected errors respond `500` without traces or internal details.

**HTTP responses**

- [ ] `201`: account created; includes `id`, `email`, `full_name`, `email_verified: false` and `created_at`, without `password_hash`.
- [ ] `409`: the email is already registered (`EMAIL_ALREADY_IN_USE`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-102: Verify the email address

**As** a registered user,
**I want** to verify my email through the link received,
**So that** I can enable login.

**Endpoint:** `POST /api/v1/auth/verify-email`
**Requires Authentication:** No; the email token proves ownership.
**Rate limit:** `rl:auth-verify-email:ip:{ip}:{window}`: 20 requests per IP every 3600 s.

**Priority:** High (P0)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `token`. Additional fields, incorrect type, `null` or absence of the field respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `token`: required, between 32 and 512 characters after removing leading and trailing spaces. The `422` applies only for length, type or missing field.

**Business rules**

- [ ] The token has the format `{user_id}.{expires_at}.{signature}`. The signature is calculated with HMAC-SHA256 over `{user_id}.{expires_at}` using `EMAIL_VERIFICATION_SECRET` and is compared in constant time.
- [ ] If the format or the signature are invalid, or the user does not exist, it responds `400` (`INVALID_VERIFICATION_TOKEN`).
- [ ] If `expires_at` has already expired, it responds `410` (`VERIFICATION_TOKEN_EXPIRED`).
- [ ] If the user already has `email_verified = true`, it responds `200` idempotently.
- [ ] If the token is valid and current, `email_verified = true`, `email_verified_at = now()` and `updated_at = now()` are updated, only if `email_verified = false`.
- [ ] Verification does not issue an access token; the user must log in afterwards with US-103.
- [ ] The verification token is not stored in the database nor returned in the response.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`.
- [ ] `users` is a global table (without per-complex RLS); the verification update executes in an atomic transaction.
- [ ] The update is conditional (`WHERE id = :user_id AND email_verified = false`), so that two simultaneous verifications do not generate inconsistencies.
- [ ] If two simultaneous requests verify the same user, both respond `200` and only one modifies the row.

**Security**

- [ ] The rate limit is evaluated before accessing the database; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged.
- [ ] The verification token is never persisted, written to logs, sent to the broker or appears in error traces.
- [ ] The signature is compared in constant time (`hmac.compare_digest`), not with direct string comparison.
- [ ] Invalid token errors use the same generic message to avoid user enumeration.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id` when applicable; they never include tokens or email addresses.
- [ ] Unexpected errors respond `500` without traces or internal details.

**HTTP responses**

- [ ] `200`: email verified or already verified; includes `email_verified: true` and `email_verified_at`.
- [ ] `400`: invalid token, incorrectly formatted or from a nonexistent user (`INVALID_VERIFICATION_TOKEN`).
- [ ] `410`: expired token (`VERIFICATION_TOKEN_EXPIRED`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: missing, empty, incorrectly typed token or token with a length outside 32-512 characters (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-103: Log in with email and password

**As** a registered user,
**I want** to log in with my email and password,
**So that** I can obtain an access token and use the protected endpoints.

**Endpoint:** `POST /api/v1/auth/login`
**Requires Authentication:** No.
**Rate limit:** `rl:auth-login:ip:{ip}:{window}`: 10 requests per IP every 60 s; `rl:auth-login:email:{email_hash}:{window}`: 5 requests per email every 60 s.

**Priority:** High (P0)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `email` and `password`. Additional fields, incorrect types, `null` or absence of fields respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `email`: required, with a valid email format and a maximum of 320 characters; spaces are removed and it is normalized to lowercase.
- [ ] `password`: required, non-empty and a maximum of 128 characters; it is not trimmed.

**Business rules**

- [ ] The user is looked up by the normalized email. If it does not exist or the password does not match, it responds `401` (`INVALID_CREDENTIALS`) with the same message and a dummy hash verification so as not to reveal whether the email exists or introduce timing differences.
- [ ] If the credentials are correct but `email_verified = false`, it responds `403` (`EMAIL_NOT_VERIFIED`).
- [ ] If the credentials are correct and the email is verified, it issues an access JWT signed with `HS256` using `JWT_SECRET` from the environment.
- [ ] The token includes `sub` (user UUID), `email`, `type = "access"`, `iss`, `aud`, `iat` and `exp`; its validity is 60 minutes.
- [ ] The response does not include a refresh token; access is valid until the JWT expires.
- [ ] `last_login_at` is updated with the current database date.
- [ ] All protected endpoints validate the JWT signature, `exp`, `iss`, `aud` and `type = "access"`, and resolve the user from `sub`.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`.
- [ ] `users` is a global table (without per-complex RLS); the `last_login_at` update executes in a transaction.
- [ ] The password is verified with Argon2id in constant time; the hash is never returned or logged.

**Security**

- [ ] The rate limit is evaluated before verifying the credentials; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged.
- [ ] Rate-limit keys per email use the SHA-256 of the normalized email, never the plaintext email.
- [ ] Authentication failures use the same generic message, both for a nonexistent email and for an incorrect password.
- [ ] `JWT_SECRET` is read from an environment variable, has no weak default value and is never logged; the `none` algorithm is rejected.
- [ ] The password, its hash and the issued token are never written to logs, responses or traces.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id` when applicable; they never include passwords, tokens or email addresses.
- [ ] Unexpected errors respond `500` without traces or internal details.

**HTTP responses**

- [ ] `200`: includes `access_token`, `token_type: "Bearer"`, `expires_in: 3600` and `user: { id, email, full_name }`.
- [ ] `401`: invalid credentials (`INVALID_CREDENTIALS`).
- [ ] `403`: the email is not verified (`EMAIL_NOT_VERIFIED`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

### Module 2 – Complexes and memberships

#### US-201: Register a sports complex and be assigned as `OWNER`

**As** an authenticated user,
**I want** to register a sports complex,
**So that** I can administer it as its owner (`OWNER`).

**Endpoint:** `POST /api/v1/complexes`
**Requires Authentication:** Yes, valid access token.
**Rate limit:** `rl:complexes:u:{user_id}:{window}`: 5 requests per user every 3600 s.

**Priority:** High (P0)
**Size:** M
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `name`, `slug`, `description`, `address`, `city` and `timezone`. Additional fields, incorrect types or `null` in non-nullable fields respond `422`; strings are trimmed before validating length; a `Content-Type` other than `application/json` responds `415`.
- [ ] `name`, `slug`, `address` and `city` are required; `description` and `timezone` are optional (they can be omitted, but not sent as `null`).
- [ ] `name`: Must be between 3 and 120 characters after removing leading and trailing spaces.
- [ ] `slug`: Must be between 3 and 80 characters, in lowercase and with format `^[a-z0-9]+(-[a-z0-9]+)*$`. It is not normalized: if it contains uppercase letters or other characters, it is rejected.
- [ ] `description`: optional; if sent, it is stored as text and leading and trailing spaces are removed.
- [ ] `address`: Must be between 1 and 255 characters after removing leading and trailing spaces.
- [ ] `city`: Must be between 1 and 100 characters after removing leading and trailing spaces.
- [ ] `timezone`: if sent, it must be a valid IANA zone; defaults to `America/Bogota`.

**Business rules**

- [ ] The creator's identity is obtained from the validated access token; the client cannot designate another owner.
- [ ] The complex is created with `created_by` equal to the token's `user_id`.
- [ ] The creator is registered in `complex_memberships` with `role = 'OWNER'` and `status = 'ACTIVE'`.
- [ ] The `slug` is provided by the client; it is not generated automatically and must be unique.
- [ ] The initial row of `complex_booking_policies` is created with the default values (`min_advance_minutes = 60`, `max_advance_days = 30`, `cancellation_deadline_hours = 24`, `max_active_bookings_per_client = 3`).
- [ ] A user can register more than one complex; each one will have its own `OWNER` membership.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the insertion of `sports_complexes`, `complex_memberships` and `complex_booking_policies` executes in an atomic transaction; uniqueness and integrity constraints are guaranteed in the database.
- [ ] The RLS read policy of `sports_complexes` allows the row to be seen when `created_by = app.user_id` or when the user has an `ACTIVE` membership in the complex.
- [ ] The RLS insert policy of `complex_memberships` requires `user_id = app.user_id` and `EXISTS (SELECT 1 FROM sports_complexes c WHERE c.id = complex_id AND c.created_by = app.user_id)`.
- [ ] Thanks to the previous policy, the complex's `INSERT ... RETURNING` returns the created row even though the membership does not yet exist.
- [ ] If two simultaneous requests use the same `slug`, exactly one succeeds and the other receives `409` (`UNIQUE` constraint, not a prior check).
- [ ] `created_at` and `updated_at` are assigned with the current database date.

**Security**

- [ ] The endpoint requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity and role are derived exclusively from the token.
- [ ] The endpoint is only accessible with an authenticated request.
- [ ] The rate limit `rl:complexes:u:{user_id}:{window}` (5 requests per user every 3600 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `201`: complex created; includes `id`, `name`, `slug`, `address`, `city`, `timezone`, `description`, `created_at` and the resulting membership `{ role: "OWNER", status: "ACTIVE" }`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `409`: `slug` already registered (`SLUG_ALREADY_EXISTS`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-202: Invite a person as `MANAGER` via email

**As** an `OWNER` of a sports complex,
**I want** to invite a person by email to operate as `MANAGER`,
**So that** I can delegate the daily operation of the complex.

**Endpoint:** `POST /api/v1/complexes/{complex_id}/invitations`
**Requires Authentication:** Yes, valid access token and `OWNER` role.
**Publishes Event:** `invitation.created`
**Rate limit:** `rl:invitations:u:{user_id}:{window}`: 20 requests per user every 3600 s (the counter is shared with US-108).

**Priority:** High (P0)
**Size:** XL
**Estimate:** 5

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `email`. Additional fields, incorrect types, `null` or absence of the field respond `422`; strings are trimmed before validation; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `email`: with a valid email format, maximum 320 characters; spaces are removed and it is normalized to lowercase before being stored.

**Business rules**

- [ ] A nonexistent or foreign complex responds `404`; an active member without the `OWNER` role responds `403`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The requester must be `OWNER` in the indicated complex.
- [ ] It is not allowed to invite an email that already belongs to an active member (`OWNER` or `MANAGER`) of the complex, including the requester's own email; it responds `409` (`ALREADY_MEMBER`).
- [ ] A `MANAGER` with an `INACTIVE` membership can be invited again; upon accepting, their membership is reactivated (US-106).
- [ ] Only one valid `PENDING` invitation can exist per `(complex_id, email)` pair; a new attempt responds `409` (`INVITATION_ALREADY_PENDING`).
- [ ] A `PENDING` invitation with `expires_at <= now()` is marked as `EXPIRED` within the same transaction and before evaluating uniqueness, with `WHERE status = 'PENDING' AND expires_at <= now()`, allowing a new one to be created.
- [ ] The invitation is created with `status = 'PENDING'`, `invited_by` taken from the token and `expires_at = now() + 7 days`.
- [ ] The invitation token is signed (`{invitation_id}.{signature}`, with `signature` calculated with HMAC-SHA256 and a server secret key); it is not stored in the database nor returned in the response.
- [ ] The invitation creation inserts the `invitation.created` event into `outbox_events` within the same transaction and with only `invitation_id`; the dispatcher publishes it after the commit and the notification task builds the token when assembling the email.
- [ ] If the insertion of the event into `outbox_events` fails, the entire transaction is rolled back and the invitation is not created; no event is published outside Outbox.
- [ ] The notification task of RF-502 retries sending the email with backoff if it fails, without blocking the `201` response.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update of expired invitations, the insertion of the new invitation and the insertion of its event into `outbox_events` execute in an atomic transaction; uniqueness rules are guaranteed with database constraints.
- [ ] A partial unique index is applied on `(complex_id, email)` for rows with `status = 'PENDING'`.
- [ ] If two simultaneous requests invite the same email, exactly one responds `201` and the other `409`; the uniqueness violation is translated to `409`, never to `500`.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `created_at`/`updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; the `OWNER` is identified exclusively from the token and `invited_by` is not accepted from the body.
- [ ] The rate limit `rl:invitations:u:{user_id}:{window}` (20 requests per user every 3600 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] The plaintext token is not persisted, not returned in the response, does not pass through the broker and is not written to logs.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `201`: invitation created; includes `id`, `complex_id`, `email`, `status`, `expires_at` and `created_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `403`: the requester is not an active `OWNER` of the complex (`FORBIDDEN`).
- [ ] `404`: the complex does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: a pending invitation already exists for that email (`INVITATION_ALREADY_PENDING`) or the email already belongs to an active member, including the requester (`ALREADY_MEMBER`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-203: Accept a valid invitation and become `MANAGER`

**As** an authenticated user who received an invitation,
**I want** to accept it while it is valid,
**So that** I can operate the sports complex as `MANAGER`.

**Endpoint:** `POST /api/v1/invitations/accept`
**Requires Authentication:** Yes, valid access token.
**Rate limit:** `rl:invitation-accept:u:{user_id}:{window}`: 10 requests per user every 3600 s.

**Priority:** High (P0)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `token`. Additional fields, incorrect type, `null` or absence of the field respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `token`: Must be between 32 and 512 characters after removing leading and trailing spaces. The `422` applies only for length, type or missing field; a token with valid length but invalid format or signature responds `404`.

**Business rules** (evaluated in this order)

- [ ] This flow is the exception to the prior membership verification. Access is validated through the invitation and the `SECURITY DEFINER` function; if the user is already `OWNER` of the complex, it responds `409` (`OWNER_CANNOT_BE_MANAGER`).
- [ ] The token signature is validated and the `invitation_id` is extracted. If the format or the signature are invalid, or the invitation does not exist, it responds `404`.
- [ ] If the invitation is `CANCELLED`, it responds `410` (`INVITATION_CANCELLED`). If it is `EXPIRED`, it responds `410` (`INVITATION_EXPIRED`). If it is `PENDING` with `expires_at <= now()`, it is updated to `EXPIRED` in the same transaction before responding `410` (`INVITATION_EXPIRED`). If it is already `ACCEPTED` and `accepted_by` is the authenticated user, it responds `200` with the current membership status; if it was accepted by another account, it responds `404`.
- [ ] The authenticated user must have `email_verified = true`; otherwise, it responds `403` (`EMAIL_NOT_VERIFIED`).
- [ ] The email registered in the authenticated user's account must match `invitations.email` case-insensitively; if it does not match, it responds `403` (`EMAIL_MISMATCH`).
- [ ] If the user is `OWNER` of the complex, it responds `409` (`OWNER_CANNOT_BE_MANAGER`).
- [ ] If the user has no membership in the complex, one is created with `role = 'MANAGER'` and `status = 'ACTIVE'`.
- [ ] If the user already has a `MANAGER` membership with `status = 'INACTIVE'`, it is reactivated to `ACTIVE`.
- [ ] If the user already has a `MANAGER` membership with `status = 'ACTIVE'` (for example, reactivated by the `OWNER` before accepting), it is not duplicated; the invitation still transitions to `ACCEPTED`.
- [ ] The invitation transitions to `ACCEPTED`, with `accepted_by` taken from the token and `accepted_at` with the current database date.
- [ ] A retry by a user who has already accepted responds `200` with the current membership status (`ACTIVE` or `INACTIVE`), not with the status of the first acceptance.
- [ ] Temporary expiration remains a validity condition even if the persisted status has not yet been updated; this request persists `EXPIRED` when it finds a `PENDING` invitation that has expired.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; reading the invitation, updating it to `EXPIRED` when applicable and updating the membership execute in an atomic transaction; constraints and indexes guarantee uniqueness.
- [ ] The invitation is locked with `SELECT ... FOR UPDATE` or updated conditionally with `WHERE status = 'PENDING'` to guarantee a single acceptance. The `EXPIRED` marking uses `WHERE status = 'PENDING' AND expires_at <= now()`, so it does not overwrite a concurrent acceptance. If two simultaneous requests try to accept the same invitation, only one modifies it.
- [ ] The transition to `ACCEPTED` and the creation or reactivation of the membership are atomic: they complete entirely or are not applied.
- [ ] RLS policies are applied with `app.user_id` and the `updated_at` audit; the invitation lookup and the membership creation use a `SECURITY DEFINER` function limited to this case, because the user is not yet a member of the complex.
- [ ] The `SECURITY DEFINER` function sets `SET search_path = pg_catalog, public` and does not use dynamic SQL.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid access token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token.
- [ ] The invitation token signature is compared in constant time (`hmac.compare_digest`), not with direct string comparison.
- [ ] All rejection causes for a nonexistent or unacceptable token use the same message and the same response shape to avoid enumeration, except for the `410` responses for expired or cancelled invitations.
- [ ] The rate limit `rl:invitation-accept:u:{user_id}:{window}` (10 requests per user every 3600 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include access tokens, invitation tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: invitation accepted or retry by the same user; includes the complex `{ id, name, slug }`, the current membership status `{ role: "MANAGER", status }` and `accepted_at`.
- [ ] `401`: access token missing or invalid (`INVALID_TOKEN`).
- [ ] `403`: the user's email is not verified (`EMAIL_NOT_VERIFIED`) or does not match the invitation's email (`EMAIL_MISMATCH`).
- [ ] `404`: the token does not correspond to an invitation acceptable due to nonexistence, invalid signature or having been accepted by another account (`NOT_FOUND`).
- [ ] `409`: the user is `OWNER` of the complex (`OWNER_CANNOT_BE_MANAGER`).
- [ ] `410`: the invitation is expired (`INVITATION_EXPIRED`) or cancelled (`INVITATION_CANCELLED`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: missing, empty, incorrectly typed token or token with a length outside 32–512 characters (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-204: Activate or deactivate a `MANAGER`'s participation

**As** an `OWNER` of a sports complex,
**I want** to activate or deactivate a `MANAGER`'s participation,
**So that** I can control their access to the complex's operation.

**Endpoint:** `PATCH /api/v1/complexes/{complex_id}/memberships/{membership_id}`
**Requires Authentication:** Yes, valid access token and `OWNER` role.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** S
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `status`. Additional fields, incorrect types, `null` or absence of the field respond `422`; strings are trimmed before validation; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `membership_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `status`: limited to `ACTIVE` or `INACTIVE`.

**Business rules**

- [ ] A nonexistent or foreign complex responds `404`; an active member without the `OWNER` role responds `403`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The requester must be an active `OWNER` of the complex.
- [ ] The target membership must belong to the indicated complex and have `role = 'MANAGER'`.
- [ ] `INACTIVE` immediately revokes the `MANAGER`'s access to the complex's operations (permissions are evaluated against the database on each request).
- [ ] `ACTIVE` reactivates the `MANAGER`'s participation.
- [ ] Changing to the same status the membership already has is idempotent and responds `200` without modifying `updated_at`.
- [ ] Deactivation does not affect bookings the user has made as `CLIENT`.
- [ ] An `OWNER`'s membership cannot be modified; it responds `409` (`OWNER_MEMBERSHIP_NOT_MODIFIABLE`).

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; integrity constraints are guaranteed in the database.
- [ ] The update executes with a condition on `id`, `complex_id`, `role = 'MANAGER'` and `status <> :status` to avoid modifications outside the tenant and not touch rows without a real change.
- [ ] If the `UPDATE` affects one row, `updated_at` is updated with the current database date.
- [ ] If the `UPDATE` affects zero rows, the membership is queried by `id` and `complex_id`: if it does not exist or belongs to another complex it responds `404`; if it is `OWNER` it responds `409`; if it is `MANAGER` and already has the requested status it responds `200` without modifying the row.
- [ ] RLS policies are applied with `app.user_id` and the corresponding audit fields.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid access token it responds `401` with `WWW-Authenticate: Bearer`; identity and role are derived exclusively from the token.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] A membership from another complex or an `OWNER` cannot be modified.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: membership updated or idempotent status; includes `id`, `user_id`, `role`, `status` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `403`: the requester is not an active `OWNER` of the complex (`FORBIDDEN`).
- [ ] `404`: the complex or the membership does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: the target membership is an `OWNER` and cannot be modified (`OWNER_MEMBERSHIP_NOT_MODIFIABLE`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid identifiers or status, or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-205: Cancel a pending invitation

**As** an `OWNER` of a sports complex,
**I want** to cancel a pending invitation,
**So that** the invited person cannot accept it.

**Endpoint:** `DELETE /api/v1/complexes/{complex_id}/invitations/{invitation_id}`
**Requires Authentication:** Yes, valid access token, `OWNER` role.
**Rate limit:** `rl:invitations:u:{user_id}:{window}`: 20 requests per user every 3600 s.

**Priority:** Medium (P1)
**Size:** S
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; only `complex_id` and `invitation_id` are validated as path UUIDs. Invalid identifiers respond `422`; `415` and body field validation do not apply.
- [ ] The request does not require a body; any additional data does not modify the operation.

**Business rules**

- [ ] A nonexistent or foreign complex responds `404`; an active member without the `OWNER` role responds `403`; an invitation from another complex responds `404`.
- [ ] The requester must be `OWNER` with `status = 'ACTIVE'` in the complex.
- [ ] The target invitation must belong to the indicated complex.
- [ ] Only an invitation with `status = 'PENDING'` and `expires_at > now()` is cancelled.
- [ ] If the invitation is `PENDING` but expired, it is updated to `EXPIRED` in the same transaction before responding `409` (`INVITATION_EXPIRED`).
- [ ] If the invitation is already `ACCEPTED`, `CANCELLED` or `EXPIRED`, it responds `409` (`INVITATION_NOT_PENDING`) without modifying it.
- [ ] Cancellation changes `status` to `CANCELLED` and records `cancelled_at` with the current database date.
- [ ] The invitation token immediately stops being acceptable (US-106 responds `410`).
- [ ] The invitation is kept for auditing; it is not physically deleted.
- [ ] The operation is not idempotent: repeating an already-applied `DELETE` responds `409` (`INVITATION_NOT_PENDING`).

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update to `EXPIRED` if the invitation is expired, and the update of `status` and `cancelled_at`, execute in an atomic transaction; integrity rules are guaranteed in the database.
- [ ] First, a `PENDING` invitation with `expires_at <= now()` is marked as `EXPIRED` through `UPDATE ... WHERE status = 'PENDING' AND expires_at <= now()`, so it does not overwrite a concurrent acceptance. Cancellation then executes with a conditional update `WHERE id = :invitation_id AND complex_id = :complex_id AND status = 'PENDING' AND expires_at > now()`; this condition resolves the race between acceptance and cancellation, so exactly one operation wins and the loser receives `409` in this story or `410`/`404` in US-106.
- [ ] If no row is affected, a distinction is made between a nonexistent or foreign invitation (`404`) and a non-cancellable invitation, whether expired or in a final state (`409`).
- [ ] RLS policies are applied with `app.user_id` and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid access token it responds `401` with `WWW-Authenticate: Bearer`; identity and role are derived exclusively from the token.
- [ ] The rate limit `rl:invitations:u:{user_id}:{window}` (20 requests per user every 3600 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `204`: invitation cancelled successfully, with no response body.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `403`: the requester is not an active `OWNER` of the complex (`FORBIDDEN`).
- [ ] `404`: the complex or the invitation does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: the invitation is not pending (`INVITATION_NOT_PENDING`) or has already expired (`INVITATION_EXPIRED`).
- [ ] `422`: invalid identifiers (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

### Module 3 – Complexes and sports zones

#### US-301: Create a sports zone in a complex

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to create sports zones in my complex,
**So that** I can offer the spaces that clients will be able to book.

**Endpoint:** `POST /api/v1/complexes/{complex_id}/zones`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** High (P0)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `name`, `sport`, `surface` and `capacity`. Additional fields, incorrect types or `null` respond `422`; strings are trimmed before validating length; a `Content-Type` other than `application/json` responds `415`.
- [ ] `name` and `sport` are required; `surface` and `capacity` are optional (they can be omitted, but not sent as `null`).
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `name`: Must be between 3 and 100 characters after removing leading and trailing spaces.
- [ ] `sport`: Must be exactly one of the accepted values (`FOOTBALL`, `FUTSAL`, `BASKETBALL`, `VOLLEYBALL`, `TENNIS`, `PADEL`, `BADMINTON`, `SQUASH`). It is not normalized: other uppercase forms or values are rejected.
- [ ] `surface`: optional; if sent, it must be between 1 and 50 characters after removing leading and trailing spaces.
- [ ] `capacity`: optional; if sent, it must be an integer between 1 and 100 (a boolean or a decimal is not accepted).

**Business rules**

- [ ] The requester must be `OWNER` and/or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The zone's complex is taken exclusively from the path; the body cannot indicate it.
- [ ] The zone is created with `status = 'ACTIVE'` and `slot_duration_minutes = 60`; the client cannot send either of the two.
- [ ] The zone is created without operating hours; while they are not configured, it has no availability.
- [ ] The `name` must be unique within the complex, case-insensitively; if it already exists, it responds `409` (`ZONE_NAME_ALREADY_EXISTS`).
- [ ] A complex can have a maximum of 50 zones, counting those in any status; when exceeded it responds `409` (`ZONE_LIMIT_REACHED`).

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the zone insertion executes in an atomic transaction; uniqueness and integrity constraints are guaranteed in the database.
- [ ] Name uniqueness is guaranteed with a unique index on `(complex_id, lower(name))`: if two simultaneous requests use the same name, exactly one responds `201` and the other `409` (`UNIQUE` constraint, not a prior check).
- [ ] Before counting the zones, the complex row is locked with `SELECT ... FOR UPDATE`, so that simultaneous creations do not exceed the limit of 50.
- [ ] The RLS insert policy of `sports_zones` requires `complex_id` to correspond to a complex where the user (`app.user_id`) has an `ACTIVE` membership as `OWNER` or `MANAGER`.
- [ ] `created_at` and `updated_at` are assigned with the current database date.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the role is evaluated against the database on each request.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`zone_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `201`: zone created; includes `id`, `complex_id`, `name`, `sport`, `surface`, `capacity`, `status`, `slot_duration_minutes`, `created_at` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: a zone with that name already exists in the complex (`ZONE_NAME_ALREADY_EXISTS`) or the complex reached the maximum number of zones (`ZONE_LIMIT_REACHED`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-302: Query the catalog of complexes with all public data

**As** an authenticated user,
**I want** to query in a single place the catalog of sports complexes with their public data, zones, schedules and booking policies,
**So that** I can find where and which zones I can book.

**Endpoint:** `GET /api/v1/complexes`
**Requires Authentication:** Yes, valid access token.
**Rate limit:** `rl:catalog:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** L
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; any additional data, including unknown query parameters, is ignored.
- [ ] `q`: optional; if sent, it must be between 2 and 100 characters after removing leading and trailing spaces.
- [ ] `city`: optional; if sent, it must be between 1 and 100 characters after removing leading and trailing spaces.
- [ ] `sport`: optional; if sent, it must be one of the accepted sports (`FOOTBALL`, `FUTSAL`, `BASKETBALL`, `VOLLEYBALL`, `TENNIS`, `PADEL`, `BADMINTON`, `SQUASH`).
- [ ] `slug`: optional; if sent, it must comply with the format `^[a-z0-9]+(-[a-z0-9]+)*$` and be between 3 and 80 characters.
- [ ] `limit`: integer between 1 and 50; defaults to 20. `cursor`: optional, opaque string of up to 256 characters as returned by the previous response; an invalid value responds `422`.

**Business rules**

- [ ] The request requires a valid access token; if it is missing, invalid, expired or cannot be verified, it responds `401` (`INVALID_TOKEN`) and the catalog is not queried.
- [ ] The catalog lists all complexes ordered by name (case-insensitively) and then by `id`, with cursor-based pagination: the response includes `next_cursor`, which is `null` on the last page.
- [ ] Catalog filters are combined with `AND`: `q` searches the text within the name case-insensitively (the characters `%`, `_` and `\` are treated as literal text), `city` matches exactly case-insensitively, `slug` matches exactly and `sport` returns only complexes with at least one `ACTIVE` zone of that sport.
- [ ] Each catalog item includes the complex's public data and its list of zones, ordered by name: `id`, `name`, `slug`, `description`, `address`, `city`, `timezone`, `sports`, `booking_policies` and `zones`.
- [ ] `sports` contains the distinct sports of its `ACTIVE` zones, in alphabetical order (an empty list if it has none).
- [ ] For all requesters, only `ACTIVE` zones are listed. Each zone includes `id`, `name`, `sport`, `surface`, `capacity`, `status`, `slot_duration_minutes` and `operating_hours` ordered by `day_of_week` and `opens_at` (an empty list if not configured). `opens_at` and `closes_at` are exposed in `HH:MM`; the persisted value `1440` is serialized as `24:00`.
- [ ] `booking_policies` includes the current values of `min_advance_minutes`, `max_advance_days`, `cancellation_deadline_hours` and `max_active_bookings_per_client`.
- [ ] A complex without visible zones appears in the catalog with `zones: []`.
- [ ] No response includes `created_by`, memberships, emails or other data about the complex's people.

**Persistence and integrity**

- [ ] The operation only reads; it does not modify any table. The reads of a single request are made in a single read-only transaction.
- [ ] The reads query only public columns, with RLS policies that show all complexes, only `ACTIVE` zones with their operating hours and the complex's booking policies.
- [ ] Queries are parameterized; no input value is concatenated into the SQL.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token. Only the complex's and zone's public columns are exposed (the rest never leaves the database).
- [ ] The rate limit `rl:catalog:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before accessing the database; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: includes `items: [{ id, name, slug, description, address, city, timezone, sports, booking_policies: { min_advance_minutes, max_advance_days, cancellation_deadline_hours, max_active_bookings_per_client }, zones: [{ id, name, sport, surface, capacity, status, slot_duration_minutes, operating_hours: [{ day_of_week, opens_at, closes_at }] }] }]` and `next_cursor`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `422`: invalid query parameters (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-303: Update the data of a sports zone

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to update the data of a sports zone,
**So that** the information clients see remains correct.

**Endpoint:** `PATCH /api/v1/complexes/{complex_id}/zones/{zone_id}`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains at most `name`, `sport`, `surface` and `capacity`, and at least one of them. An empty body, additional fields (including `status` and `slot_duration_minutes`) or incorrect types respond `422`; strings are trimmed before validating length; a `Content-Type` other than `application/json` responds `415`.
- [ ] Only `surface` and `capacity` accept `null`, which clears their value; `name` and `sport` cannot be `null`.
- [ ] `complex_id` and `zone_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `name`: Must be between 3 and 100 characters after removing leading and trailing spaces.
- [ ] `sport`: Must be exactly one of the accepted values (`FOOTBALL`, `FUTSAL`, `BASKETBALL`, `VOLLEYBALL`, `TENNIS`, `PADEL`, `BADMINTON`, `SQUASH`).
- [ ] `surface`: if sent with a value, it must be between 1 and 50 characters after removing leading and trailing spaces.
- [ ] `capacity`: if sent with a value, it must be an integer between 1 and 100.

**Business rules**

- [ ] The requester must be `OWNER` and/or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The zone must belong to the indicated complex; a nonexistent zone or one from another complex responds `404`.
- [ ] Only the sent fields are modified; the others keep their value.
- [ ] A zone can be updated in any status (`ACTIVE`, `INACTIVE` or `MAINTENANCE`).
- [ ] If the new `name` is already used by another zone of the complex (case-insensitively), it responds `409` (`ZONE_NAME_ALREADY_EXISTS`).
- [ ] If no sent value differs from the current one, the operation is idempotent: it responds `200` with the current state without modifying `updated_at`.
- [ ] The update does not modify or cancel the zone's existing bookings.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; integrity constraints are guaranteed in the database.
- [ ] The update executes with a condition on `id` and `complex_id`, modifies only the sent columns and only affects the row if some value changes (`IS DISTINCT FROM`), so as not to touch rows without a real change.
- [ ] If the `UPDATE` affects one row, `updated_at` is updated with the current database date; if it affects zero rows, the zone is queried by `id` and `complex_id`: if it does not exist it responds `404`; if it exists it responds `200` without modifying the row.
- [ ] If two simultaneous requests modify different fields of the same zone, both changes are kept; if they modify the same field, the last write prevails.
- [ ] Name uniqueness is guaranteed with the unique index `(complex_id, lower(name))`; the violation is translated to `409`, never to `500`.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the role is evaluated against the database on each request.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] A zone from another complex cannot be modified even if the path identifiers are manipulated.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`zone_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: zone updated or unchanged; includes `id`, `complex_id`, `name`, `sport`, `surface`, `capacity`, `status`, `slot_duration_minutes`, `created_at` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex or the zone does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: another zone with that name already exists in the complex (`ZONE_NAME_ALREADY_EXISTS`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-304: Change the status of a sports zone

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to change a zone's status between active, inactive or under maintenance,
**So that** I can control whether clients can book it.

**Endpoint:** `PATCH /api/v1/complexes/{complex_id}/zones/{zone_id}/status`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** S
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `status` and `reason`. Additional fields, incorrect types, `null` or absence of `status` respond `422`; strings are trimmed before validation; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id` and `zone_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `status`: limited to `ACTIVE`, `INACTIVE` or `MAINTENANCE`.
- [ ] `reason`: required when `status` is `INACTIVE` or `MAINTENANCE`, with between 3 and 255 characters after removing leading and trailing spaces; if `status` is `ACTIVE`, it must not be sent.

**Business rules**

- [ ] The requester must be `OWNER` and/or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The zone must belong to the indicated complex; a nonexistent zone or one from another complex responds `404`.
- [ ] Changing to the same status the zone already has is idempotent: it responds `200` without modifying `updated_at`, `status_reason` or the bookings, and without inserting events into Outbox.
- [ ] An `INACTIVE` or `MAINTENANCE` zone stops appearing in the catalog (US-302) and does not accept new bookings.
- [ ] Moving to `INACTIVE` or `MAINTENANCE` does not automatically cancel confirmed bookings. Future bookings and those in progress keep their `starts_at`, `ends_at` and `status`; staff can explicitly cancel them through US-408, which records the reason and triggers the corresponding notification.
- [ ] Moving to `ACTIVE` makes the zone visible and bookable again, `status_reason` becomes `NULL` and the preserved bookings are not restored or modified.
- [ ] The status change does not modify the zone's operating hours or slot duration.
- [ ] The status change does not insert events into `outbox_events` nor send emails by itself; the only cancellation path with notification is US-408.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the zone status change and its `updated_at` execute in a single atomic transaction. The operation does not modify `bookings`, so it does not require cancelling or inserting events into `outbox_events`.
- [ ] The zone is locked with `SELECT ... FOR UPDATE` before changing the status. Booking creation and rescheduling lock the same row with `FOR SHARE` and validate `status = 'ACTIVE'` within their transaction, so no new booking is confirmed on a zone that stops being active.
- [ ] The received `reason` is persisted in `sports_zones.status_reason` to record the status change; it is not copied to any booking.
- [ ] If two simultaneous requests change the status of the same zone, they are applied one after the other and the final status is the last one's; bookings are not modified.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the role is evaluated against the database on each request.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] The operation does not publish events or send emails; it does not expose booking data.
- [ ] Logs include `request_id`, route, method, status, duration, `user_id`/`complex_id`/`zone_id` and the previous and new status; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: status updated or unchanged; includes `id`, `status`, `status_reason` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex or the zone does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid identifiers, status or reason, or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-305: Configure the operating hours and slot duration of a zone

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to configure the days and operating windows in which a zone operates and its booking slot duration,
**So that** I can define when and at which intervals clients can book it.

**Endpoint:** `PUT /api/v1/complexes/{complex_id}/zones/{zone_id}/schedule`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** High (P0)
**Size:** L
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `slot_duration_minutes` and `operating_hours`, both required. Additional fields, incorrect types, `null` or absence of fields respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id` and `zone_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `slot_duration_minutes`: integer multiple of 15 between 15 and 240.
- [ ] `operating_hours`: list of between 0 and 28 operating windows, with a maximum of 4 per `day_of_week`. Each window contains exclusively `day_of_week`, `opens_at` and `closes_at`.
- [ ] `day_of_week`: integer between 1 and 7 (ISO day; 1 = Monday).
- [ ] `opens_at` and `closes_at`: strings with 24-hour `HH:MM` format. `opens_at` ranges from `00:00` to `23:59`; `closes_at` ranges from `00:01` to `24:00` (`24:00` indicates closing at midnight). A window belongs to a single day and cannot cross midnight.
- [ ] In each window, `opens_at` must be earlier than `closes_at`, and its duration must be a multiple of `slot_duration_minutes`.
- [ ] Windows on the same day cannot overlap (they can be contiguous). Window errors indicate their position and the field in `details`.

**Business rules**

- [ ] The requester must be `OWNER` and/or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] The zone must belong to the indicated complex; a nonexistent zone or one from another complex responds `404`.
- [ ] The operation completely replaces the previous configuration: the zone's previous windows are replaced by the sent ones. An empty list leaves the zone without operating hours and therefore without availability.
- [ ] Sending the same configuration the zone already has responds `200` with the same result (idempotent).
- [ ] Operating hours are interpreted in the complex's local time (`sports_complexes.timezone`) and stored as local minutes since midnight (`opens_at_minute`, `closes_at_minute`); they are not converted to UTC nor represented with `datetime.time`.
- [ ] A zone can be configured in any status (`ACTIVE`, `INACTIVE` or `MAINTENANCE`).
- [ ] The new configuration applies to availability and to bookings created or rescheduled from that moment; it does not retroactively modify, invalidate or cancel existing bookings, which keep their `starts_at` and `ends_at`. Availability for new bookings always uses the current operating hours.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update of `slot_duration_minutes`, the deletion of the previous windows and the insertion of the new ones execute in a single atomic transaction.
- [ ] Conversion between `HH:MM` and local minutes is done in a single boundary function: `00:00 = 0`, `24:00 = 1440`; the response converts back to `HH:MM` and serializes `1440` as `24:00`. No endpoint or repository implements alternative conversions.
- [ ] The zone is locked with `SELECT ... FOR UPDATE` at the start of the transaction; if two simultaneous requests configure the same zone, they are applied one after the other and the result is exactly one of the complete configurations, never a mix.
- [ ] The database guarantees the integrity rules: `day_of_week` between 1 and 7, `opens_at_minute` between 0 and 1439, `closes_at_minute` between 1 and 1440, `opens_at_minute < closes_at_minute`, `slot_duration_minutes` a multiple of 15 between 15 and 240, and an exclusion constraint that prevents overlapping windows for the same zone and day.
- [ ] The exclusion constraint uses `EXCLUDE USING gist (zone_id WITH =, day_of_week WITH =, int4range(opens_at_minute, closes_at_minute, '[)') WITH &&)` and requires the `btree_gist` extension. The half-open range allows contiguous windows and does not allow windows that cross midnight; `24:00` is persisted as `1440`.
- [ ] `zone_operating_hours` references the zone with a composite foreign key `(zone_id, complex_id)`, so that the `complex_id` used by RLS cannot differ from the zone's.
- [ ] If `slot_duration_minutes` changes, the zone's `updated_at` is updated with the current database date.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `created_at`/`updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the role is evaluated against the database on each request.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Each window's `complex_id` is taken from the zone, never from the body.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`zone_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: configuration saved; includes `zone_id`, `slot_duration_minutes`, `operating_hours: [{ day_of_week, opens_at, closes_at }]` ordered by day and opening time, and the zone's `updated_at`. `opens_at` and `closes_at` are serialized in `HH:MM`; `1440` is returned as `24:00`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex or the zone does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data, overlapping windows or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

### Module 4 – Bookings

#### Common temporal rules (US-401, US-402, US-403)

- The reference time zone is `sports_complexes.timezone` (IANA). Operating hours are expressed in local minutes since midnight and bookings are persisted as `TIMESTAMPTZ` in UTC.
- `min_advance_minutes` is a real duration: `starts_at >= now() + min_advance_minutes`.
- `max_advance_days` are calendar days in the complex's time zone: with `local_date = (starts_at AT TIME ZONE timezone)::date` and `local_today = (now() AT TIME ZONE timezone)::date`, `local_today <= local_date <= local_today + max_advance_days` is required. `now() + max_advance_days * interval '1 day'` is not used; the deadline includes the entire local day.
- Slot generation is unique for US-401, US-402 and US-403: it starts from the local day's `opens_at_minute`, advances by `slot_duration_minutes` and resolves each local start to UTC. A slot is offered only if its `ends_at` does not exceed the resolved local closing time and if it meets the advance-notice windows.
- `ends_at = starts_at + slot_duration_minutes` as a real duration. On a daylight saving change, the local time of `ends_at` may not match the wall-clock sum; the real duration of the slot is preserved.
- Nonexistent local time (spring forward): the slot start is the first valid instant after the gap. Ambiguous local time (fall back): the first occurrence is used. Closing is resolved with the same rule. A slot that does not fit completely before closing is omitted and, if two candidates resolve to the same instant, a single slot is kept.
- The same domain function is reused in availability, creation and rescheduling; no endpoint implements its own conversions.
- Schedule changes do not alter existing bookings: they keep `starts_at` and `ends_at`; availability for new bookings uses the current configuration.

#### US-401: Book a sports zone at an available time

**As** a `CLIENT`,
**I want** to book an active sports zone at an available time,
**So that** I can secure my space without anyone else being able to book it.

**Endpoint:** `POST /api/v1/complexes/{complex_id}/zones/{zone_id}/bookings`
**Requires Authentication:** Yes, valid access token.
**Rate limit:** `rl:bookings:u:{user_id}:{window}`: 20 requests per user every 60 s.

**Priority:** High (P0)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `starts_at`. The field is required. Additional fields, incorrect types, `null` or absence of the field respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id` and `zone_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `starts_at`: ISO 8601 string with an explicit time zone (`Z` or offset, for example `-05:00`), with seconds and fractions at zero. A date without a time zone is rejected.

**Business rules**

- [ ] The zone must exist and belong to the indicated complex; otherwise it responds `404`. If it exists but its status is not `ACTIVE`, it responds `409` (`ZONE_NOT_ACTIVE`).
- [ ] The booking is created for the token's user; the body cannot indicate the client or the complex (it is taken from the zone).
- [ ] A booking is active when `status = 'CONFIRMED'` and `ends_at > now()`; `CONFIRMED` bookings with `ends_at <= now()` are considered `COMPLETED` in a derived way and are not persisted with that status.
- [ ] If the user already has their own `CONFIRMED` booking with the same zone, `starts_at` and `ends_at`, the request is a retry: it responds `200` with that booking, without creating another and without evaluating the active-booking limit.
- [ ] `starts_at` must correspond to the start of a valid slot within a `zone_operating_hours` window of the corresponding local day. The slot must respect alignment with `slot_duration_minutes`, have a real duration equal to that configuration and end before or exactly at the window's closing time. Local time resolution must account for daylight saving time (DST) changes: nonexistent times are resolved to the first valid instant after the gap and ambiguous times use their first occurrence. If these conditions are not met, it responds `422` (`INVALID_SLOT`).
- [ ] The complex's policy is respected: `starts_at >= now() + min_advance_minutes` and `local_date(starts_at) <= local_date(now()) + max_advance_days` calendar days in the complex's time zone; otherwise it responds `422` (`OUTSIDE_BOOKING_WINDOW`). `now() + max_advance_days * interval '1 day'` is not used.
- [ ] The user cannot exceed `max_active_bookings_per_client` active bookings in that complex, where active means those with `status = 'CONFIRMED'` and `ends_at > now()`; upon reaching it, it responds `409` (`BOOKING_LIMIT_REACHED`).
- [ ] The booking is created with `status = 'CONFIRMED'`, `ends_at = starts_at + slot_duration_minutes` and no cancellation data.
- [ ] If the slot is already occupied by a non-cancelled booking of another client, it responds `409` (`SLOT_ALREADY_BOOKED`).

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()` for auditing; validation and insertion execute in a single atomic transaction.
- [ ] Non-overlap is guaranteed in the database with an exclusion constraint (`btree_gist`) on `zone_id` and `tstzrange(starts_at, ends_at)` (half-open interval, so contiguous slots do not collide) for bookings with `status <> 'CANCELLED'`; the violation is resolved by querying the equivalent booking and, if it does not exist, is translated to `409`, never to `500`.
- [ ] If several simultaneous requests compete for the same slot, exactly one creates the booking; equivalent requests from the same client respond `200` with that booking and the others `409`, even with multiple API instances.
- [ ] If the insertion violates the exclusion constraint, it is rolled back to a savepoint and the equivalent `CONFIRMED` booking of the same `client_id`, `zone_id`, `starts_at` and `ends_at` is queried; if it exists, it responds `200` with it; if the interval is occupied by another booking, it responds `409` (`SLOT_ALREADY_BOOKED`). The decision is made from the violation confirmed in PostgreSQL, not from a prior query susceptible to races.
- [ ] Before counting active bookings, a transactional lock (`pg_advisory_xact_lock`) is acquired on the `(client_id, complex_id)` pair, so that two simultaneous requests from the same client do not exceed the limit.
- [ ] A `SECURITY DEFINER` trigger on `bookings` runs on `INSERT` and on updates of `zone_id`, `starts_at`, `ends_at` or `status` when the new row ends up `CONFIRMED`; it locks the zone row with `FOR SHARE`, verifies that the zone belongs to the complex and requires `status = 'ACTIVE'`, so that no booking is confirmed on a zone that is being deactivated (US-304). The function uses a fixed `search_path` and does not use dynamic SQL.
- [ ] `bookings` references the zone with a composite foreign key `(zone_id, complex_id)`, and `ends_at > starts_at` is guaranteed with a `CHECK` constraint.
- [ ] The RLS policies described in the `Security, multi-tenancy and data access` section are applied: the client only sees and creates their own bookings; active staff see those of their complex and can only cancel them according to the corresponding story.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the booking's client is never accepted from the body.
- [ ] The rate limit `rl:bookings:u:{user_id}:{window}` (20 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] A nonexistent zone or one from another complex responds `404` even if the path identifiers are manipulated.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`zone_id`/`booking_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `201`: booking created; includes `id`, `complex_id`, `zone_id`, `client_id`, `starts_at`, `ends_at`, `status` and `created_at`, and the `Location` header with the booking's path.
- [ ] `200`: retry of an already-created own booking; same body as `201`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the zone does not exist or does not belong to the complex (`NOT_FOUND`).
- [ ] `409`: the slot is already booked (`SLOT_ALREADY_BOOKED`), the zone is not active (`ZONE_NOT_ACTIVE`) or the maximum number of active bookings was reached (`BOOKING_LIMIT_REACHED`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`), a time that does not correspond to a zone slot (`INVALID_SLOT`) or outside the allowed advance notice (`OUTSIDE_BOOKING_WINDOW`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-402: Query the availability of a complex's zones

**As** a user (with or without a signed-in session),
**I want** to query the available times of a complex's zones on a date,
**So that** I can choose a slot before booking.

**Endpoint:** `GET /api/v1/complexes/{complex_id}/availability`
**Requires Authentication:** The token is optional.
**Rate limit:** `rl:catalog:ip:{ip}:{window}`: 60 requests per IP every 60 s (anonymous); `rl:catalog:u:{user_id}:{window}`: 120 requests per user every 60 s (valid token).

**Priority:** High (P0)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; any additional data, including unknown query parameters, is ignored.
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `date`: required, with `YYYY-MM-DD` format and a valid calendar date; it is interpreted as the complex's local date.
- [ ] `sport`: optional; if sent, it must be one of the accepted sports (`FOOTBALL`, `FUTSAL`, `BASKETBALL`, `VOLLEYBALL`, `TENNIS`, `PADEL`, `BADMINTON`, `SQUASH`).
- [ ] `zone_id`: optional; if sent, it must have a valid UUID format.

**Business rules**

- [ ] If the token is valid, the per-user limit is used; if it is missing, invalid or cannot be validated, the request is anonymous and limited by IP. An invalid token never prevents querying availability.
- [ ] A nonexistent complex responds `404`.
- [ ] `date` must be between the complex's current local date and that date plus `max_advance_days` calendar days; otherwise it responds `422` (`OUTSIDE_BOOKING_WINDOW`).
- [ ] The complex's `ACTIVE` zones are considered, filtered with `AND` by `sport` and `zone_id` when sent. If `zone_id` does not correspond to an active zone of the complex, it responds `200` with `zones: []`.
- [ ] The available slots of each zone must be generated from its `zone_operating_hours` windows for the weekday of `date`, starting at `opens_at_minute` and advancing in intervals of `slot_duration_minutes`. Each slot must have that real duration and end before or exactly at the window's closing time. Local time resolution must account for daylight saving time (DST) changes: nonexistent times are resolved to the first valid instant after the gap and ambiguous times use their first occurrence. Slots that do not fit completely in the window must be omitted, and duplicates must be avoided when several candidates resolve to the same instant.
- [ ] A slot is returned only if it is not occupied by a booking with `status <> 'CANCELLED'`, if `starts_at >= now() + min_advance_minutes` and if `local_date(starts_at) <= local_date(now()) + max_advance_days` calendar days in the complex's time zone.
- [ ] Each active zone that meets the filters appears in the response, with `slots: []` if it has no available slots; zones are ordered by name and slots by `starts_at`.
- [ ] The response only indicates which slots are free; it does not expose who booked or data from any booking.
- [ ] Availability is informative: the definitive booking is validated by US-401, so a returned slot may be taken before it is booked.

**Persistence and integrity**

- [ ] The operation only reads; it does not modify any table. The reads of a single request are made in a single read-only transaction with a consistent snapshot.
- [ ] The reads query only public columns of zones, operating hours and booking policies, and only `zone_id`, `starts_at`, `ends_at` and `status` of `bookings`; with RLS policies that only show bookings of `ACTIVE` zones with `status <> 'CANCELLED'`, necessary to calculate availability.
- [ ] Queries are parameterized; no input value is concatenated into the SQL.

**Security**

- [ ] The endpoint is public; the response does not include people's data (clients, emails or booking identifiers).
- [ ] The `rl:catalog` rate limit is evaluated after optional authentication and before accessing the database, with `rl:catalog:ip:{ip}:{window}` (60 requests per IP every 60 s) or, with a valid token, `rl:catalog:u:{user_id}:{window}` (120 requests per user every 60 s); when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: includes `complex_id`, `timezone`, `date` and `zones: [{ zone_id, name, sport, slot_duration_minutes, slots: [{ starts_at, ends_at }] }]`, with instants in UTC.
- [ ] `404`: the complex does not exist (`NOT_FOUND`).
- [ ] `422`: invalid parameters or identifier (`VALIDATION_ERROR`) or date outside the booking window (`OUTSIDE_BOOKING_WINDOW`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-403: Reschedule their own booking

**As** a `CLIENT`,
**I want** to reschedule one of my bookings to another date, time or zone,
**So that** I can adjust it without having to cancel it and book again.

**Endpoint:** `PATCH /api/v1/bookings/{booking_id}`
**Requires Authentication:** Yes, valid access token and `CLIENT` role.
**Rate limit:** `rl:bookings:u:{user_id}:{window}`: 20 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains at most `zone_id` and `starts_at`, and at least one of them. An empty body, additional fields, incorrect types or `null` respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `booking_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `zone_id`: if sent, it must have a valid UUID format.
- [ ] `starts_at`: if sent, an ISO 8601 string with an explicit time zone (`Z` or offset), with seconds and fractions at zero.

**Business rules** (evaluated in this order)

- [ ] The booking must belong to the token's user; a nonexistent or foreign booking responds `404`.
- [ ] Only a booking with `status = 'CONFIRMED'` and `starts_at > now()` is rescheduled; if it is cancelled, has already started or has already ended, it responds `409` (`BOOKING_NOT_MODIFIABLE`).
- [ ] The original booking must start at least `cancellation_deadline_hours` hours in advance; otherwise it responds `409` (`RESCHEDULE_DEADLINE_PASSED`). It is the same deadline as cancellation (US-404), so that rescheduling cannot be used to release a slot after the deadline.
- [ ] If only `starts_at` is sent, the zone is kept; if only `zone_id` is sent, the current `starts_at` is kept. The new zone must belong to the booking's complex; a nonexistent zone or one from another complex responds `404`, and a zone that is not `ACTIVE` responds `409` (`ZONE_NOT_ACTIVE`).
- [ ] If the resulting zone and `starts_at` are equal to the current ones, the operation is idempotent: it responds `200` with the booking without modifying `updated_at`.
- [ ] The new `starts_at` must correspond to the start of a valid slot within a `zone_operating_hours` window of the local day corresponding to the new zone. The slot must respect alignment with `slot_duration_minutes`, have a real duration equal to that configuration and end before or exactly at the window's closing time. Local time resolution must account for daylight saving time (DST) changes: nonexistent times are resolved to the first valid instant after the gap and ambiguous times use their first occurrence. If these conditions are not met, it responds `422` (`INVALID_SLOT`).
- [ ] The new `starts_at` must respect the policy: `starts_at >= now() + min_advance_minutes` and `local_date(starts_at) <= local_date(now()) + max_advance_days` calendar days in the complex's time zone; otherwise it responds `422` (`OUTSIDE_BOOKING_WINDOW`). `now() + max_advance_days * interval '1 day'` is not used.
- [ ] The booking keeps its `id` and is updated in place: `zone_id`, `starts_at` and `ends_at` change (`starts_at` plus the new zone's slot duration).
- [ ] If the new slot is already occupied by another non-cancelled booking, it responds `409` (`SLOT_ALREADY_BOOKED`) and the original booking does not change. The booking itself does not count as a conflict, so it can be moved to a slot that overlaps with the current one.
- [ ] Rescheduling does not change the number of active bookings, so `max_active_bookings_per_client` is not re-evaluated.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update executes in a single atomic transaction: it completes entirely or is not applied.
- [ ] Locks are always taken in this order: first the involved zones with `FOR SHARE` (in ascending `id` order, through the `SECURITY DEFINER` trigger of `bookings` described in US-401) and then the booking with `FOR UPDATE`; this avoids deadlocks with US-304. If PostgreSQL still detects a deadlock, the transaction is retried once.
- [ ] Non-overlap is guaranteed by the exclusion constraint of `bookings` (zone and time range for `status <> 'CANCELLED'`); the violation is translated to `409`, never to `500`.
- [ ] If two simultaneous requests try to move different bookings to the same slot, exactly one succeeds and the other receives `409`.
- [ ] The update executes with a condition on `id`, `client_id`, `status = 'CONFIRMED'` and the booking's `complex_id`, so as not to modify bookings outside the user's scope or from another complex.
- [ ] `updated_at` is updated with the current database date; RLS policies are applied with `app.user_id` (the user only sees and modifies their own bookings).

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the booking's client cannot be changed.
- [ ] The rate limit `rl:bookings:u:{user_id}:{window}` (20 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Another person's booking responds `404`, indistinguishable from a nonexistent one.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`booking_id`, and the previous and new zones when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: booking rescheduled or unchanged; includes `id`, `complex_id`, `zone_id`, `client_id`, `starts_at`, `ends_at`, `status` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the booking does not exist or is not the user's, or the new zone does not exist in the complex (`NOT_FOUND`).
- [ ] `409`: the slot is already booked (`SLOT_ALREADY_BOOKED`), the booking cannot be modified (`BOOKING_NOT_MODIFIABLE`), the rescheduling deadline has passed (`RESCHEDULE_DEADLINE_PASSED`) or the new zone is not active (`ZONE_NOT_ACTIVE`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data or disallowed fields (`VALIDATION_ERROR`), a time that does not correspond to a zone slot (`INVALID_SLOT`) or outside the allowed advance notice (`OUTSIDE_BOOKING_WINDOW`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-404: Cancel their own booking

**As** a `CLIENT`,
**I want** to cancel one of my bookings within the deadline allowed by the complex,
**So that** I can release the time when I can no longer attend.

**Endpoint:** `DELETE /api/v1/bookings/{booking_id}`
**Requires Authentication:** Yes, valid access token and `CLIENT` role.
**Rate limit:** `rl:bookings:u:{user_id}:{window}`: 20 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** S
**Estimate:** 2

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; only `booking_id` is validated as a path UUID. An invalid identifier responds `422`; `415` and body field validation do not apply.
- [ ] Any additional data in the request is ignored.

**Business rules**

- [ ] The booking must belong to the token's user; a nonexistent or foreign booking responds `404`.
- [ ] Only a booking with `status = 'CONFIRMED'` that starts at least `cancellation_deadline_hours` hours in advance is cancelled (`starts_at >= now() + cancellation_deadline_hours`) and `starts_at > now()`.
- [ ] If the booking is already `CANCELLED`, has already started or has already ended, it responds `409` (`BOOKING_NOT_CANCELLABLE`) without modifying it.
- [ ] If fewer hours remain than the complex's cancellation deadline, it responds `409` (`CANCELLATION_DEADLINE_PASSED`) without modifying it.
- [ ] Cancellation changes `status` to `CANCELLED`, records `cancelled_at` with the current database date and `cancelled_by` with the token's user; it does not require a reason, so `cancellation_reason` remains `NULL`.
- [ ] The cancelled slot becomes immediately available for new bookings (US-401, US-402).
- [ ] The booking is kept for auditing; it is not physically deleted.
- [ ] The operation is not idempotent: repeating an already-applied `DELETE` responds `409` (`BOOKING_NOT_CANCELLABLE`).
- [ ] A cancellation made by the client themselves does not insert events into Outbox nor send emails (RF-503 only applies to cancellations made by `OWNER` or `MANAGER` through US-408).

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update of `status`, `cancelled_at` and `cancelled_by` executes in an atomic transaction.
- [ ] Cancellation executes with a conditional update on `bookings` joined to `complex_booking_policies`: `WHERE id = :booking_id AND client_id = :user_id AND status = 'CONFIRMED' AND starts_at >= now() + make_interval(hours => cancellation_deadline_hours) AND starts_at > now()`.
- [ ] If no row is affected, the booking is queried: if it does not exist or is not the user's, it responds `404`; if it exists, it responds `409` with the corresponding code (`CANCELLATION_DEADLINE_PASSED` or `BOOKING_NOT_CANCELLABLE`).
- [ ] The same condition resolves races with another cancellation (US-408): exactly one operation wins and the loser receives `409`. In the event of a simultaneous reschedule (US-403), they are applied one after the other and the second re-evaluates the booking's status.
- [ ] RLS policies are applied with `app.user_id` (the user only sees and modifies their own bookings) and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token.
- [ ] The rate limit `rl:bookings:u:{user_id}:{window}` (20 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Another person's booking responds `404`, indistinguishable from a nonexistent one.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`booking_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `204`: booking cancelled successfully, with no response body.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the booking does not exist or is not the user's (`NOT_FOUND`).
- [ ] `409`: the booking cannot be cancelled due to its status (`BOOKING_NOT_CANCELLABLE`) or the cancellation deadline has passed (`CANCELLATION_DEADLINE_PASSED`).
- [ ] `422`: invalid identifier (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-405: Query my bookings

**As** a `CLIENT`,
**I want** to query my bookings filtering by date, zone and status,
**So that** I can know what I have booked and review those that have already passed or were cancelled.

**Endpoint:** `GET /api/v1/bookings`
**Requires Authentication:** Yes, valid access token and `CLIENT` role.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; any additional data, including unknown query parameters, is ignored.
- [ ] `date_from` and `date_to`: optional, with `YYYY-MM-DD` format and a valid calendar date. If both are sent, `date_from` cannot be later than `date_to`.
- [ ] `zone_id`: optional; if sent, it must have a valid UUID format.
- [ ] `status`: optional; if sent, it must be `CONFIRMED`, `COMPLETED` or `CANCELLED`. `COMPLETED` is an effective derived status, not a persisted value.
- [ ] `order`: optional, `asc` or `desc`; defaults to `desc`.
- [ ] `limit`: integer between 1 and 50; defaults to 20. `cursor`: optional, opaque string of up to 256 characters as returned by the previous response; an invalid value, or one issued with another `order`, responds `422`.

**Business rules**

- [ ] Only bookings whose `client_id` is the token's user are returned, even if that user is also an `OWNER` or `MANAGER` of some complex; other people's bookings never appear.
- [ ] `date_from` and `date_to` are inclusive local dates and are interpreted in the time zone of each booking's complex: a booking matches if its `starts_at` falls between the start of the local day of `date_from` and the end of the local day of `date_to`.
- [ ] Filters are combined with `AND`. A `zone_id` that has no bookings from the user produces an empty list, not an error.
- [ ] The status that is filtered and returned is the effective one: `CANCELLED` if the booking is cancelled; `COMPLETED` if it is `CONFIRMED` and its `ends_at` has already passed; `CONFIRMED` if it is `CONFIRMED` and its `ends_at` is later than `now()`. The `CONFIRMED` filter is translated to `status = 'CONFIRMED' AND ends_at > now()`; `COMPLETED` to `status = 'CONFIRMED' AND ends_at <= now()`; `CANCELLED` to `status = 'CANCELLED'`. A persisted `COMPLETED` status is never queried.
- [ ] The result is ordered by `starts_at` and `id` in the direction of `order`, with cursor-based pagination: the response includes `next_cursor`, which is `null` on the last page.
- [ ] Each booking includes the complex `{ id, name, slug }` and the zone `{ id, name, sport }` (with their current values, even if the zone is no longer active).
- [ ] Cancelled bookings include `cancelled_at`, `cancellation_reason` and `cancelled_by_type`: `CLIENT` if the user cancelled it themselves and `STAFF` if an `OWNER` or `MANAGER` cancelled it. Data about who cancelled is not exposed.

**Persistence and integrity**

- [ ] The operation only reads; it does not modify any table. The reads of a single request are made in a single read-only transaction.
- [ ] The query explicitly filters by `client_id = :user_id`, in addition to the RLS policies with `app.user_id`, so that a complex's staff does not receive other clients' bookings.
- [ ] Date limits are calculated in the database with each complex's time zone, so that days with daylight saving time changes (23 or 25 hours) are resolved correctly.
- [ ] Queries are parameterized; no input value is concatenated into the SQL.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and a `client_id` from the request is not accepted.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before accessing the database; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id` when applicable; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: includes `items: [{ id, complex: { id, name, slug }, zone: { id, name, sport }, starts_at, ends_at, status, cancelled_at, cancelled_by_type, cancellation_reason, created_at }]` and `next_cursor`; instants in UTC. An empty list responds `200`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `422`: invalid query parameters (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-406: Query a complex's bookings

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to query my complex's bookings filtering by date, zone, status and client,
**So that** I can operate day to day and serve clients.

**Endpoint:** `GET /api/v1/complexes/{complex_id}/bookings`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004, RNF-005

**Input validation**

- [ ] The request has no body; any additional data, including unknown query parameters, is ignored.
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `date_from` and `date_to`: optional, with `YYYY-MM-DD` format and a valid calendar date. If both are sent, `date_from` cannot be later than `date_to`.
- [ ] `zone_id` and `client_id`: optional; if sent, they must have a valid UUID format.
- [ ] `status`: optional; if sent, it must be `CONFIRMED`, `COMPLETED` or `CANCELLED`. `COMPLETED` is an effective derived status, not a persisted value.
- [ ] `order`: optional, `asc` or `desc`; defaults to `asc`.
- [ ] `limit`: integer between 1 and 50; defaults to 20. `cursor`: optional, opaque string of up to 256 characters as returned by the previous response; an invalid value, or one issued with another `order`, responds `422`.

**Business rules**

- [ ] The requester must be `OWNER` or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex. There is no `403` response, because every active member can query.
- [ ] Only bookings of the indicated complex are returned, from any client and any zone (including inactive ones).
- [ ] `date_from` and `date_to` are inclusive local dates of the complex (`sports_complexes.timezone`): a booking matches if its `starts_at` falls between the start of the local day of `date_from` and the end of the local day of `date_to`.
- [ ] Filters are combined with `AND`. A `zone_id` or `client_id` with no bookings in the complex produces an empty list, not an error.
- [ ] The status that is filtered and returned is the effective one: `CANCELLED` if the booking is cancelled; `COMPLETED` if it is `CONFIRMED` and its `ends_at` has already passed; `CONFIRMED` if it is `CONFIRMED` and its `ends_at` is later than `now()`. The `CONFIRMED` filter is translated to `status = 'CONFIRMED' AND ends_at > now()`; `COMPLETED` to `status = 'CONFIRMED' AND ends_at <= now()`; `CANCELLED` to `status = 'CANCELLED'`. A persisted `COMPLETED` status is never queried.
- [ ] The result is ordered by `starts_at` and `id` in the direction of `order`, with cursor-based pagination: the response includes `next_cursor`, which is `null` on the last page.
- [ ] Each booking includes the zone `{ id, name, sport }` and the client `{ id, full_name, email }`, necessary to serve them. No other user data is exposed.
- [ ] Cancelled bookings include `cancelled_at`, `cancelled_by`, `cancelled_by_type` (`CLIENT` or `STAFF`) and `cancellation_reason`.

**Persistence and integrity**

- [ ] The operation only reads; it does not modify any table. The reads of a single request are made in a single read-only transaction.
- [ ] RLS policies by `complex_id` with `app.user_id` limit the reading of `bookings` to complexes where the user has an `ACTIVE` membership.
- [ ] Client data is read through the `complex_booking_clients` view defined in `Security, multi-tenancy and data access`: it only exposes `id`, `full_name` and `email`, and limits rows to complexes where `app.user_id` has an `ACTIVE` membership; `users` remains without direct read access for staff.
- [ ] Date limits are calculated in the database with the complex's time zone, so that days with daylight saving time changes (23 or 25 hours) are resolved correctly.
- [ ] Queries are parameterized; no input value is concatenated into the SQL.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity is obtained only from the token and the role is evaluated against the database on each request.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before accessing the database; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Another complex's bookings cannot be queried even if identifiers or filters are manipulated.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable; they never include tokens, credentials or email addresses, not even the client's.

**HTTP responses**

- [ ] `200`: includes `items: [{ id, zone: { id, name, sport }, client: { id, full_name, email }, starts_at, ends_at, status, cancelled_at, cancelled_by, cancelled_by_type, cancellation_reason, created_at, updated_at }]` and `next_cursor`; instants in UTC. An empty list responds `200`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `422`: invalid query parameters or identifiers (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-407: Configure a complex's booking policies

**As** an `OWNER` of a sports complex,
**I want** to configure my complex's booking policies,
**So that** I can define how far in advance bookings and cancellations can be made, and how many active bookings each client can have.

**Endpoint:** `PATCH /api/v1/complexes/{complex_id}/booking-policies`
**Requires Authentication:** Yes, valid access token and `OWNER` role.
**Rate limit:** `rl:default:u:{user_id}:{window}`: 120 requests per user every 60 s.

**Priority:** High (P0)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains at most `min_advance_minutes`, `max_advance_days`, `cancellation_deadline_hours` and `max_active_bookings_per_client`, and at least one of them. An empty body, additional fields, incorrect types or `null` respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `min_advance_minutes`: integer between 0 and 10080 (7 days). Decimals and booleans are not accepted.
- [ ] `max_advance_days`: integer between 1 and 365; it represents calendar days in the complex's time zone, not exact 24-hour periods.
- [ ] `cancellation_deadline_hours`: integer between 0 and 720 (30 days).
- [ ] `max_active_bookings_per_client`: integer between 1 and 50.
- [ ] After applying the sent values over the current ones, `min_advance_minutes` must be less than `max_advance_days × 1440`; otherwise it responds `422` and modifies nothing, because no booking window would remain.

**Business rules**

- [ ] The requester must be `OWNER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; an active member without the `OWNER` role responds `403`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex.
- [ ] Only the sent values are modified; the others keep their current value. The complex's policies exist from its creation (US-104), so this operation never creates rows.
- [ ] Sending values equal to the current ones is idempotent: it responds `200` with the current policies without modifying `updated_at`.
- [ ] Changes take effect once confirmed and are evaluated on each operation: booking (US-401), rescheduling (US-403), availability queries (US-402) and cancellation (US-404). Existing bookings are not cancelled or modified, even if a client ends up above the new maximum of active bookings; they simply cannot book more until they drop below that maximum.
- [ ] The new cancellation deadline applies immediately to already-created bookings.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; integrity constraints are guaranteed in the database, including the rule `min_advance_minutes < max_advance_days × 1440` through a `CHECK` constraint, whose violation is translated to `422`, never to `500`.
- [ ] The update executes on the `complex_booking_policies` row whose `complex_id` is the path's, modifies only the sent columns and only affects the row if some value changes (`IS DISTINCT FROM`).
- [ ] If the `UPDATE` affects one row, `updated_at` is updated with the current database date; if it affects zero rows, the row exists and there were no changes, and it responds `200` without modifying it.
- [ ] If two simultaneous requests modify different fields, both changes are kept; if they modify the same field, the last write prevails.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity and role are derived exclusively from the token and the database, never from the body.
- [ ] The rate limit `rl:default:u:{user_id}:{window}` (120 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] Another complex's policies cannot be modified even if the path identifier is manipulated.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id` when applicable, and the previous and new values of each modified policy; they never include tokens, credentials or email addresses.

**HTTP responses**

- [ ] `200`: policies updated or unchanged; includes `complex_id`, `min_advance_minutes`, `max_advance_days`, `cancellation_deadline_hours`, `max_active_bookings_per_client` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `403`: the requester is not an active `OWNER` of the complex (`FORBIDDEN`).
- [ ] `404`: the complex does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid input data, disallowed fields or an empty booking window (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

#### US-408: Cancel a complex booking indicating the reason

**As** an `OWNER` or `MANAGER` of a sports complex,
**I want** to cancel a booking of my complex indicating the reason, without being subject to the cancellation deadline,
**So that** I can resolve unforeseen events at the complex and let the client know why.

**Endpoint:** `POST /api/v1/complexes/{complex_id}/bookings/{booking_id}/cancel`
**Requires Authentication:** Yes, valid access token and `ACTIVE` membership as `OWNER` or `MANAGER`.
**Publishes Event:** `booking.cancelled` **Rate limit:** `rl:bookings:u:{user_id}:{window}`: 20 requests per user every 60 s.

**Priority:** Medium (P1)
**Size:** M
**Estimate:** 3

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-002, RNF-003, RNF-004, RNF-005

**Input validation**

- [ ] The body is JSON and contains exclusively `reason`. The field is required, must be a text string and cannot be `null`. Additional fields or incorrect types respond `422`; a `Content-Type` other than `application/json` responds `415`.
- [ ] `complex_id` and `booking_id`: required in the path and with a valid UUID format; otherwise it responds `422`.
- [ ] `reason`: Must be between 3 and 255 characters after removing leading and trailing spaces.

**Business rules**

- [ ] The requester must be `OWNER` or `MANAGER` with `status = 'ACTIVE'` in the complex. A nonexistent or foreign complex responds `404`; a `MANAGER` with an `INACTIVE` membership is considered foreign to the complex. There is no `403` response, because every active member can cancel.
- [ ] The booking must belong to the indicated complex; a nonexistent booking or one from another complex responds `404`.
- [ ] Cancellation is not subject to `cancellation_deadline_hours`.
- [ ] Only a booking with `status = 'CONFIRMED'` and `ends_at > now()` is cancelled, so a booking in progress can also be cancelled. If it is already `CANCELLED` or has already ended, it responds `409` (`BOOKING_NOT_CANCELLABLE`) without modifying it.
- [ ] Cancellation changes `status` to `CANCELLED`, records `cancelled_at` with the current database date, `cancelled_by` with the token's user and `cancellation_reason` with the received reason.
- [ ] The cancelled slot becomes immediately available for new bookings (US-401, US-402).
- [ ] The booking is kept for auditing; it is not physically deleted.
- [ ] The operation is not idempotent: repeating an already-applied cancellation responds `409` (`BOOKING_NOT_CANCELLABLE`).
- [ ] Cancellation inserts the `booking.cancelled` event into `outbox_events` within the same transaction and with only `booking_id`; the dispatcher publishes it after the commit and the notification task sends the email to the `CLIENT`, with the reason (RF-503).
- [ ] If the insertion of the event into `outbox_events` fails, the entire transaction is rolled back and the cancellation is not applied; no event is published outside Outbox.

**Persistence and integrity**

- [ ] Dates are `TIMESTAMPTZ` in UTC and are taken from the database's `now()`; the update of `status`, `cancelled_at`, `cancelled_by` and `cancellation_reason`, together with the insertion of the event into `outbox_events`, executes in an atomic transaction.
- [ ] Cancellation executes with a conditional update `WHERE id = :booking_id AND complex_id = :complex_id AND status = 'CONFIRMED' AND ends_at > now()`; this same condition resolves races with the client's cancellation (US-404) and rescheduling (US-403): exactly one operation wins and the loser receives `409` (or `404` if the booking stopped existing in that complex).
- [ ] If no row is affected, the booking is queried by `id` and `complex_id`: if it does not exist or belongs to another complex it responds `404`; if it exists it responds `409`.
- [ ] RLS policies are applied by `complex_id` with `app.user_id` and the `updated_at` audit.

**Security**

- [ ] Requires `Authorization: Bearer`; without a valid token it responds `401` with `WWW-Authenticate: Bearer`; identity and role are derived exclusively from the token and the database.
- [ ] The rate limit `rl:bookings:u:{user_id}:{window}` (20 requests per user every 60 s) is evaluated after authenticating and before the write; when exceeded it responds `429` with `Retry-After`. If Redis is unavailable, the request continues and the error is logged. The real IP is only taken from `X-Forwarded-For` from a trusted proxy.
- [ ] The `booking.cancelled` event carries only `booking_id`: it does not include emails, names or the reason.
- [ ] Another complex's booking cannot be cancelled even if the path identifiers are manipulated.
- [ ] Logs include `request_id`, route, method, status, duration and `user_id`/`complex_id`/`booking_id` when applicable; they never include tokens, credentials, email addresses or the reason text.

**HTTP responses**

- [ ] `200`: booking cancelled; includes `id`, `complex_id`, `zone_id`, `client_id`, `starts_at`, `ends_at`, `status`, `cancelled_at`, `cancelled_by`, `cancellation_reason` and `updated_at`.
- [ ] `401`: token missing or invalid (`INVALID_TOKEN`).
- [ ] `404`: the complex or the booking does not exist or does not belong to the requester (`NOT_FOUND`).
- [ ] `409`: the booking is already cancelled or has already ended (`BOOKING_NOT_CANCELLABLE`).
- [ ] `415`: the body is sent with an unsupported `Content-Type` (`UNSUPPORTED_MEDIA_TYPE`).
- [ ] `422`: invalid identifiers or reason, or disallowed fields (`VALIDATION_ERROR`).
- [ ] `429`: request limit exceeded (`RATE_LIMITED`).
- [ ] `500`: unexpected error, without traces or internal details (`INTERNAL_ERROR`).

### Module 5 – Notifications

#### US-501: Send the account verification link by email

**As** a person who has just registered,
**I want** to receive the account verification link by email,
**So that** I can verify my email and be able to log in.

**Task:** `notifications.send_verification_email`
**Consumes Event:** `user.verification_email.created`

**Priority:** High (P0)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004

**Input validation**

- [ ] The message contains exclusively `user_id` (valid UUID) and the `request_id` of the request that originated it. A message without `user_id`, with an invalid format or with additional fields is discarded, logged as an error and not retried.
- [ ] The message does not contain the user's email, the password hash, the verification token or other personal data; everything else is read from the database.

**Business rules**

- [ ] The task loads the user by `user_id`. The email is only sent if the user exists and has `email_verified = false`; in any other case the task finishes successfully without sending and without retrying, and logs the reason (`NOT_FOUND` or `ALREADY_VERIFIED`).
- [ ] The task builds the signed token `{user_id}.{expires_at}.{signature}` with HMAC-SHA256 and `EMAIL_VERIFICATION_SECRET`. The token only exists in memory during execution and expires after 24 hours.
- [ ] The email is sent exclusively to the user's `email`, with a single recipient and no copies.
- [ ] The email is written in English, in plain text and HTML (`multipart/alternative`), and includes: the greeting with the `full_name` (if it does not exist, a generic greeting), the verification link, the expiration date and a notice that it can be ignored if the user did not register.
- [ ] The link has the format `{APP_EMAIL_VERIFICATION_URL}#token={token}`, with the token in the fragment so that it does not reach servers or access logs. The client reads it and sends it in the body of `POST /api/v1/auth/verify-email`.
- [ ] On a transient SMTP error (connection failure, timeout or `4xx` response), the task is retried up to 5 times with exponential backoff and jitter (approximately 1, 3, 9, 27 and 60 minutes). Before each retry, it is checked again that the user is still unverified.
- [ ] On a permanent SMTP error (`5xx` response, for example a rejected recipient), the task is not retried and finishes in failure.
- [ ] If the task finishes in failure, the user remains unverified and cannot log in; their status in the database is not modified.

**Persistence and integrity**

- [ ] The read is done in a short read-only transaction, and the database connection is released before opening the SMTP connection.
- [ ] Delivery is at least once (`acks_late = True`): if the worker crashes after sending and before acknowledging, the email may be sent twice. This is acceptable because the link is the same and is idempotent.
- [ ] The event is received from the Outbox dispatcher, not from the business transaction; the task does not publish events or modify `outbox_events`.
- [ ] Dates are `TIMESTAMPTZ` in UTC; the token expiration is calculated and validated in UTC.

**Security**

- [ ] The token and the user's email are not written to logs, task arguments or results, nor to the broker or error traces. Logs include `request_id`, `user_id`, attempt number, result and duration.
- [ ] User-controlled data (`full_name`) is escaped in the HTML and line breaks are removed from the subject, to prevent HTML or header injection.
- [ ] The SMTP connection requires TLS with certificate verification and authentication. Credentials and the sender (`MAIL_FROM`) are read from environment variables, never from code or logs. The connection and the read have a 10 s timeout.
- [ ] The email contains only the recipient's account data.

**Task results**

- [ ] `SENT`: the SMTP server accepted the message; `user.verification_email.sent` is logged.
- [ ] `OMITTED`: the user does not exist or is already verified; the task finishes successfully and `user.verification_email.skipped` is logged with the reason.
- [ ] `RETRY`: transient error; it is rescheduled and `user.verification_email.retry` is logged with the attempt and the wait.
- [ ] `FAILED`: permanent error or retries exhausted; the task finishes in failure and `user.verification_email.failed` is logged without personal data.
- [ ] `DISCARDED`: invalid message; the error is logged and it is not retried.

#### US-502: Send the invitation link by email to the invited person

**As** a person invited to operate as `MANAGER`,
**I want** to receive my invitation link by email,
**So that** I can accept it without depending on the `OWNER` sending me the link through another channel.

**Task:** `notifications.send_invitation_email`
**Consumes Event:** `invitation.created`

**Priority:** High (P0)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004

**Input validation**

- [ ] The message contains exclusively `invitation_id` (valid UUID) and the `request_id` of the request that originated it. A message without `invitation_id`, with an invalid format or with additional fields is discarded, logged as an error and not retried.
- [ ] The message does not contain the invitation token, the guest's email or other personal data; everything else is read from the database.

**Business rules**

- [ ] The task loads the invitation by `invitation_id`, together with the complex's `name` and `timezone` and the inviter's `full_name`.
- [ ] The email is only sent if the invitation exists, is `PENDING` and `expires_at > now()` (database time). In any other case the task finishes successfully without sending and without retrying, and logs the reason (`NOT_FOUND`, `NOT_PENDING` or `EXPIRED`). This covers an invitation cancelled or expired before the email goes out.
- [ ] The task builds the signed token `{invitation_id}.{signature}` (HMAC-SHA256) with the same secret key used at creation to validate it. The token only exists in memory during execution.
- [ ] The email is sent exclusively to `invitations.email`, with a single recipient and no copies.
- [ ] The email is written in English, in plain text and HTML (`multipart/alternative`), and includes: the complex's name (also in the subject), the inviter's name (if they have no `full_name`, "The owner of {complex}"), the `MANAGER` role and what it implies, the acceptance link, the deadline in the complex's time zone and a notice that it can be ignored if the invitation was not expected.
- [ ] The link has the format `{INVITATION_ACCEPT_URL}#token={token}`, with the token in the fragment so that it does not reach servers or access logs. The client reads it and sends it in the body of `POST /api/v1/invitations/accept`.
- [ ] On a transient SMTP error (connection failure, timeout or `4xx` response), the task is retried up to 5 times with exponential backoff and jitter (approximately 1, 3, 9, 27 and 60 minutes). Before each retry, the validity rules are evaluated again.
- [ ] On a permanent SMTP error (`5xx` response, for example a rejected recipient), the task is not retried and finishes in failure.
- [ ] If the task finishes in failure, the invitation does not change status (it remains `PENDING`); the `OWNER` can cancel it and create another one.

**Persistence and integrity**

- [ ] The read is done in a short read-only transaction, and the database connection is released before opening the SMTP connection.
- [ ] Delivery is at least once (`acks_late = True`): if the worker crashes after sending and before acknowledging, the email may be sent twice. This is acceptable because the link is the same and is idempotent.
- [ ] The event is received from the Outbox dispatcher, not from the business transaction; the task does not publish events or modify `outbox_events`.
- [ ] Dates are `TIMESTAMPTZ` in UTC; the deadline is converted to the complex's time zone only to display it in the email.

**Security**

- [ ] The token and the guest's email are not written to logs, task arguments or results, nor to the broker or error traces. Logs include `request_id`, `invitation_id`, `complex_id`, attempt number, result and duration.
- [ ] User-controlled data (complex and inviter names) is escaped in the HTML and line breaks are removed from the subject, to prevent HTML or header injection.
- [ ] The SMTP connection requires TLS with certificate verification and authentication. Credentials and the sender (`MAIL_FROM`) are read from environment variables, never from code or logs. The connection and the read have a 10 s timeout.
- [ ] The email contains only data of the complex that originated the invitation.

**Task results**

- [ ] `SENT`: the SMTP server accepted the message; `invitation.email.sent` is logged.
- [ ] `OMITTED`: the invitation does not exist, is not `PENDING` or is expired; the task finishes successfully and `invitation.email.skipped` is logged with the reason.
- [ ] `RETRY`: transient error; it is rescheduled and `invitation.email.retry` is logged with the attempt and the wait.
- [ ] `FAILED`: permanent error or retries exhausted; the task finishes in failure and `invitation.email.failed` is logged without personal data.
- [ ] `DISCARDED`: invalid message; the error is logged and it is not retried.

#### US-503: Notify the client by email of their booking cancellation

**As** a `CLIENT`,
**I want** to receive an email when the complex cancels my booking or the zone stops being available,
**So that** I find out in time, know the reason and can book another time.

**Task:** `notifications.send_booking_cancelled_email`
**Consumes Event:** `booking.cancelled`

**Priority:** Medium (P1)
**Size:** L
**Estimate:** 4

**Acceptance criteria:**

- [ ] **NFR to comply with:** RNF-001, RNF-004

**Input validation**

- [ ] The message contains exclusively `booking_id` (valid UUID) and the `request_id` of the request that originated it. A message without `booking_id`, with an invalid format or with additional fields is discarded, logged as an error and not retried.
- [ ] The message does not contain the client's email, the cancellation reason or other personal data; everything else is read from the database.

**Business rules**

- [ ] Events are inserted into Outbox through US-408 (`OWNER` or `MANAGER` cancellation), once per cancelled booking and within the same transaction; the dispatcher publishes them after the commit. Zone status changes (US-304) do not insert events.
- [ ] The task loads the booking by `booking_id`, together with the zone's `name` and `sport`, the complex's `name` and `timezone`, and the client's `email` and `full_name`.
- [ ] The email is only sent if the booking exists, has `status = 'CANCELLED'`, `cancelled_by` is not `NULL` and differs from `client_id` (staff cancellation), and `ends_at > now()` (database time). In any other case the task finishes successfully without sending and without retrying, and logs the reason (`NOT_FOUND`, `NOT_CANCELLED`, `CANCELLED_BY_CLIENT` or `BOOKING_ENDED`).
- [ ] The email is sent exclusively to the booking client's current `email`, with a single recipient and no copies.
- [ ] The email is written in English, in plain text and HTML (`multipart/alternative`), and includes: the greeting with the `full_name` (if it does not exist, a generic greeting), the complex's name (also in the subject), the zone's name and its sport, the booking date and time in the complex's time zone (indicating the zone), a sentence explaining the cause (the complex cancelled the booking) and the reason recorded in `cancellation_reason`.
- [ ] The name or email of the staff member who cancelled is not included.
- [ ] If the `APP_BOOKINGS_URL` variable is configured, the email includes a link to query bookings and book another time; the link does not contain any token or personal data.
- [ ] On a transient SMTP error (connection failure, timeout or `4xx` response), the task is retried up to 5 times with exponential backoff and jitter (approximately 1, 3, 9, 27 and 60 minutes). Before each retry, the previous rules are evaluated again.
- [ ] On a permanent SMTP error (`5xx` response, for example a rejected recipient), the task is not retried and finishes in failure.
- [ ] If the task finishes in failure, the booking cancellation is not modified; the email is not retried and the client can see the cancellation and its reason in their bookings (US-405).
- [ ] The task has a configurable execution limit (by default, 60 per minute per worker) so that a massive cancellation does not saturate the SMTP server.

**Persistence and integrity**

- [ ] The task only reads: it does not modify any table.
- [ ] The read is done in a short read-only transaction, and the database connection is released before opening the SMTP connection.
- [ ] Delivery is at least once (`acks_late = True`): if the worker crashes after sending and before acknowledging, the email may be sent twice. This is acceptable because the content is the same and only reports a fact that has already occurred.
- [ ] The event is received from the Outbox dispatcher, not from the business transaction; the task does not publish events or modify `outbox_events`.
- [ ] Dates are `TIMESTAMPTZ` in UTC; the booking time is converted to the complex's time zone only to display it in the email, with the correct local time even if that day has a daylight saving time change.

**Security**

- [ ] The client's email and the reason text are not written to logs, task arguments or results, nor to the broker or error traces. Logs include `request_id`, `booking_id`, `complex_id`, attempt number, result and duration.
- [ ] People-controlled data (complex name, zone name, client name and reason) is escaped in the HTML and line breaks are removed from the subject, to prevent HTML or header injection.
- [ ] The SMTP connection requires TLS with certificate verification and authentication. Credentials and the sender (`MAIL_FROM`) are read from environment variables, never from code or logs. The connection and the read have a 10 s timeout.
- [ ] The email contains only the recipient's booking data; never data from other clients or other bookings.

**Task results**

- [ ] `SENT`: the SMTP server accepted the message; `booking.cancellation_email.sent` is logged.
- [ ] `OMITTED`: the booking does not exist, is not cancelled, was cancelled by the client themselves or has already ended; the task finishes successfully and `booking.cancellation_email.skipped` is logged with the reason.
- [ ] `RETRY`: transient error; it is rescheduled and `booking.cancellation_email.retry` is logged with the attempt and the wait.
- [ ] `FAILED`: permanent error or retries exhausted; the task finishes in failure and `booking.cancellation_email.failed` is logged without personal data.
- [ ] `DISCARDED`: invalid message; the error is logged and it is not retried.

---

## Data Models

### Persistence Models

[Data model diagram](https://dbdiagram.io/d/Sturdy-Parakeet-6ae91707027db74914cca4b4)

#### `users` data model

| Field               | Type         | Constraints                                             | Description                                                                                            |
|---------------------|--------------|---------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `id`                | UUID         | PK                                                      | Internal user identifier                                                                               |
| `email`             | VARCHAR(320) | NOT NULL, UNIQUE, CHECK (`email = lower(btrim(email))`) | Account email, stored normalized in lowercase; used for login and compared with the invitations' email |
| `password_hash`     | VARCHAR(255) | NOT NULL                                                | Argon2id hash of the password; never returned or logged                                                |
| `full_name`         | VARCHAR(150) | NULL                                                    | Display name                                                                                           |
| `email_verified`    | BOOLEAN      | NOT NULL, DEFAULT false                                 | Indicates whether the email was verified (RF-102)                                                      |
| `email_verified_at` | TIMESTAMPTZ  | NULL                                                    | Email verification date                                                                                |
| `last_login_at`     | TIMESTAMPTZ  | NULL                                                    | Last successful login (RF-103)                                                                         |
| `created_at`        | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                 | Registration date                                                                                      |
| `updated_at`        | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                 | Last modification                                                                                      |

#### `sports_complexes` data model

| Field                       | Type         | Constraints                                               | Description                                                     |
|-----------------------------|--------------|-----------------------------------------------------------|-----------------------------------------------------------------|
| `id`                        | UUID         | PK                                                        | Complex identifier (tenant)                                     |
| `created_by`                | UUID         | NOT NULL, FK → `users.id`                                 | User who registered the complex; basis of the insert RLS policy |
| `name`                      | VARCHAR(120) | NOT NULL                                                  | Trade name                                                      |
| `slug`                      | VARCHAR(80)  | NOT NULL, UNIQUE, CHECK format `^[a-z0-9]+(-[a-z0-9]+)*$` | Public identifier for URLs                                      |
| `description`               | TEXT         | NULL                                                      | Description for the catalog                                     |
| `address`                   | VARCHAR(255) | NOT NULL                                                  | Address                                                         |
| `city`                      | VARCHAR(100) | NOT NULL                                                  | City                                                            |
| `timezone`                  | VARCHAR(64)  | NOT NULL, DEFAULT `'America/Bogota'`                      | IANA time zone with which schedules are interpreted             |
| `created_at` / `updated_at` | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                   | Basic audit                                                     |

**Indexes:** `(lower(name), id)` for catalog ordering and `(lower(city))` for the exact city filter of US-302. No additional index is created for `slug`, because `UNIQUE (slug)` already backs it.

#### `complex_memberships` data model

| Field                       | Type        | Constraints                                                   | Description                    |
|-----------------------------|-------------|---------------------------------------------------------------|--------------------------------|
| `id`                        | UUID        | PK                                                            | Identifier                     |
| `complex_id`                | UUID        | NOT NULL, FK → `sports_complexes.id`                          | Complex                        |
| `user_id`                   | UUID        | NOT NULL, FK → `users.id`                                     | User                           |
| `role`                      | VARCHAR(10) | NOT NULL, CHECK IN (`OWNER`, `MANAGER`)                       | Role within the complex        |
| `status`                    | VARCHAR(10) | NOT NULL, DEFAULT `'ACTIVE'`, CHECK IN (`ACTIVE`, `INACTIVE`) | Active or deactivated (RF-107) |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now()                                       | Basic audit                    |

**Additional constraints:** `UNIQUE (complex_id, user_id)` to prevent duplicate memberships of the same user in a complex.

#### `invitations` data model

| Field                       | Type         | Constraints                                                                             | Description                                    |
|-----------------------------|--------------|-----------------------------------------------------------------------------------------|------------------------------------------------|
| `id`                        | UUID         | PK                                                                                      | Identifier                                     |
| `complex_id`                | UUID         | NOT NULL, FK → `sports_complexes.id`                                                    | Inviting complex                               |
| `email`                     | VARCHAR(320) | NOT NULL                                                                                | Invited email, normalized with `strip + lower` |
| `status`                    | VARCHAR(10)  | NOT NULL, DEFAULT `'PENDING'`, CHECK IN (`PENDING`, `ACCEPTED`, `CANCELLED`, `EXPIRED`) | Invitation status                              |
| `expires_at`                | TIMESTAMPTZ  | NOT NULL                                                                                | End of validity (e.g., 7 days)                 |
| `invited_by`                | UUID         | NOT NULL, FK → `users.id`                                                               | `OWNER` who created it                         |
| `accepted_by`               | UUID         | NULL, FK → `users.id`                                                                   | User who accepted it                           |
| `accepted_at`               | TIMESTAMPTZ  | NULL                                                                                    | Acceptance date                                |
| `cancelled_at`              | TIMESTAMPTZ  | NULL                                                                                    | Cancellation date (RF-108)                     |
| `created_at` / `updated_at` | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                                                 | Basic audit                                    |

**Additional constraints:** partial unique index on `(complex_id, email)` for rows with `status = 'PENDING'`; `CHECK (email = lower(btrim(email)))` to guarantee that the persisted email is normalized. `EXPIRED` is persisted on demand in US-105, US-106 and US-108; a scheduler is not required solely to expire invitations.

#### `sports_zones` data model

| Field                       | Type         | Constraints                                                                  | Description                                                                                 |
|-----------------------------|--------------|------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `id`                        | UUID         | PK                                                                           | Identifier                                                                                  |
| `complex_id`                | UUID         | NOT NULL, FK → `sports_complexes.id`                                         | Complex to which it belongs                                                                 |
| `name`                      | VARCHAR(100) | NOT NULL                                                                     | Zone name                                                                                   |
| `sport`                     | VARCHAR(50)  | NOT NULL                                                                     | Sport (value controlled by the application)                                                 |
| `surface`                   | VARCHAR(50)  | NULL                                                                         | Surface                                                                                     |
| `capacity`                  | SMALLINT     | NULL, CHECK > 0                                                              | Maximum number of players                                                                   |
| `status`                    | VARCHAR(12)  | NOT NULL, DEFAULT `'ACTIVE'`, CHECK IN (`ACTIVE`, `INACTIVE`, `MAINTENANCE`) | Status (RF-304)                                                                             |
| `status_reason`             | VARCHAR(255) | NULL                                                                         | Reason for the last change to `INACTIVE` or `MAINTENANCE`; `NULL` when the zone is `ACTIVE` |
| `slot_duration_minutes`     | SMALLINT     | NOT NULL, DEFAULT 60, CHECK `% 15 = 0` and BETWEEN 15 AND 240                | Booking slot duration (RF-305)                                                              |
| `created_at` / `updated_at` | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                                      | Basic audit                                                                                 |

**Additional constraints:** `UNIQUE (id, complex_id)` to support composite foreign keys; unique index on `(complex_id, lower(name))`; index on `(complex_id, status)` for complex queries.

#### `zone_operating_hours` data model

| Field                       | Type        | Constraints                        | Description                                                       |
|-----------------------------|-------------|------------------------------------|-------------------------------------------------------------------|
| `id`                        | UUID        | PK                                 | Identifier                                                        |
| `complex_id`                | UUID        | NOT NULL                           | Complex (for RLS)                                                 |
| `zone_id`                   | UUID        | NOT NULL                           | Zone                                                              |
| `day_of_week`               | SMALLINT    | NOT NULL, CHECK BETWEEN 1 AND 7    | ISO day (1 = Monday)                                              |
| `opens_at_minute`           | SMALLINT    | NOT NULL, CHECK BETWEEN 0 AND 1439 | Opening in minutes since midnight, local complex time             |
| `closes_at_minute`          | SMALLINT    | NOT NULL, CHECK BETWEEN 1 AND 1440 | Closing in minutes since midnight; `24:00` is persisted as `1440` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now()            | Basic audit                                                       |

**Additional constraints:** composite foreign key `(zone_id, complex_id)` to `sports_zones (id, complex_id)`, so that PostgreSQL rejects operating hours whose complex does not match the zone's. `CHECK (opens_at_minute < closes_at_minute)`; `btree_gist` extension and `EXCLUDE USING gist (zone_id WITH =, day_of_week WITH =, int4range(opens_at_minute, closes_at_minute, '[)') WITH &&)` constraint to prevent overlaps. The API exposes these values as `opens_at` and `closes_at` in `HH:MM` format.

#### `bookings` data model

| Field                       | Type         | Constraints                                                          | Description                                                                       |
|-----------------------------|--------------|----------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `id`                        | UUID         | PK                                                                   | Identifier                                                                        |
| `complex_id`                | UUID         | NOT NULL                                                             | Complex (for RLS)                                                                 |
| `zone_id`                   | UUID         | NOT NULL                                                             | Booked zone                                                                       |
| `client_id`                 | UUID         | NOT NULL, FK → `users.id`                                            | Who books                                                                         |
| `starts_at`                 | TIMESTAMPTZ  | NOT NULL                                                             | Start, in UTC                                                                     |
| `ends_at`                   | TIMESTAMPTZ  | NOT NULL                                                             | End, in UTC                                                                       |
| `status`                    | VARCHAR(10)  | NOT NULL, DEFAULT `'CONFIRMED'`, CHECK IN (`CONFIRMED`, `CANCELLED`) | Persisted status; `COMPLETED` is derived from `CONFIRMED` with `ends_at <= now()` |
| `cancelled_at`              | TIMESTAMPTZ  | NULL                                                                 | Cancellation date                                                                 |
| `cancelled_by`              | UUID         | NULL, FK → `users.id`                                                | Who cancelled; compared with `client_id` to derive `cancelled_by_type`            |
| `cancellation_reason`       | VARCHAR(255) | NULL                                                                 | Reason (required for cancellations by `OWNER`/`MANAGER` through US-408)           |
| `created_at` / `updated_at` | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                              | Basic audit                                                                       |

**Additional constraints:** composite foreign key `(zone_id, complex_id)` to `sports_zones (id, complex_id)`; `CHECK (ends_at > starts_at)`; `btree_gist` exclusion constraint on `zone_id` and `tstzrange(starts_at, ends_at, '[)')` for rows with `status <> 'CANCELLED'`. The half-open interval allows contiguous bookings. `UNIQUE (id, complex_id)` is not added because no table references bookings through that combination.

**Indexes:** `(complex_id, starts_at DESC, id DESC)` for US-406; `(client_id, starts_at DESC, id DESC)` for US-405; `(client_id, status, ends_at)` for the active-booking limit and per-client queries; `(zone_id, starts_at)` for availability. They are not duplicated with the GiST index created by the exclusion constraint.

#### `complex_booking_policies` data model

| Field                            | Type        | Constraints                                     | Description                                                        |
|----------------------------------|-------------|-------------------------------------------------|--------------------------------------------------------------------|
| `complex_id`                     | UUID        | PK, FK → `sports_complexes.id`                  | 1:1 relationship with the complex                                  |
| `min_advance_minutes`            | INTEGER     | NOT NULL, DEFAULT 60, CHECK BETWEEN 0 AND 10080 | Minimum advance notice for booking                                 |
| `max_advance_days`               | INTEGER     | NOT NULL, DEFAULT 30, CHECK BETWEEN 1 AND 365   | Maximum advance notice in calendar days of the complex's time zone |
| `cancellation_deadline_hours`    | INTEGER     | NOT NULL, DEFAULT 24, CHECK BETWEEN 0 AND 720   | Hours before the start until which the `CLIENT` can cancel         |
| `max_active_bookings_per_client` | SMALLINT    | NOT NULL, DEFAULT 3, CHECK BETWEEN 1 AND 50     | Maximum active bookings per client                                 |
| `created_at` / `updated_at`      | TIMESTAMPTZ | NOT NULL, DEFAULT now()                         | Basic audit                                                        |

**Additional constraints:** `CHECK (min_advance_minutes < max_advance_days * 1440)` to prevent an empty booking window. It is a lower bound: the effective validation of `max_advance_days` uses calendar days in the complex's time zone, so on DST days the real window may last 23 or 25 hours.

#### `outbox_events` data model

| Field             | Type         | Constraints                                                                | Description                                                                                            |
|-------------------|--------------|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| `id`              | UUID         | PK                                                                         | Event identifier                                                                                       |
| `event_type`      | VARCHAR(100) | NOT NULL                                                                   | Event type, for example `user.verification_email.created`, `invitation.created` or `booking.cancelled` |
| `aggregate_id`    | UUID         | NOT NULL                                                                   | Identifier of the aggregate that originated the event                                                  |
| `payload`         | JSONB        | NOT NULL                                                                   | Minimum event data, without unnecessary personal data                                                  |
| `status`          | VARCHAR(20)  | NOT NULL, DEFAULT `'PENDING'`, CHECK IN (`PENDING`, `PUBLISHED`, `FAILED`) | Publication status                                                                                     |
| `attempts`        | SMALLINT     | NOT NULL, DEFAULT 0, CHECK >= 0                                            | Publication attempts made                                                                              |
| `last_error`      | TEXT         | NULL                                                                       | Last publication error, without sensitive data                                                         |
| `created_at`      | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                                    | Creation date in the business transaction                                                              |
| `published_at`    | TIMESTAMPTZ  | NULL                                                                       | Date the broker accepted the event                                                                     |
| `next_attempt_at` | TIMESTAMPTZ  | NOT NULL, DEFAULT now()                                                    | Next publication attempt; enables backoff and recovery                                                 |

**Indexes:** `(status, next_attempt_at, created_at)` for the dispatcher and `(aggregate_id)` for traceability.

**Transactional flow:** the business operation inserts the event into `outbox_events` within the same transaction. A dispatcher takes `PENDING` events with `next_attempt_at <= now()` using `FOR UPDATE SKIP LOCKED`, publishes them to the Celery/Redis broker after the commit and marks them `PUBLISHED` only when the broker accepts the event. On failures, it increments `attempts`, stores `last_error` and schedules `next_attempt_at` with exponential backoff; after exhausting retries it marks them `FAILED`. Stuck events are recovered by `next_attempt_at`, and delivery is at least once, so consumers must tolerate duplicates.

### Cache Structures - Redis

| Key                                       | Type             | Value                                   | TTL                          | Purpose                                                                                        |
|-------------------------------------------|------------------|-----------------------------------------|------------------------------|------------------------------------------------------------------------------------------------|
| `rl:{policy}:u:{user_id}:{window}`        | String (counter) | Integer with the requests in the window | Window size (60 s or 3600 s) | Limit per authenticated user                                                                   |
| `rl:{policy}:ip:{ip}:{window}`            | String (counter) | Integer with the requests in the window | Window size (60 s or 3600 s) | Limit per IP, for anonymous users and sensitive endpoints                                      |
| `rl:{policy}:email:{email_hash}:{window}` | String (counter) | Integer with the requests in the window | Window size (60 s or 3600 s) | Limit per email in registration and login; `email_hash` is the SHA-256 of the normalized email |
