# Aula 12 - Draft technical issues

These are local drafts. They are not yet GitHub issues.

## Issue 1 - Extend coverage to Django API and workers

Context: current coverage includes inventory, aula4api.idempotency and aula4api.event_contracts. Django views and worker modules are not included in the measured scope.

Tasks:
- Test Django views, authentication, request validation and Kafka publishing with mocks.
- Test success, duplicate delivery, retry and error paths in payment_worker.py and notification_worker.py.
- Expand coverage progressively without excluding production modules merely to increase the percentage.

Acceptance: tests pass in Docker and the expanded coverage target is documented.

## Issue 2 - Resolve TestClient deprecation warning

Context: pytest reports a DeprecationWarning related to starlette.testclient and anyio.abc.BlockingPortal.

Tasks:
- Identify compatible FastAPI, Starlette and AnyIO versions.
- Pin compatible versions.
- Rerun the complete suite.

Acceptance: tests pass and the warning is removed or its temporary retention is documented.

## Issue 3 - Run pytest and coverage in CI

Context: tests are currently run manually in Docker.

Tasks:
- Add a CI pipeline for pull requests.
- Publish the coverage report.
- Fail the pipeline when measured coverage falls below 85%.

Acceptance: CI demonstrates successful tests and enforcement of the coverage threshold.

## Issue 4 - Test Kafka retries and dead-letter queues

Context: Redis is isolated with fakes, and consumers do not yet have full automated integration tests against Kafka.

Tasks:
- Add controlled integration tests for consumption, retries and DLQ publishing.
- Cover duplicate delivery and failures between persistence and offset commit.
- Ensure test messages and data are cleaned up.

Acceptance: scenarios run repeatably without interfering with development data.
