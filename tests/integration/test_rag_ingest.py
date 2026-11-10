import pytest

from aula4api import rag, rag_index


pytestmark = pytest.mark.integration


class FakeEmbedder:
    model = "fake-embedding-model"

    def embed(self, texts):
        return [
            [0.0, 1.0] if "operationId" in text else [1.0, 0.0]
            for text in texts
        ]


def test_ingest_real_documentation_and_search(tmp_path):
    index_path = tmp_path / "rag_index.sqlite3"
    stats = rag.ingest_documents(
        index_path=index_path,
        embedder=FakeEmbedder(),
    )

    assert stats["documents"] >= 2
    assert stats["chunks"] > 0
    assert stats["updated"] == 2
    assert stats["skipped"] == 0
    assert "README.md" in stats["paths"]
    assert "docs/openapi.yaml" in stats["paths"]

    connection = rag_index.connect(index_path)

    try:
        readme_results = rag_index.search(
            connection,
            [1.0, 0.0],
            top_k=5,
            min_score=0.1,
        )
        openapi_results = rag_index.search(
            connection,
            [0.0, 1.0],
            top_k=5,
            min_score=0.1,
        )
    finally:
        connection.close()

    assert "README.md" in {
        result["path"] for result in readme_results
    }
    assert "docs/openapi.yaml" in {
        result["path"] for result in openapi_results
    }
    assert all(
        result["score"] > 0
        for result in readme_results + openapi_results
    )
