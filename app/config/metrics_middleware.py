"""Middleware de monitoramento de desempenho da API."""

import logging
import time

from .metrics import record_request_metric

logger = logging.getLogger(__name__)


class APIMetricsMiddleware:
    """Registra latência e status das requisições da API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Monitora somente os endpoints da API principal.
        if not request.path.startswith("/api/v1/"):
            return self.get_response(request)

        started_at = time.perf_counter()

        try:
            response = self.get_response(request)

        except Exception:
            duration_ms = (
                time.perf_counter() - started_at
            ) * 1000

            self._record_metric(
                request=request,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = (
            time.perf_counter() - started_at
        ) * 1000

        self._record_metric(
            request=request,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response

    @staticmethod
    def _record_metric(request, status_code, duration_ms):
        try:
            resolver_match = request.resolver_match

            endpoint = (
                resolver_match.route
                if resolver_match
                else request.path
            )

            record_request_metric(
                method=request.method,
                endpoint=f"/{endpoint.lstrip('/')}",
                status_code=status_code,
                duration_ms=duration_ms,
            )

        except Exception:
            # Falhas nas métricas não podem interromper a API.
            logger.warning(
                "Falha ao registrar métrica HTTP.",
                exc_info=True,
            )