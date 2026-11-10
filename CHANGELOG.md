# Changelog

All notable changes to this project are recorded in this file.

## [Unreleased] - Aula 24

### Added
- Added a SQLite RAG index with document/chunk storage, character offsets and cosine search.
- Added an OpenAI-compatible embedding client with batching, retries and payload validation.
- Added explicit documentation ingestion through `python app/manage.py ingest_docs`.
- Added the authenticated `POST /api/v1/ask_docs` endpoint with citations and guardrails.
- Added a documentation-answer prompt with untrusted-context handling and redaction.
- Added the `rag_index_data` Compose volume and `README.md` in the API image.
- Added unit and integration tests for the RAG index, embeddings, service, API and real documentation ingestion.
- Added Aula 24 documentation to README and PROMPTS.

### Changed
- Documented `EMBEDDING_*` and `RAG_*` variables in `.env.example` and Docker Compose.
- Added local RAG index paths to `.gitignore` and `.dockerignore`.
- Added RAG OpenAPI schemas and the `ask_docs` operation.

### Validation
- RAG-focused unit and integration tests passed.
- `ruff check --no-cache .` passed.
- Full `pytest` suite passed.
- `python app/manage.py check` passed.
- `docker compose config --quiet` passed.
- API image build and `ingest_docs --help` validation passed.

## [Unreleased] - Aula 23

### Added
- Added pip dependency caching to the CI workflow.
- Added a `compose-validation` job that builds API/dashboard images and validates service communication.
- Added API and dashboard healthchecks to Docker Compose.
- Added a DockerHub publish job using `docker/login-action` and `docker/build-push-action` with GHA cache.
- Added Aula 23 documentation to README and PROMPTS.

### Changed
- Replaced the standalone `docker-build` job with Compose-based build and validation.
- Changed the dashboard dependency to wait for a healthy API.
- Updated Aula 22 limitations to reference the Aula 23 implementation.

### Validation
- Workflow YAML parsed successfully.
- `docker compose config --quiet` passed.
- `ruff check --no-cache .` passed.
- Full `pytest` suite passed.
- API and dashboard images built with Docker Compose.
- API, dashboard, PostgreSQL and Kafka started with healthchecks.
- API-to-PostgreSQL, dashboard-to-PostgreSQL and dashboard-to-API checks passed.
- `git diff --check` passed.

## [Unreleased] - Aula 22

### Added
- Added a GitHub Actions CI workflow with `test-and-lint` and `docker-build` jobs.
- Added `requirements-dev.txt` with Ruff and a `.ruff.toml` configuration.
- Added a README section and status badge for the CI pipeline.
- Added CI documentation to `PROMPTS.md`.

### Changed
- `SECRET_KEY` can now be supplied through the environment.
- Added `SECRET_KEY` to `.env.example` and Docker Compose Django services.
- Cleaned lint findings in existing Python files.
- Ignored CI test reports in `.gitignore`.

### Validation
- Workflow YAML parsed successfully.
- `ruff check --no-cache .` passed.
- Full `pytest` suite passed.
- `docker build -t synapseshop-api:test .` passed.
- Ephemeral PostgreSQL with TLS started and accepted connections.

## [Unreleased] - Aula 21

### Added
- Added the POST /api/v1/ask_sql endpoint for natural-language questions converted to read-only SQL.
- Added a curated schema context and validation rules for single SELECT statements, allowed tables and blocked identifiers.
- Added read-only query execution with statement timeout and row limits.
- Added the `generate_sql` flow to the LLM service with SQL-specific prompts and no answer redaction.
- Added the Consulta IA Streamlit page and an HTTP client with JWT login and token refresh.
- Added environment variables for row limits, statement timeout, API base URL and an optional dashboard token.
- Added unit tests for SQL extraction, validation, serialization, endpoint error mapping, HTTP client behavior and SQL generation.

### Changed
- Added `sqlparse` to the API requirements and `httpx` to the dashboard requirements.
- Updated Docker Compose, `.env.example`, README, PROMPTS and OpenAPI documentation.

### Validation
- Docker Compose configuration validated.
- OpenAPI lint passed with Redocly.
- Unit and integration tests for the new modules and endpoint executed with pytest.
- Read-only execution validated against the local PostgreSQL database.

## [Unreleased] - Aula 20

### Added
- Added the Streamlit performance dashboard consuming HTTP metrics from Redis.
- Added KPI cards for total requests, average latency, p95 latency and error rate.
- Added latency, throughput and HTTP status distribution charts.
- Added period, endpoint and status filters with `@st.cache_data` caching.
- Added inventory cache metrics and a messaging section with an empty state.
- Added the `performance-dashboard` service to Docker Compose on port 8502.
- Added unit tests for metric event building and dashboard data transformations.

### Changed
- Registered `APIMetricsMiddleware` to record `/api/v1/` request metrics.
- Documented dashboard usage, environment variables and limitations in README and PROMPTS.
- Restored the sales dashboard `depends_on` for the database service.

### Validation
- Docker Compose configuration validated.
- Performance dashboard image built and health endpoint checked.
- Unit tests for metrics and dashboard helpers passed.

## [Aula 13]

### Documentation
- Added a combined OpenAPI 3.0.3 contract for the Django API and inventory API.
- Added Django-hosted OpenAPI YAML, Swagger UI and ReDoc pages.
- Added Redocly CLI lint configuration for existing route conventions.
- Added a Postman collection with 29 requests and a local environment.
- Added the external integrator checklist.
- Documented the current pagination, filtering, ordering, authentication, idempotency and rate limits.
- Recorded that X-Trace-Id and complete RFC 7807 error responses are not implemented yet.

### Validation
- Redocly CLI lint passed without errors or warnings.
- Documentation endpoints returned HTTP 200 in local verification.
- Postman collection and environment JSON files parsed successfully.

## [Unreleased] - Aula 14

### Added
- Added the LLM service for summarizing and explaining application logs.
- Added the POST /api/v1/assist endpoint with request validation.
- Added environment variables for provider configuration, timeout, retries, circuit breaker and estimated token costs.
- Added redaction rules for common patterns of personal information and secrets before sending logs and returning model responses.
- Added prompt templates for summarize and explain modes.
- Added structured telemetry for latency, errors, token usage and estimated costs.
- Added unit tests for timeouts, HTTP 429, HTTP 5xx, provider unavailability, invalid responses, circuit breaker and sensitive-data redaction.
- Added API endpoint tests for successful requests, invalid payloads and provider error handling.
- Updated README.md and PROMPTS.md with Aula 14 information.

### Validation
- Docker API image rebuilt successfully.
- Python syntax checks passed for the modified API files.
- Django system check passed without issues.
- LLM service tests: 14 passed.
- Assist endpoint tests: 11 passed.
- Full test suite: 77 passed, with one Starlette/AnyIO deprecation warning.

### Notes
- Provider calls were mocked during automated tests; no real external LLM call was validated.
- Cost estimates depend on the configured rates for the selected model.
- Sensitive-data redaction uses known patterns and may not detect every confidential value.
- Telemetry aggregates are kept in memory in the current implementation.