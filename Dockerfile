# =========================
# ETAPA 1 - BUILD
# =========================
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt


# =========================
# ETAPA 2 - RUNTIME
# =========================
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY docs/ ./docs/
COPY README.md ./README.md

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

CMD ["python", "app/manage.py", "runserver", "0.0.0.0:8000"]