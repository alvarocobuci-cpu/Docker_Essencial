import hashlib
from pathlib import Path

from . import rag_index
from .llm_service import llm_service
from .rag_embeddings import embedding_service as default_embedding_service


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENT_PATHS = (
    "README.md",
    "docs/openapi.yaml",
)
DEFAULT_TOP_K = rag_index.DEFAULT_TOP_K
DEFAULT_MIN_SCORE = rag_index.DEFAULT_MIN_SCORE
MAX_TOP_K = rag_index.MAX_TOP_K

NO_ANSWER_TEXT = (
    "Nao encontrei informacao suficiente na documentacao indexada "
    "para responder a essa pergunta."
)


def _resolve_document_path(path):
    candidate = Path(path).expanduser()

    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate

    return candidate.resolve()


def _document_label(path):
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_answer_request(question, top_k, min_score):
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Pergunta invalida.")

    question = question.strip()

    if len(question) > 500:
        raise ValueError("A pergunta excede o limite de 500 caracteres.")

    if isinstance(top_k, bool):
        raise ValueError("top_k deve estar entre 1 e 5.")

    try:
        top_k = int(top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("top_k deve estar entre 1 e 5.") from exc

    if not 1 <= top_k <= MAX_TOP_K:
        raise ValueError("top_k deve estar entre 1 e 5.")

    try:
        min_score = float(min_score)
    except (TypeError, ValueError) as exc:
        raise ValueError("min_score deve estar entre 0 e 1.") from exc

    if not 0.0 <= min_score <= 1.0:
        raise ValueError("min_score deve estar entre 0 e 1.")

    return question, top_k, min_score


def build_context(results):
    blocks = []

    for result in results:
        content = result["content"].strip()
        blocks.append(
            f"[{result['path']}#{result['range']}]\n{content}"
        )

    return "\n\n".join(blocks)


def answer(
    question,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE,
    index_path=None,
    embedder=None,
    llm=None,
):
    question, top_k, min_score = _validate_answer_request(
        question,
        top_k,
        min_score,
    )
    embedder = embedder or default_embedding_service
    llm = llm or llm_service
    connection = rag_index.connect(index_path)

    try:
        rag_index.ensure_not_empty(connection)
        query_embedding = embedder.embed([question])[0]
        results = rag_index.search(
            connection,
            query_embedding,
            top_k=top_k,
            min_score=min_score,
        )
    finally:
        connection.close()

    meta = {
        "top_k": top_k,
        "min_score": min_score,
        "retrieved": len(results),
        "llm": {},
    }

    if not results:
        return {
            "question": question,
            "answer": NO_ANSWER_TEXT,
            "sources": [],
            "meta": meta,
        }

    sources = [
        {
            "path": result["path"],
            "title": result["title"],
            "range": result["range"],
            "score": result["score"],
        }
        for result in results
    ]
    llm_result = llm.generate_docs_answer(
        question,
        build_context(results),
    )
    meta["llm"] = llm_result.get("meta", {})

    return {
        "question": question,
        "answer": llm_result["answer"],
        "sources": sources,
        "meta": meta,
    }


def ingest_documents(
    paths=None,
    index_path=None,
    force=False,
    embedder=None,
):
    embedder = embedder or default_embedding_service
    embedding_model = getattr(
        embedder,
        "model",
        "unknown-embedding-model",
    )
    selected_paths = paths or DEFAULT_DOCUMENT_PATHS
    connection = rag_index.connect(index_path)
    updated = 0
    skipped = 0
    indexed_paths = []

    try:
        for raw_path in selected_paths:
            path = _resolve_document_path(raw_path)

            if not path.is_file():
                raise rag_index.RAGIndexError(
                    f"Documento nao encontrado: {path}"
                )

            text = path.read_text(encoding="utf-8")
            content_hash = _content_hash(text)
            label = _document_label(path)

            if not rag_index.needs_reindex(
                connection,
                label,
                content_hash,
                embedding_model,
                force=force,
            ):
                skipped += 1
                indexed_paths.append(label)
                continue

            chunks = rag_index.split_text(text)

            if not chunks:
                raise rag_index.RAGIndexError(
                    f"Documento sem conteudo indexavel: {label}"
                )

            embeddings = embedder.embed(
                [chunk["content"].strip() for chunk in chunks]
            )
            rag_index.replace_document(
                connection,
                label,
                rag_index.extract_title(text, label),
                content_hash,
                embedding_model,
                chunks,
                embeddings,
            )
            updated += 1
            indexed_paths.append(label)

        stats = rag_index.get_index_stats(connection)
    finally:
        connection.close()

    return {
        **stats,
        "updated": updated,
        "skipped": skipped,
        "paths": indexed_paths,
    }
