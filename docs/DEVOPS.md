# DevOps

> Describes the delivery flow, the CI/CD pipelines, the required variables and tokens, and the development, test and production environments of the project.

## Table of Contents

- [DevOps Flow](#devops-flow)
- [Environments](#environments)
  - [Development](#development)
  - [Test](#test)
  - [Production](#production)
- [Pipelines](#pipelines)
  - [CI Pipeline](#ci-pipeline)
  - [Release Pipeline](#release-pipeline)
  - [Publish Docker Image Pipeline](#publish-docker-image-pipeline)
  - [CD Pipeline](#cd-pipeline)
- [Required Variables and Tokens](#required-variables-and-tokens)
  - [GitHub Secrets](#github-secrets)
  - [GitHub Variables](#github-variables)
  - [Runtime Environment Variables](#runtime-environment-variables)
- [Branching and Release Flow](#branching-and-release-flow)
- [Configuration Checklist](#configuration-checklist)
- [Troubleshooting](#troubleshooting)

---

## DevOps Flow

The delivery path is the same for every project built from this template. Local development uses Docker Compose, a pull request runs the full CI suite, a release is created from `main`, the release tag publishes a Docker image, and the CD pipeline configures Railway to deploy that exact published image.

Docker Hub is the source of the production image, while Railway is responsible for running the container. The CD pipeline does not rebuild the application or upload source code to Railway. It updates the Railway service image reference to the versioned image published by the Docker pipeline and triggers a redeployment.

```text
Developer
    |
    v
Local Development
    |
    v
Commit / Push / Pull Request
    |
    v
CI Pipeline
(Lint, Unit, Integration, E2E, Coverage)
    |
    v
Merge to main
    |
    v
Release Pipeline
(semantic-release, Git Tag vX.Y.Z)
    |
    v
Publish Docker Image Pipeline
(Build, Push to Docker Hub, Trivy Scan)
    |
    v
CD Pipeline
(Configure Railway Image Source, Redeploy, Health Check)
    |
    v
Production
(Railway runs the published Docker image)
```

| Stage                  | Trigger                                               | What happens                                                                                               | Result                              |
|------------------------|-------------------------------------------------------|------------------------------------------------------------------------------------------------------------|-------------------------------------|
| Local development      | Developer command                                     | Docker Compose `dev` profile, pre-commit hooks, local API on port 8000                                     | Working environment                 |
| Continuous integration | Push or pull request on `develop` / `main`, or manual | Lint, unit, integration and E2E jobs, then a combined coverage report                                      | Green or red CI run                 |
| Release                | Automatic: after a successful CI run on `main`        | semantic-release computes the next version, updates `CHANGELOG.md` and `pyproject.toml`, and creates a tag | Git tag `vX.Y.Z` and GitHub release |
| Image publication      | Push of a tag matching `v*`                           | Production image is built, pushed to Docker Hub and scanned with Trivy                                     | Versioned container image `vX.Y.Z`  |
| Deployment             | Successful image publication, or manual dispatch      | Railway service is configured to use the published Docker image, redeployed and checked for readiness      | Release image running in production |

**Deployment relationship:**

- Docker builds and publishes the production image.
- Docker Hub stores the versioned image consumed by Railway.
- CD identifies the exact image using `${DOCKERHUB_USERNAME}/<repository-name>` and `IMAGE_TAG`.
- Railway receives the image reference and redeploys the service.
- The health check verifies that the deployed application is ready.

---

## Environments

| Environment | Where it runs                       | Orchestration                                                                   | Configuration source                               | Database and cache                                     | URL                     | Notes                                                                                         |
|-------------|-------------------------------------|---------------------------------------------------------------------------------|----------------------------------------------------|--------------------------------------------------------|-------------------------|-----------------------------------------------------------------------------------------------|
| Development | Developer machine                   | `docker compose --profile dev` (`backend-dev`, `postgres`, `redis`)             | `.env` copied from `.env.example`                  | `postgres:16-alpine` on 5432, `redis:7-alpine` on 6379 | `http://localhost:8000` | `DEBUG=True`, `ENVIRONMENT=development`, Uvicorn with `--reload`, migrations on startup       |
| Test        | Developer machine or GitHub Actions | `docker compose --profile test` (`backend-test`, `postgres-test`, `redis-test`) | `.env` plus `DATABASE_URL_TEST` / `REDIS_URL_TEST` | `postgres-test` on 5433, `redis-test` on 6380          | Not published           | Isolated containers and volumes, `db` and `e2e` markers, coverage collected per suite         |
| Production  | Railway                             | Railway service configured with the published Docker Hub image                  | Railway service variables                          | Managed PostgreSQL and Redis (`<PRODUCTION_DATABASE>`) | `<PRODUCTION_URL>`      | `DEBUG=False`, `ENVIRONMENT=production`, Gunicorn with Uvicorn workers, migrations on startup |

### Development

- Purpose: day-to-day development and manual verification.
- API: `http://localhost:8000`; interactive docs at `http://localhost:8000/docs`.
- Start it with `make up` or `docker compose --profile dev up --build`.
- The `development` target of the Dockerfile installs the `dev` group and runs Uvicorn with `--reload`.
- `entrypoint.sh` applies `alembic upgrade head` before the server starts.
- The root endpoint, `/health` and `/health/ready` are available for quick checks.

### Test

- Purpose: run the three test levels in isolation from development data.
- The `test` profile uses dedicated `postgres-test` and `redis-test` containers, volumes and ports.
- `backend-test` receives `DATABASE_URL` and `REDIS_URL` overridden with `DATABASE_URL_TEST` and `REDIS_URL_TEST`.
- CI runs unit tests directly with Poetry and integration/E2E tests through Docker Compose.
- Coverage data is uploaded as artifacts and combined in the `coverage` job; the threshold is 70%.

### Production

- Purpose: serve real traffic.
- The production image is built by the `Publish Docker Image Pipeline` from the `production` target of the Dockerfile.
- The image is published to Docker Hub with a version tag and scanned with Trivy.
- Railway runs the published image instead of building the application from the repository source.
- The image is selected by the CD pipeline as `${DOCKERHUB_USERNAME}/<repository-name>:${IMAGE_TAG}`, where `IMAGE_TAG` is the release tag.
- The container runs `gunicorn` with `uvicorn_worker.UvicornWorker`.
- `BACKEND_WORKERS` controls the number of Gunicorn workers.
- Migrations run on every container start through `entrypoint.sh`; there is no separate migration pipeline.
- Runtime configuration lives in the Railway service, not in the repository.
- The deployment job uses the GitHub Environment `production`; add protection rules there if the project requires manual approval.

---

## Pipelines

### CI Pipeline

**File:** [.github/workflows/ci.yml](../.github/workflows/ci.yml)

- **Purpose:** validate every change before it reaches `main`.
- **Trigger:** push or pull request on `develop` and `main`, plus `workflow_dispatch`.
- **Permissions:** `contents: read`; uses the automatic `GITHUB_TOKEN`.
- **Concurrency:** cancels the previous run for the same workflow and ref.
- **Jobs:**
  - `lint`: installs the `dev` and `test` groups and runs `make check` (Ruff format check, Ruff lint, mypy).
  - `unit-tests`: runs `make test-unit`, collects coverage with `make test-coverage-unit` and uploads `coverage-data-unit-<run_id>`.
  - `integration-tests`: runs `make test-integration` against the test profile, collects coverage and uploads `coverage-data-integration-<run_id>`.
  - `e2e-tests`: runs `make test-e2e`, collects coverage and uploads `coverage-data-e2e-<run_id>`.
  - `coverage`: runs after the four jobs, fails early if any of them failed, downloads the three artifacts and runs `make test-coverage-report`.
- **Secrets required:** none.
- **Artifacts:** per-suite coverage data with one day of retention.

### Release Pipeline

**File:** [.github/workflows/release.yml](../.github/workflows/release.yml)

- **Purpose:** derive the next semantic version from commit messages, create the changelog, update the project version and tag the release.
- **Trigger:** automatic execution after a successful `CI Pipeline` run on `main` (push event), through `workflow_run`.
- **Permissions:** `contents: write`.
- **Concurrency:** one release at a time for `main`.
- **Steps:** checkout the successful CI commit with full history, set up Node.js 24 and Python 3.14, install Poetry and the project dependencies, install semantic-release and run it.
- **Configuration:** `.releaserc.json` defines `branches: ["main"]`, the `v${version}` tag format and these release rules:
  - breaking change: `major`;
  - `feat`: `minor`;
  - `fix`: `patch`.
- **Outputs:** `CHANGELOG.md`, the updated version in `pyproject.toml`, a commit `chore(release): vX.Y.Z`, a Git tag and a GitHub release.
- **Secrets required:** `RELEASE_TOKEN_STURDY_PARAKEET` (see [GitHub Secrets](#github-secrets)).

### Publish Docker Image Pipeline

**File:** [.github/workflows/publish-image.yml](../.github/workflows/publish-image.yml)

- **Purpose:** build and publish the production Docker image for a release.
- **Trigger:** push of a tag matching `v*`.
- **Permissions:** `contents: read`.
- **Image name:** `${DOCKERHUB_USERNAME}/<repository-name>`.
- **Steps:** checkout the tag, set up Docker Buildx, log in to Docker Hub, detect whether the tag is a pre-release, build the `production` target, push the tags and scan the image with Trivy.
- **Tags:**
  - `v1.2.3` publishes `:v1.2.3` and moves `:latest`.
  - `v1.2.3-beta.1` publishes `:v1.2.3-beta.1` and does **not** move `:latest`, because the tag contains a `-`.
- **Security scan:** Trivy reports `HIGH` and `CRITICAL` findings with `exit-code: "0"`, so a new CVE appears in the log without blocking the release. Tighten it to `"1"` when the project is ready to enforce it.
- **Secrets required:** `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.

The versioned image published by this pipeline is the same image that the CD pipeline deploys to Railway. Railway does not build another image from the source code.

### CD Pipeline

**File:** [.github/workflows/cd.yml](../.github/workflows/cd.yml)

- **Purpose:** configure the Railway service to use the exact Docker image published for a release tag, trigger its deployment and verify that the service is healthy.
- **Trigger:** completion of the `Publish Docker Image Pipeline`, or `workflow_dispatch` with a required `tag` input.
- **Condition:** manual runs always proceed; workflow runs proceed only when the image publication succeeded and was triggered by a push.
- **Environment:** the job is bound to the GitHub Environment `production`.
- **Concurrency:** `railway-deploy-production`, without cancelling an in-progress deployment.
- **Image reference:** `${DOCKERHUB_USERNAME}/<repository-name>:${IMAGE_TAG}`, using the same version tag that `publish-image.yml` pushed (the tag comes from `workflow_run.head_branch`).
- **Steps:**
  1. Skip pre-release tags.
  2. Set up Node.js 24.
  3. Install `@railway/cli@5.71.0`.
  4. Authenticate using `RAILWAY_API_TOKEN` (Account Token).
  5. Identify the Railway project explicitly using `RAILWAY_PROJECT_ID`.
  6. Update the Railway service source to the published Docker image with `railway service source connect --project ... --image`.
  7. Trigger the deployment with `railway redeploy --from-source`.
  8. Poll the health check URL up to 12 times with 10 seconds between attempts.

- **Deploy commands:**

```bash
railway service source connect \
  --project "$RAILWAY_PROJECT_ID" \
  --image "${IMAGE_NAME}:${IMAGE_TAG}" \
  --service "$RAILWAY_SERVICE_NAME" \
  --environment "$RAILWAY_ENVIRONMENT_NAME"

railway redeploy \
  --from-source \
  --project "$RAILWAY_PROJECT_ID" \
  --service "$RAILWAY_SERVICE_NAME" \
  --environment "$RAILWAY_ENVIRONMENT_NAME" \
  --yes
```

- **Health check:** runs only when the repository variable `RAILWAY_HEALTHCHECK_URL` is not empty; it expects HTTP 200.
- **Secrets required:** `RAILWAY_API_TOKEN`, `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE`, `RAILWAY_ENVIRONMENT` (the environment secret defaults to `production`).
- **Variables required:** `RAILWAY_HEALTHCHECK_URL` (optional, but recommended). The image name is built from the `DOCKERHUB_USERNAME` secret and the repository name.

**Important notes:**

- `RAILWAY_API_TOKEN` is an Account Token, not a Project Token. It authenticates the Railway CLI.
- Account tokens do not implicitly identify the project to deploy. The workflow must explicitly pass `RAILWAY_PROJECT_ID` through `--project`.
- The workflow does not need a checkout or a `railway link` because the project, service and environment are explicitly supplied to the CLI.
- `railway service source connect` changes the image source at the service level. If the same service is shared with another environment, that environment may also use the updated image source and trigger an additional deployment.
- Railway must be able to pull the image. Public Docker Hub repositories work out of the box; private repositories require registry credentials configured in Railway.
- The CD pipeline does not rebuild the Docker image. It deploys the already published and scanned release image.

---

## Required Variables and Tokens

GitHub secrets are for workflows. Runtime configuration is a separate concern and lives in `.env` locally and in the provider (Railway) in production. Do not store runtime values as repository secrets unless a workflow consumes them.

### GitHub Secrets

Configure them in **Settings → Secrets and variables → Actions → Secrets** (repository level) or under the `production` environment.

| Name                            | Used by                           | Required           | Where it comes from                                           | Permissions and notes                                                                                                                                                                 |
|---------------------------------|-----------------------------------|--------------------|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `GITHUB_TOKEN`                  | CI Pipeline                       | Automatic          | GitHub injects it into every workflow                         | The CI workflow declares `contents: read`. Do not create it manually.                                                                                                                 |
| `RELEASE_TOKEN_STURDY_PARAKEET` | Release Pipeline                  | Yes for releases   | GitHub Settings → Developer settings → Personal access tokens | Personal Access Token with write access to repository contents. Required because tags pushed with `GITHUB_TOKEN` do not trigger other workflows, which would break image publication. |
| `DOCKERHUB_USERNAME`            | Publish Docker Image, CD Pipeline | Yes                | Docker Hub account username                                   | Also used by CD to build the image name, so the published repository is `${DOCKERHUB_USERNAME}/<repo-name>`.                                                                          |
| `DOCKERHUB_TOKEN`               | Publish Docker Image              | Yes                | Docker Hub Account settings → Personal access tokens          | Access token with read and write permissions. Use a token, not the account password.                                                                                                  |
| `RAILWAY_API_TOKEN`             | CD Pipeline                       | Yes for deployment | Railway account settings → Account Tokens                     | Account Token used to authenticate the Railway CLI. This is not a Project Token.                                                                                                      |
| `RAILWAY_PROJECT_ID`            | CD Pipeline                       | Yes for deployment | Railway project dashboard / project settings                  | Project identifier passed explicitly through `--project` to both deployment commands.                                                                                                 |
| `RAILWAY_SERVICE`               | CD Pipeline                       | Yes for deployment | Railway project dashboard, service settings                   | Name or identifier of the service that receives the deployment.                                                                                                                       |
| `RAILWAY_ENVIRONMENT`           | CD Pipeline                       | Optional           | Railway project dashboard, environment settings               | Name or identifier of the target environment. Defaults to `production` when the secret is absent.                                                                                     |

**Railway authentication and identification:**

- Create an Account Token in Railway's account settings.
- Store the token in GitHub as `RAILWAY_API_TOKEN`.
- Obtain the project identifier from the Railway project settings and store it as `RAILWAY_PROJECT_ID`.
- Obtain the target service and environment identifiers or names and configure `RAILWAY_SERVICE` and `RAILWAY_ENVIRONMENT`.
- Do not use a Project Token for this workflow.

### GitHub Variables

Configure them in **Settings → Secrets and variables → Actions → Variables**.

| Name                      | Used by     | Required | Where it comes from                                                          | Notes                                                                                                       |
|---------------------------|-------------|----------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `RAILWAY_HEALTHCHECK_URL` | CD Pipeline | No       | Public production readiness URL, for example `<PRODUCTION_URL>/health/ready` | If it is empty or missing, the health check step is skipped. Use the readiness endpoint, not `/health`.     |

### Runtime Environment Variables

The full list, with descriptions and examples, is in the root [README](../README.md#quick-start) and in [`.env.example`](../.env.example). The groups are:

| Group                | Variables                                                                                                 | Where it is set                                         |
|----------------------|-----------------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| Application metadata | `APP_NAME`, `APP_SUMMARY`, `APP_DESCRIPTION`                                                              | `.env` locally; Railway service variables in production |
| Backend              | `DEBUG`, `ENVIRONMENT`, `BACKEND_PORT`, `BACKEND_WORKERS`, `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_CREDENTIALS` | `.env` locally; Railway service variables in production |
| Database             | `DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_ECHO`                           | `.env` locally; Railway service variables in production |
| Redis                | `REDIS_URL`, `REDIS_MAX_CONNECTIONS`, `REDIS_DECODE_RESPONSES`                                            | `.env` locally; Railway service variables in production |
| Test infrastructure  | `POSTGRES_TEST_*`, `DATABASE_URL_TEST`, `REDIS_TEST_PORT`, `REDIS_URL_TEST`                               | `.env`; consumed only by the `test` profile             |

- `.env` is gitignored. Never commit real credentials.
- CI copies `.env.example` into `.env`; the test profile overrides the database and cache URLs.
- In production, `DEBUG` must be `False`, `ENVIRONMENT` should be `production` and `CORS_ALLOW_ORIGINS` must list the real frontend origins.
- `BACKEND_WORKERS` should match the container resources; the template default is `4`.
- Database and cache credentials are managed by the hosting provider and injected as service variables.
- Railway deployment credentials (`RAILWAY_API_TOKEN`, `RAILWAY_PROJECT_ID`, etc.) are GitHub workflow configuration, not application runtime variables.

---

## Branching and Release Flow

- `develop` is the integration branch; `main` is the release branch.
- CI runs on push and pull requests against both branches.
- Semantic-release only publishes from `main`.
- Commit messages follow Conventional Commits:
  - `feat: ...` produces a minor release;
  - `fix: ...` produces a patch release;
  - a breaking change (`!` or `BREAKING CHANGE:` footer) produces a major release;
  - other types (`docs`, `chore`, `test`, `refactor`, `ci`) do not produce a release on their own.
- A normal tag (`v1.2.3`) updates `:latest`, publishes `:v1.2.3` and makes the CD Pipeline deploy that exact image tag.
- A pre-release tag (`v1.2.3-beta.1`) does not move `:latest` and is skipped by the CD Pipeline.
- The deployed image must match the tag published by the Docker pipeline. CD must not build a different image or deploy an independently rebuilt version.

---

## Configuration Checklist

Use this checklist when adopting the template in a new project:

1. Create the Docker Hub repository and add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.
2. Create the Railway project, service and environment.
3. Generate a Railway Account Token and add it to GitHub as `RAILWAY_API_TOKEN`.
4. Obtain the Railway project identifier and add it as `RAILWAY_PROJECT_ID`.
5. Add `RAILWAY_SERVICE` and `RAILWAY_ENVIRONMENT` with the target service and environment names or identifiers.
6. Set the production runtime variables in Railway (`APP_*`, `DEBUG`, `ENVIRONMENT`, `DATABASE_URL`, `REDIS_URL`, CORS and worker settings).
7. Add the `RAILWAY_HEALTHCHECK_URL` variable pointing at `<PRODUCTION_URL>/health/ready`.
8. Create the `production` GitHub Environment and add protection rules if manual approval is required.
9. Add `RELEASE_TOKEN_STURDY_PARAKEET` so semantic-release can push the tag and trigger image publication.
10. Verify CI with a pull request, then let a successful CI run on `main` trigger the release and confirm the tag, the Docker image and the Railway deployment.
11. Rotate tokens on the project's security schedule and remove tokens that are no longer needed.

---

## Troubleshooting

| Symptom                                | Likely cause                                                                           | Fix                                                                                                                      |
|----------------------------------------|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| Releases never start automatically     | CI on `main` did not succeed, or the release token is missing                          | Confirm the `workflow_run` job ran after a successful push CI on `main` and that `RELEASE_TOKEN_STURDY_PARAKEET` is set. |
| semantic-release cannot push the tag   | Missing, expired or read-only `RELEASE_TOKEN_STURDY_PARAKEET`                          | Recreate the PAT with repository contents write access and update the secret.                                            |
| A tag exists but no image is published | The tag was pushed with `GITHUB_TOKEN`                                                 | Use `RELEASE_TOKEN_STURDY_PARAKEET` so the tag push triggers `publish-image.yml`.                                        |
| `:latest` is missing after a release   | The tag is a pre-release (it contains `-`)                                             | Expected behaviour; publish a stable tag to move `:latest`.                                                              |
| The CD job is skipped                  | Pre-release tag, or the image workflow did not succeed on a push                       | Check the `guard` step and the condition; run the workflow manually with a stable tag if needed.                         |
| Railway authentication fails           | Missing, invalid or expired `RAILWAY_API_TOKEN`                                        | Generate a new Account Token in Railway account settings and update the GitHub secret.                                   |
| Railway cannot identify the project    | Missing or incorrect `RAILWAY_PROJECT_ID`, or the command does not include `--project` | Verify the project identifier and ensure both deployment commands receive `--project "$RAILWAY_PROJECT_ID"`.             |
| `No linked project found`              | The CLI cannot infer the project from the Account Token                                | Pass the project explicitly with `--project "$RAILWAY_PROJECT_ID"`; do not rely on implicit project resolution.          |
| Railway deploys the old image          | The image tag was not found or the service source was not updated                      | Confirm the tag exists in Docker Hub and inspect the `Point service to the published image` step logs.                   |
| Railway cannot pull the image          | Private Docker Hub repository without registry credentials                             | Make the repository public or configure Docker Hub credentials in the Railway service.                                   |
| `railway service source connect` fails | The pinned Railway CLI is older than `5.71.0` or required identifiers are missing      | Keep `RAILWAY_CLI_VERSION` at `5.71.0` or newer and verify the project, service and environment arguments.               |
| The health check fails                 | Wrong URL, `/health` used instead of `/health/ready`, or a dependency is down          | Set `RAILWAY_HEALTHCHECK_URL` to the readiness endpoint and inspect Railway logs, PostgreSQL and Redis.                  |
| CI integration or E2E tests fail       | `.env` missing or Docker not available                                                 | Run `cp .env.example .env` and execute the suites through `make` with Docker running.                                    |
| The coverage job fails                 | Combined coverage is below 70%                                                         | Add tests or cover the untested paths before merging.                                                                    |
| Railway reports an unknown service     | `RAILWAY_SERVICE` does not match the target Railway project                            | Verify the service name or identifier and ensure it belongs to `RAILWAY_PROJECT_ID`.                                     |