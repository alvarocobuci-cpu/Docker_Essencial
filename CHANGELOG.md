# Changelog

All notable changes to this project are recorded in this file.

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