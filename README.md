# Sturdy Parakeet

Multi-tenant REST API to administer sports complexes and manage the availability and booking of their zones.

Sturdy Parakeet centralizes the catalog of complexes and zones, operating hours, booking policies and reservations. It protects each complex's information with role-based access and PostgreSQL Row-Level Security, and sends asynchronous notifications for account verification, invitations and staff cancellations. The repository is currently the shared backend scaffold; the business modules and endpoints described below are the MVP target defined in [REQUIREMENTS_SPECIFICATION.md](docs/REQUIREMENTS_SPECIFICATION.md).

---

## Table of Contents

- [Technologies](#technologies)
- [Quick Start](#quick-start)
    - [Cloning the Repository](#cloning-the-repository)
    - [Dependency Management](#dependency-management)
    - [Running the Environment](#running-the-environment)
- [Architecture and Decisions](#architecture-and-decisions)
- [API Endpoints](#api-endpoints)
    - [System](#system)
    - [Authentication](#authentication)
    - [Complexes and Memberships](#complexes-and-memberships)
    - [Zones](#zones)
    - [Bookings](#bookings)
    - [Notifications](#notifications)
- [Testing](#testing)
- [DevOps](#devops)
- [License](#license)

---

## Technologies

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-CC2927?style=for-the-badge&logo=python&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-3D3D3D?style=for-the-badge&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Argon2id](https://img.shields.io/badge/Argon2id-4B5563?style=for-the-badge&logoColor=white)
![PyJWT](https://img.shields.io/badge/PyJWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![SMTP](https://img.shields.io/badge/SMTP-4A90E2?style=for-the-badge&logoColor=white)
![Structlog](https://img.shields.io/badge/Structlog-000000?style=for-the-badge&logo=logstash&logoColor=white)
![Pytest](https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![pytest-asyncio](https://img.shields.io/badge/pytest--asyncio-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![pytest-cov](https://img.shields.io/badge/pytest--cov-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-000000?style=for-the-badge&logo=ruff&logoColor=white)
![Mypy](https://img.shields.io/badge/Mypy-233564?style=for-the-badge&logo=python&logoColor=white)
![Pre-commit](https://img.shields.io/badge/Pre--commit-F9F3E6?style=for-the-badge&logo=pre-commit&logoColor=000000)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![OpenAPI](https://img.shields.io/badge/OpenAPI-6BA539?style=for-the-badge&logo=openapiinitiative&logoColor=white)
![Swagger UI](https://img.shields.io/badge/Swagger_UI-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)
![Hexagonal Architecture](https://img.shields.io/badge/Hexagonal_Architecture-6A5ACD?style=for-the-badge)
![Domain Driven Design](https://img.shields.io/badge/Domain_Driven_Design-8A2BE2?style=for-the-badge)

---

## Quick Start

### Cloning the Repository

```bash
git clone git@github.com:JohannGaviria/sturdy-parakeet.git
cd sturdy-parakeet
```

Copy the environment variables file and fill in the local values:

```bash
cp .env.example .env
```

| Variable                 | Description                                                                  | Example                                                                                                                                                                               |
|--------------------------|------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Application metadata** | Used to build the OpenAPI docs.                                              |                                                                                                                                                                                       |
| `APP_NAME`               | Title of the API shown in the OpenAPI docs and in the root endpoint.         | `Sturdy Parakeet`                                                                                                                                                                     |
| `APP_SUMMARY`            | Short summary of the API shown in the OpenAPI docs.                          | `Multi-tenant REST API for sports complexes, availability and bookings.`                                                                                                              |
| `APP_DESCRIPTION`        | Long description of the API shown in the OpenAPI docs.                       | `Multi-tenant REST API to administer sports complexes and manage the availability and booking of their zones, with authentication, role-based access and asynchronous notifications.` |
| **Backend**              |                                                                              |                                                                                                                                                                                       |
| `DEBUG`                  | Enables or disables debug mode.                                              | `True` / `False`                                                                                                                                                                      |
| `ENVIRONMENT`            | Runtime environment of the application.                                      | `development`                                                                                                                                                                         |
| `BACKEND_PORT`           | Port the API listens on inside the container and is published on the host.   | `8000`                                                                                                                                                                                |
| `BACKEND_WORKERS`        | Number of Gunicorn worker processes (production stage).                      | `4`                                                                                                                                                                                   |
| `CORS_ALLOW_ORIGINS`     | Allowed origins for CORS requests.                                           | `http://localhost:8000`                                                                                                                                                               |
| `CORS_ALLOW_CREDENTIALS` | Allows credentials to be included in CORS requests.                          | `True` / `False`                                                                                                                                                                      |
| **PostgreSQL (dev)**     | Consumed by the `postgres` container.                                        |                                                                                                                                                                                       |
| `POSTGRES_USER`          | User created by the `postgres` container.                                    | `postgres`                                                                                                                                                                            |
| `POSTGRES_PASSWORD`      | Password of that user. Required, the image refuses to initialize without it. | `password`                                                                                                                                                                            |
| `POSTGRES_DB`            | Database name created by the `postgres` container.                           | `db`                                                                                                                                                                                  |
| `POSTGRES_PORT`          | Host port published for `postgres`.                                          | `5432`                                                                                                                                                                                |
| **Database (dev)**       |                                                                              |                                                                                                                                                                                       |
| `DATABASE_URL`           | Connection string used by the application and by Alembic (SQLAlchemy Async). | `postgresql+asyncpg://postgres:password@postgres:5432/db`                                                                                                                             |
| `DB_POOL_SIZE`           | Maximum number of connections kept in the pool.                              | `10`                                                                                                                                                                                  |
| `DB_MAX_OVERFLOW`        | Connections allowed above the pool size before the pool blocks.              | `5`                                                                                                                                                                                   |
| `DB_POOL_TIMEOUT`        | Seconds to wait for a free connection before failing.                        | `30`                                                                                                                                                                                  |
| `DB_ECHO`                | Logs every SQL statement executed by the engine.                             | `false`                                                                                                                                                                               |
| **Redis (dev)**          |                                                                              |                                                                                                                                                                                       |
| `REDIS_URL`              | Redis connection URL.                                                        | `redis://redis:6379/0`                                                                                                                                                                |
| `REDIS_PORT`             | Host port published for `redis`.                                             | `6379`                                                                                                                                                                                |
| `REDIS_MAX_CONNECTIONS`  | Maximum size of the Redis connection pool.                                   | `20`                                                                                                                                                                                  |
| `REDIS_DECODE_RESPONSES` | Decodes the Redis responses to `str` instead of `bytes`.                     | `true`                                                                                                                                                                                |
| **Test infrastructure**  | Only used by the `test` profile (`docker compose --profile test`).           |                                                                                                                                                                                       |
| `POSTGRES_TEST_USER`     | User created by the `postgres-test` container.                               | `postgres_test`                                                                                                                                                                       |
| `POSTGRES_TEST_PASSWORD` | Password of that user.                                                       | `password`                                                                                                                                                                            |
| `POSTGRES_TEST_DB`       | Database name created by the `postgres-test` container.                      | `db_test`                                                                                                                                                                             |
| `POSTGRES_TEST_PORT`     | Host port published for `postgres-test`.                                     | `5433`                                                                                                                                                                                |
| `DATABASE_URL_TEST`      | Overrides `DATABASE_URL` inside `backend-test`.                              | `postgresql+asyncpg://postgres_test:password@postgres-test:5432/db_test`                                                                                                              |
| `REDIS_TEST_PORT`        | Host port published for `redis-test`.                                        | `6380`                                                                                                                                                                                |
| `REDIS_URL_TEST`         | Overrides `REDIS_URL` inside `backend-test`.                                 | `redis://redis-test:6379/0`                                                                                                                                                           |

> The hosts in `DATABASE_URL` and `REDIS_URL` are the compose service names, so those values only resolve from inside the Docker network. To run the API without Docker, point them at `localhost`.

> The version exposed in the OpenAPI docs is not an environment variable: it is read from the `version` field of `[project]` in `pyproject.toml`.

### Dependency Management

[Poetry](https://python-poetry.org/) is used as the dependency manager and virtual environment tool.

#### Installing the project dependencies

```shell
poetry install --with dev,test # Or: make setup
```

> **Note:** running the command via `make` will also install the pre-commit hooks.

This creates an isolated virtual environment and installs all the dependencies defined in `pyproject.toml`, including the development tools (`ruff`, `mypy`, `pytest`, etc.).

Dependency groups:

| Group  | Installed with | Contents                                            |
|--------|----------------|-----------------------------------------------------|
| `dev`  | `--with dev`   | ruff, mypy, pre-commit                              |
| `test` | `--with test`  | pytest and friends                                  |
| `prod` | `--with prod`  | gunicorn, only needed to build the production image |


### Running the Environment

#### Running the Environment without Docker

Run the API directly with Poetry and manage the external services (PostgreSQL, Redis, etc) separately:

**Requirements:**
- [Python 3.14](https://www.python.org/downloads/release/python-3140/)
- [PostgreSQL 16+](https://www.postgresql.org/docs/)
- [Redis 7+](https://redis.io/docs/latest/)

##### Starting the API

```shell
poetry run alembic upgrade head
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. The interactive documentation is available at `http://localhost:8000/docs`.

> The default port will be `8000`, but it can be configured through environment variables.

#### Running the Environment with Docker

Docker Compose starts all the required services simultaneously: the API, PostgreSQL and Redis.

**Requirements:**
- [Docker](https://www.docker.com/), or Docker Engine + Compose plugin
- [Docker Compose](https://docs.docker.com/compose/)

##### Starting the API

```shell
docker compose --profile dev up --build # or: make up
```

The first run downloads the base images and builds the application image. Subsequent runs are significantly faster if the dependencies have not changed.

The API will be available at `http://localhost:8000`. The interactive documentation is available at `http://localhost:8000/docs`.

> The default port will be `8000`, but it can be configured through environment variables.

---

## Architecture and Decisions

Sturdy Parakeet is a **modular monolith** built with **hexagonal architecture (Ports & Adapters)** and **tactical DDD**. The synchronous API writes in PostgreSQL within a single transaction, while notifications are delivered asynchronously through a transactional Outbox and Celery workers.

```
src/
├── modules/
│   ├── auth/           # Registration, email verification and login
│   ├── complexes/      # Complexes, memberships and invitations
│   ├── zones/          # Zones, operating hours and status
│   ├── bookings/       # Availability, creation, rescheduling and cancellation
│   └── notifications/  # Asynchronous email delivery
└── shared/
```

**Why a modular monolith:** it keeps business transactions and consistency inside one PostgreSQL database while preserving module boundaries and the option to extract modules later.

For a detailed explanation of the layers, request flow, RLS and Outbox, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## API Endpoints

The tables below describe the target contract from the requirements specification. The current scaffold exposes only the System endpoints; business endpoints are added as their modules are implemented.

### System

| Method | Endpoint        | Auth/Role | Description                                              |
| ------ | --------------- | --------- | -------------------------------------------------------- |
| `GET`  | `/`             | Public    | Welcome message.                                         |
| `GET`  | `/health`       | Public    | Liveness check; does not touch PostgreSQL or Redis.      |
| `GET`  | `/health/ready` | Public    | Readiness check for PostgreSQL and Redis.                |

### Authentication

| Method | Endpoint                      | Auth/Role | Description                                                              |
| ------ | ----------------------------- | --------- | ------------------------------------------------------------------------ |
| `POST` | `/api/v1/auth/register`       | Public    | Register with email and password; sends a verification email via Outbox. |
| `POST` | `/api/v1/auth/verify-email`   | Public    | Verify the email address with a signed, expiring token.                  |
| `POST` | `/api/v1/auth/login`          | Public    | Obtain an access JWT; requires a verified email.                         |

### Complexes and Memberships

| Method   | Endpoint                                                         | Auth/Role | Description                                      |
| -------- | ---------------------------------------------------------------- | --------- | ------------------------------------------------ |
| `POST`   | `/api/v1/complexes`                                              | Bearer    | Create a complex; the creator becomes `OWNER`.   |
| `POST`   | `/api/v1/complexes/{complex_id}/invitations`                     | `OWNER`   | Invite a person by email to be `MANAGER`.        |
| `POST`   | `/api/v1/invitations/accept`                                     | Bearer    | Accept a valid invitation and become `MANAGER`.  |
| `PATCH`  | `/api/v1/complexes/{complex_id}/memberships/{membership_id}`     | `OWNER`   | Activate or deactivate a `MANAGER`.              |
| `DELETE` | `/api/v1/complexes/{complex_id}/invitations/{invitation_id}`     | `OWNER`   | Cancel a pending invitation.                     |

### Zones

| Method  | Endpoint                                                  | Auth/Role         | Description                                                                  |
|---------|-----------------------------------------------------------|-------------------|------------------------------------------------------------------------------|
| `POST`  | `/api/v1/complexes/{complex_id}/zones`                    | `OWNER`/`MANAGER` | Create a sports zone in the complex.                                         |
| `GET`   | `/api/v1/complexes`                                       | Bearer            | Catalog of complexes with public data, active zones, schedules and policies. |
| `PATCH` | `/api/v1/complexes/{complex_id}/zones/{zone_id}`          | `OWNER`/`MANAGER` | Update a zone's data.                                                        |
| `PATCH` | `/api/v1/complexes/{complex_id}/zones/{zone_id}/status`   | `OWNER`/`MANAGER` | Change the zone status to `ACTIVE`, `INACTIVE` or `MAINTENANCE`.             |
| `PUT`   | `/api/v1/complexes/{complex_id}/zones/{zone_id}/schedule` | `OWNER`/`MANAGER` | Replace operating hours and slot duration.                                   |

### Bookings

| Method   | Endpoint                                                      | Auth/Role         | Description                                                        |
|----------|---------------------------------------------------------------|-------------------|--------------------------------------------------------------------|
| `POST`   | `/api/v1/complexes/{complex_id}/zones/{zone_id}/bookings`     | Bearer            | Create a booking for an available slot.                            |
| `GET`    | `/api/v1/complexes/{complex_id}/availability`                 | Optional Bearer   | Query availability for a local date.                               |
| `PATCH`  | `/api/v1/bookings/{booking_id}`                               | `CLIENT`          | Reschedule the user's own booking.                                 |
| `DELETE` | `/api/v1/bookings/{booking_id}`                               | `CLIENT`          | Cancel the user's own booking within the policy deadline.          |
| `GET`    | `/api/v1/bookings`                                            | `CLIENT`          | List the user's own bookings.                                      |
| `GET`    | `/api/v1/complexes/{complex_id}/bookings`                     | `OWNER`/`MANAGER` | List the complex's bookings.                                       |
| `PATCH`  | `/api/v1/complexes/{complex_id}/booking-policies`             | `OWNER`           | Configure advance notice, cancellation deadline and booking limit. |
| `POST`   | `/api/v1/complexes/{complex_id}/bookings/{booking_id}/cancel` | `OWNER`/`MANAGER` | Cancel a complex booking with a reason and notify the client.      |

### Notifications

Notifications are asynchronous tasks, not HTTP endpoints.

| Task                                          | Consumes event                      | Description                                              |
| --------------------------------------------- | ----------------------------------- | -------------------------------------------------------- |
| `notifications.send_verification_email`       | `user.verification_email.created`   | Send the account verification link.                      |
| `notifications.send_invitation_email`         | `invitation.created`                | Send the invitation link to the invited person.          |
| `notifications.send_booking_cancelled_email`  | `booking.cancelled`                 | Notify the client when staff cancels their booking.      |

---

## Testing

The tests are organized in three levels, each one in its own directory:

```
tests/
├── unit/          # No DB or Redis. Domain rules, use cases and fakes. Very fast.
├── integration/   # Real PostgreSQL and Redis. Repositories, RLS, constraints and concurrency.
└── e2e/           # Full HTTP flows against the running application.
```

- **Unit** → domain invariants, slot generation and DST rules, token signing, policies and use cases with fakes.
- **Integration** → repositories, RLS, exclusion constraints, locking, Outbox recovery and Redis rate limiting.
- **E2E** → registration, verification, login, memberships, zones, availability and booking flows through the HTTP contract.

The integration and E2E tests require the infrastructure services to be running; the unit tests have no external dependencies. RLS, locking, exclusion, concurrency and Outbox tests run against real PostgreSQL, never SQLite.

| Scope       | Makefile                      | Equivalent                                                                                                                 |
| ----------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| All         | `make test`                   | `docker compose --profile test run --rm backend-test pytest tests -v`                                                      |
| Unit        | `make test-unit`              | `poetry run pytest tests/unit -v`                                                                                          |
| Integration | `make test-integration`       | `docker compose --profile test run --rm backend-test pytest tests/integration -v`                                          |
| No DB       | `make test-integration-no-db` | `poetry run pytest tests/integration -m "not db" -v`                                                                       |
| E2E         | `make test-e2e`               | `docker compose --profile test run --rm backend-test pytest tests/e2e -v`                                                  |
| Coverage    | `make test-coverage`          | `docker compose --profile test run --rm backend-test pytest tests --cov=src --cov-report=term-missing --cov-fail-under=70` |

RNF-006 sets **80%** as the normative coverage target. The current Makefile and CI configuration still enforce 70%; the alignment is tracked in [TEST_STRATEGY.md](docs/TEST_STRATEGY.md), which also contains the full P0 and P1 acceptance test suites.

For the testing strategy, test structure, coverage target and the full list of commands, see [TEST_STRATEGY.md](docs/TEST_STRATEGY.md).

---

## DevOps

The delivery flow is the same for every project built from this template:

```text
Local development -> Pull request -> CI -> Merge to main -> Release (vX.Y.Z)
                                                               |
                                                               v
                                                Docker image (Build and Publish)
                                                               |
                                                               v
                                                  Railway (Deploy Image)
                                                               |
                                                               v
                                                        Health Check
```

| Environment | Where it runs                               | Configuration              | URL                     |
|-------------|---------------------------------------------|----------------------------|-------------------------|
| Development | Local Docker Compose (`dev` profile)        | `.env`                     | `http://localhost:8000` |
| Test        | Local Docker Compose (`test` profile) or CI | `.env` plus test overrides | Not published           |
| Production  | Railway (published Docker Hub image)        | Railway service variables  | `<PRODUCTION_URL>`      |

The delivery pipelines are responsible for the following:

- `ci.yml`: validates every change through linting, unit, integration and E2E tests, and coverage.
- `release.yml`: creates the semantic version, changelog and Git tag.
- `publish-image.yml`: builds the production Docker image, publishes it to Docker Hub and scans it with Trivy.
- `cd.yml`: configures the Railway service to use the published Docker image, triggers the deployment and checks readiness.

The Release Pipeline is opt-in, and the CD Pipeline skips pre-release tags. Railway deploys the exact image published by the Docker pipeline; it does not rebuild the application from source.

For the complete delivery flow, pipeline configuration, required variables and tokens, and instructions for adapting the template to a new project, see [DEVOPS.md](docs/DEVOPS.md).

---

## License

Distributed under the **MIT** License. See [LICENSE](LICENSE).

---

> Made with ♥️ by [JohannGaviria](https://github.com/JohannGaviria); always open to connecting for feedback, collaboration, or job opportunities.
