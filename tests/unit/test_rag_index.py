import pytest

from aula4api import rag_index


pytestmark = pytest.mark.unit


def make_chunk(index, start, end, content):
    return {
        "chunk_index": index,
        "start_char": start,
        "end_char": end,
        "content": content,
    }


def test_split_text_preserves_offsets_and_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"

    chunks = rag_index.split_text(
        text,
        chunk_chars=10,
        overlap_chars=3,
    )

    assert [chunk["start_char"] for chunk in chunks] == [0, 7, 14, 21]
    assert [chunk["end_char"] for chunk in chunks] == [10, 17, 24, 26]

    for chunk in chunks:
        assert (
            text[chunk["start_char"]:chunk["end_char"]]
            == chunk["content"]
        )


def test_split_text_prefers_paragraph_break():
    text = "Primeiro paragrafo.\n\nSegundo paragrafo."

    chunks = rag_index.split_text(
        text,
        chunk_chars=30,
        overlap_chars=5,
    )

    assert chunks
    assert chunks[0]["content"].endswith("\n\n")
    assert text[
        chunks[0]["start_char"]:chunks[0]["end_char"]
    ] == chunks[0]["content"]


def test_split_text_returns_empty_for_blank_content():
    assert rag_index.split_text("") == []
    assert rag_index.split_text("   \n\n ") == []


def test_extract_title_uses_markdown_heading():
    assert rag_index.extract_title(
        "# Docker Essencial\n\nTexto",
        "README.md",
    ) == "Docker Essencial"
    assert rag_index.extract_title(
        "sem titulo",
        "docs/openapi.yaml",
    ) == "openapi.yaml"


def test_replace_document_and_search_orders_by_score(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        rag_index.replace_document(
            connection,
            "docs/guia.md",
            "Guia",
            "hash-1",
            "embedding-model",
            [
                make_chunk(0, 0, 10, "primeiro"),
                make_chunk(1, 10, 20, "segundo"),
                make_chunk(2, 20, 30, "terceiro"),
            ],
            [
                [1.0, 0.0],
                [0.8, 0.6],
                [0.0, 1.0],
            ],
        )

        results = rag_index.search(
            connection,
            [1.0, 0.0],
            top_k=2,
            min_score=0.5,
        )
    finally:
        connection.close()

    assert [result["content"] for result in results] == [
        "primeiro",
        "segundo",
    ]
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["score"] == pytest.approx(0.8)
    assert results[0]["path"] == "docs/guia.md"
    assert results[0]["title"] == "Guia"
    assert results[0]["range"] == "0-10"


def test_search_empty_index_raises(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        with pytest.raises(rag_index.RAGIndexEmptyError):
            rag_index.search(connection, [1.0, 0.0])
    finally:
        connection.close()


def test_needs_reindex_compares_hash_model_and_force(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        rag_index.replace_document(
            connection,
            "README.md",
            "README",
            "hash-1",
            "model-a",
            [make_chunk(0, 0, 5, "texto")],
            [[1.0, 0.0]],
        )

        assert not rag_index.needs_reindex(
            connection,
            "README.md",
            "hash-1",
            "model-a",
        )
        assert rag_index.needs_reindex(
            connection,
            "README.md",
            "hash-2",
            "model-a",
        )
        assert rag_index.needs_reindex(
            connection,
            "README.md",
            "hash-1",
            "model-b",
        )
        assert rag_index.needs_reindex(
            connection,
            "README.md",
            "hash-1",
            "model-a",
            force=True,
        )
    finally:
        connection.close()


def test_search_rejects_embedding_dimension_mismatch(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        rag_index.replace_document(
            connection,
            "README.md",
            "README",
            "hash-1",
            "model-a",
            [make_chunk(0, 0, 5, "texto")],
            [[1.0, 0.0]],
        )

        with pytest.raises(rag_index.RAGIndexError):
            rag_index.search(connection, [1.0, 0.0, 0.0])
    finally:
        connection.close()


def test_replace_document_rejects_zero_vector(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        with pytest.raises(rag_index.RAGIndexError):
            rag_index.replace_document(
                connection,
                "README.md",
                "README",
                "hash-1",
                "model-a",
                [make_chunk(0, 0, 5, "texto")],
                [[0.0, 0.0]],
            )
    finally:
        connection.close()


def test_get_index_stats(tmp_path):
    connection = rag_index.connect(tmp_path / "index.sqlite3")

    try:
        rag_index.replace_document(
            connection,
            "README.md",
            "README",
            "hash-1",
            "model-a",
            [
                make_chunk(0, 0, 5, "texto"),
                make_chunk(1, 5, 10, "mais"),
            ],
            [[1.0, 0.0], [0.0, 1.0]],
        )

        assert rag_index.get_index_stats(connection) == {
            "documents": 1,
            "chunks": 2,
        }
    finally:
        connection.close()
