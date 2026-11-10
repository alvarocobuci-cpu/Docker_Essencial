import pytest

from aula4api import rag, rag_index


pytestmark = pytest.mark.unit


class FakeEmbedder:
    model = "fake-embedding-model"

    def __init__(self, vectors=None):
        self.vectors = vectors
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))

        if self.vectors is not None:
            return self.vectors[:len(texts)]

        return [[1.0, 0.0] for _ in texts]


class FakeLLM:
    def __init__(self):
        self.calls = []

    def generate_docs_answer(self, question, context):
        self.calls.append(
            {
                "question": question,
                "context": context,
            }
        )
        return {
            "answer": "Use Docker Compose. [README.md#0-5]",
            "meta": {"latency_ms": 1.0},
        }


def build_index(tmp_path, embeddings):
    index_path = tmp_path / "index.sqlite3"
    connection = rag_index.connect(index_path)

    try:
        rag_index.replace_document(
            connection,
            "README.md",
            "Docker Essencial",
            "hash-1",
            "fake-embedding-model",
            [
                {
                    "chunk_index": 0,
                    "start_char": 0,
                    "end_char": 5,
                    "content": "texto",
                }
            ],
            embeddings,
        )
    finally:
        connection.close()

    return index_path


def test_build_context_includes_citation_identifier():
    context = rag.build_context(
        [
            {
                "path": "README.md",
                "range": "10-20",
                "content": "conteudo",
            }
        ]
    )

    assert context == "[README.md#10-20]\nconteudo"


def test_answer_returns_sources_and_llm_metadata(tmp_path):
    index_path = build_index(tmp_path, [[1.0, 0.0]])
    embedder = FakeEmbedder()
    llm = FakeLLM()

    result = rag.answer(
        "Como subir?",
        index_path=index_path,
        embedder=embedder,
        llm=llm,
    )

    assert result["question"] == "Como subir?"
    assert result["answer"] == "Use Docker Compose. [README.md#0-5]"
    assert result["sources"] == [
        {
            "path": "README.md",
            "title": "Docker Essencial",
            "range": "0-5",
            "score": 1.0,
        }
    ]
    assert result["meta"]["retrieved"] == 1
    assert result["meta"]["llm"] == {"latency_ms": 1.0}
    assert llm.calls[0]["context"] == "[README.md#0-5]\ntexto"


def test_answer_returns_guardrail_without_llm_when_no_chunk_matches(
    tmp_path,
):
    index_path = build_index(tmp_path, [[0.0, 1.0]])
    embedder = FakeEmbedder(vectors=[[1.0, 0.0]])
    llm = FakeLLM()

    result = rag.answer(
        "Como subir?",
        min_score=0.5,
        index_path=index_path,
        embedder=embedder,
        llm=llm,
    )

    assert result["answer"] == rag.NO_ANSWER_TEXT
    assert result["sources"] == []
    assert result["meta"]["retrieved"] == 0
    assert llm.calls == []


def test_answer_rejects_empty_index_before_embedding(tmp_path):
    index_path = tmp_path / "empty.sqlite3"
    connection = rag_index.connect(index_path)
    connection.close()
    embedder = FakeEmbedder()
    llm = FakeLLM()

    with pytest.raises(rag_index.RAGIndexEmptyError):
        rag.answer(
            "Como subir?",
            index_path=index_path,
            embedder=embedder,
            llm=llm,
        )

    assert embedder.calls == []
    assert llm.calls == []


def test_ingest_skips_unchanged_document_and_force_reindexes(tmp_path):
    document = tmp_path / "guia.md"
    document.write_text(
        "# Guia\n\nConteudo de teste.",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.sqlite3"
    embedder = FakeEmbedder()

    first = rag.ingest_documents(
        paths=[str(document)],
        index_path=index_path,
        embedder=embedder,
    )
    second = rag.ingest_documents(
        paths=[str(document)],
        index_path=index_path,
        embedder=embedder,
    )
    third = rag.ingest_documents(
        paths=[str(document)],
        index_path=index_path,
        force=True,
        embedder=embedder,
    )

    assert first["updated"] == 1
    assert first["skipped"] == 0
    assert second["updated"] == 0
    assert second["skipped"] == 1
    assert third["updated"] == 1
    assert third["skipped"] == 0
    assert len(embedder.calls) == 2


def test_ingest_rejects_missing_document(tmp_path):
    with pytest.raises(rag_index.RAGIndexError):
        rag.ingest_documents(
            paths=[str(tmp_path / "missing.md")],
            index_path=tmp_path / "index.sqlite3",
            embedder=FakeEmbedder(),
        )


@pytest.mark.parametrize(
    "question,top_k,min_score",
    [
        ("", 3, 0.25),
        ("   ", 3, 0.25),
        ("x" * 501, 3, 0.25),
        ("pergunta", 0, 0.25),
        ("pergunta", 6, 0.25),
        ("pergunta", 3, -0.1),
        ("pergunta", 3, 1.1),
    ],
)
def test_answer_rejects_invalid_parameters(
    tmp_path,
    question,
    top_k,
    min_score,
):
    index_path = build_index(tmp_path, [[1.0, 0.0]])

    with pytest.raises(ValueError):
        rag.answer(
            question,
            top_k=top_k,
            min_score=min_score,
            index_path=index_path,
            embedder=FakeEmbedder(),
            llm=FakeLLM(),
        )
