import math
import os
import random
import time

import httpx

from .llm_service import (
    LLMConfigurationError,
    LLMInvalidPayloadError,
    LLMProviderError,
    LLMRateLimitError,
)


class EmbeddingConfigurationError(LLMConfigurationError):
    pass


class EmbeddingRateLimitError(LLMRateLimitError):
    pass


class EmbeddingProviderError(LLMProviderError):
    pass


class EmbeddingInvalidPayloadError(LLMInvalidPayloadError):
    pass


def _env_float(name, default, minimum, maximum):
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return float(default)

    return min(maximum, max(minimum, value))


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)

    return min(maximum, max(minimum, value))


class EmbeddingService:
    def __init__(
        self,
        post=None,
        sleeper=None,
        uniform=None,
    ):
        self.api_url = os.getenv(
            "EMBEDDING_API_URL",
            "https://api.openai.com/v1/embeddings",
        ).strip()
        self.api_key = (
            os.getenv("EMBEDDING_API_KEY", "").strip()
            or os.getenv("LLM_API_KEY", "").strip()
        )
        self.model = os.getenv(
            "EMBEDDING_MODEL",
            "replace-with-supported-embedding-model",
        ).strip()
        self.timeout_seconds = _env_float(
            "EMBEDDING_TIMEOUT_SECONDS",
            10,
            0.1,
            30,
        )
        self.max_attempts = _env_int(
            "EMBEDDING_MAX_RETRIES",
            3,
            1,
            3,
        )
        self.retry_base_seconds = _env_float(
            "EMBEDDING_RETRY_BASE_SECONDS",
            0.2,
            0,
            2,
        )
        self.batch_size = _env_int(
            "EMBEDDING_BATCH_SIZE",
            32,
            1,
            2048,
        )

        self._post = post or httpx.post
        self._sleep = sleeper or time.sleep
        self._uniform = uniform or random.uniform

    def _ensure_configured(self):
        if not self.api_url:
            raise EmbeddingConfigurationError(
                "EMBEDDING_API_URL nao configurada."
            )

        if not self.api_key:
            raise EmbeddingConfigurationError(
                "EMBEDDING_API_KEY ou LLM_API_KEY nao configurada."
            )

        if (
            not self.model
            or self.model == "replace-with-supported-embedding-model"
        ):
            raise EmbeddingConfigurationError(
                "EMBEDDING_MODEL nao aponta para um modelo configurado."
            )

    def _retry_delay(self, attempt):
        ceiling = self.retry_base_seconds * (2 ** (attempt - 1))
        return ceiling + self._uniform(0, ceiling)

    def _request_batch(self, batch):
        payload = {
            "model": self.model,
            "input": batch,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx.HTTPError as exc:
                if attempt >= self.max_attempts:
                    raise EmbeddingProviderError(
                        "Provedor de embeddings indisponivel "
                        "apos as tentativas."
                    ) from exc

                self._sleep(self._retry_delay(attempt))
                continue
            except OSError as exc:
                if attempt >= self.max_attempts:
                    raise EmbeddingProviderError(
                        "Falha de rede ao gerar embeddings."
                    ) from exc

                self._sleep(self._retry_delay(attempt))
                continue

            status_code = int(response.status_code)

            if status_code in (408, 429) or status_code >= 500:
                if attempt < self.max_attempts:
                    self._sleep(self._retry_delay(attempt))
                    continue

                if status_code == 429:
                    raise EmbeddingRateLimitError(
                        "Provedor manteve HTTP 429 apos as tentativas."
                    )

                raise EmbeddingProviderError(
                    f"Provedor de embeddings retornou HTTP {status_code}."
                )

            if status_code >= 400:
                raise EmbeddingProviderError(
                    "Provedor de embeddings rejeitou a requisicao "
                    f"com HTTP {status_code}."
                )

            return self._parse_response(response, len(batch))

        raise EmbeddingProviderError(
            "Falha inesperada na comunicacao com o provedor de embeddings."
        )

    @staticmethod
    def _parse_response(response, expected_count):
        try:
            data = response.json()
        except (ValueError, TypeError) as exc:
            raise EmbeddingInvalidPayloadError(
                "Provedor retornou JSON invalido."
            ) from exc

        if not isinstance(data, dict):
            raise EmbeddingInvalidPayloadError(
                "Resposta do provedor nao e um objeto JSON."
            )

        items = data.get("data")

        if not isinstance(items, list) or len(items) != expected_count:
            raise EmbeddingInvalidPayloadError(
                "Resposta do provedor nao contem todos os embeddings."
            )

        ordered = []
        dimensions = set()

        for position, item in enumerate(items):
            if not isinstance(item, dict):
                raise EmbeddingInvalidPayloadError(
                    "Item de embedding invalido."
                )

            index = item.get("index")

            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < expected_count
            ):
                raise EmbeddingInvalidPayloadError(
                    "Indice de embedding invalido."
                )

            vector = item.get("embedding")

            if not isinstance(vector, list) or not vector:
                raise EmbeddingInvalidPayloadError(
                    "Embedding invalido."
                )

            try:
                values = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise EmbeddingInvalidPayloadError(
                    "Embedding invalido."
                ) from exc

            if any(not math.isfinite(value) for value in values):
                raise EmbeddingInvalidPayloadError(
                    "Embedding contem valores invalidos."
                )

            dimensions.add(len(values))
            ordered.append((index, values))

        if len(dimensions) != 1:
            raise EmbeddingInvalidPayloadError(
                "Embeddings com dimensoes diferentes."
            )

        ordered.sort(key=lambda item: item[0])
        indexes = [index for index, _ in ordered]

        if indexes != list(range(expected_count)):
            raise EmbeddingInvalidPayloadError(
                "Indices de embedding duplicados ou ausentes."
            )

        return [values for _, values in ordered]

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        if not isinstance(texts, (list, tuple)):
            raise ValueError(
                "Os textos para embedding devem ser uma lista."
            )

        normalized = []

        for text in texts:
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    "Os textos para embedding nao podem ser vazios."
                )

            normalized.append(text)

        if not normalized:
            return []

        self._ensure_configured()
        embeddings = []
        dimensions = set()

        for start in range(0, len(normalized), self.batch_size):
            batch = normalized[start:start + self.batch_size]
            batch_embeddings = self._request_batch(batch)

            for embedding in batch_embeddings:
                dimensions.add(len(embedding))

            embeddings.extend(batch_embeddings)

        if len(dimensions) != 1:
            raise EmbeddingInvalidPayloadError(
                "Embeddings com dimensoes diferentes."
            )

        return embeddings


embedding_service = EmbeddingService()
