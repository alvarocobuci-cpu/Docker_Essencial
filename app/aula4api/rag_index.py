import math
import os
import re
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CHUNK_TOKENS = 400
DEFAULT_CHUNK_OVERLAP_TOKENS = 80
CHARS_PER_TOKEN = 4
DEFAULT_TOP_K = 3
MAX_TOP_K = 5
DEFAULT_MIN_SCORE = 0.25

RAG_INDEX_EMPTY_MESSAGE = (
    "O indice RAG esta vazio. Execute "
    "'python app/manage.py ingest_docs' para indexar a documentacao."
)

_HEADING_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
_BREAK_CANDIDATES = ("\n\n", "\n", ". ", " ")


class RAGIndexError(Exception):
    pass


class RAGIndexEmptyError(RAGIndexError):
    pass


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)

    return min(maximum, max(minimum, value))


def default_index_path():
    return APP_DIR / "data" / "rag_index.sqlite3"


def resolve_index_path(index_path=None):
    if index_path is not None:
        return Path(index_path).expanduser()

    configured = os.getenv("RAG_INDEX_PATH", "").strip()

    if configured:
        return Path(configured).expanduser()

    return default_index_path()


def chunk_settings():
    chunk_tokens = _env_int(
        "RAG_CHUNK_TOKENS",
        DEFAULT_CHUNK_TOKENS,
        50,
        2000,
    )
    overlap_tokens = _env_int(
        "RAG_CHUNK_OVERLAP_TOKENS",
        DEFAULT_CHUNK_OVERLAP_TOKENS,
        0,
        max(0, chunk_tokens - 1),
    )

    return (
        chunk_tokens * CHARS_PER_TOKEN,
        overlap_tokens * CHARS_PER_TOKEN,
    )


def extract_title(text, path):
    match = _HEADING_RE.search(text)

    if match:
        return match.group(1).strip()

    return Path(path).name


def split_text(text, chunk_chars=None, overlap_chars=None):
    if not isinstance(text, str) or not text.strip():
        return []

    if chunk_chars is None or overlap_chars is None:
        default_chunk_chars, default_overlap_chars = chunk_settings()
        chunk_chars = (
            default_chunk_chars
            if chunk_chars is None
            else int(chunk_chars)
        )
        overlap_chars = (
            default_overlap_chars
            if overlap_chars is None
            else int(overlap_chars)
        )

    chunk_chars = max(1, int(chunk_chars))
    overlap_chars = max(0, min(int(overlap_chars), chunk_chars - 1))

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_chars, text_length)

        if end < text_length:
            end = _find_break(text, start, end, chunk_chars)

        content = text[start:end]

        if content.strip():
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "start_char": start,
                    "end_char": end,
                    "content": content,
                }
            )

        if end >= text_length:
            break

        next_start = max(start + 1, end - overlap_chars)
        start = next_start

    return chunks


def _find_break(text, start, end, chunk_chars):
    minimum_break = start + max(1, int(chunk_chars * 0.6))

    for delimiter in _BREAK_CANDIDATES:
        position = text.rfind(delimiter, minimum_break, end)

        if position == -1:
            continue

        candidate_end = position + len(delimiter)

        if candidate_end > minimum_break:
            return candidate_end

    return end


def connect(index_path=None):
    path = resolve_index_path(index_path)

    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        str(path),
        timeout=5.0,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    init_schema(connection)

    return connection


def init_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_dim INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL
                REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            start_char INTEGER NOT NULL,
            end_char INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            UNIQUE(document_id, chunk_index)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_document_id
            ON chunks(document_id);
        """
    )
    connection.commit()


def get_document(connection, path):
    row = connection.execute(
        "SELECT * FROM documents WHERE path = ?",
        (str(path),),
    ).fetchone()

    return dict(row) if row else None


def needs_reindex(
    connection,
    path,
    content_hash,
    embedding_model,
    force=False,
):
    if force:
        return True

    document = get_document(connection, path)

    if document is None:
        return True

    return (
        document["content_hash"] != content_hash
        or document["embedding_model"] != embedding_model
    )


def replace_document(
    connection,
    path,
    title,
    content_hash,
    embedding_model,
    chunks,
    embeddings,
):
    if len(chunks) != len(embeddings):
        raise RAGIndexError(
            "A quantidade de chunks e embeddings nao corresponde."
        )

    if not chunks:
        raise RAGIndexError(
            "O documento nao possui conteudo indexavel."
        )

    packed_embeddings = []
    dimensions = set()

    for embedding in embeddings:
        normalized, dimension = normalize_vector(embedding)
        packed_embeddings.append(pack_vector(normalized))
        dimensions.add(dimension)

    if len(dimensions) != 1:
        raise RAGIndexError(
            "Os embeddings do documento possuem dimensoes diferentes."
        )

    embedding_dim = dimensions.pop()
    updated_at = datetime.now(timezone.utc).isoformat()

    with connection:
        connection.execute(
            "DELETE FROM documents WHERE path = ?",
            (str(path),),
        )
        cursor = connection.execute(
            """
            INSERT INTO documents (
                path,
                title,
                content_hash,
                embedding_model,
                embedding_dim,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(path),
                title,
                content_hash,
                embedding_model,
                embedding_dim,
                updated_at,
            ),
        )
        document_id = cursor.lastrowid

        connection.executemany(
            """
            INSERT INTO chunks (
                document_id,
                chunk_index,
                start_char,
                end_char,
                content,
                embedding
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    chunk["chunk_index"],
                    chunk["start_char"],
                    chunk["end_char"],
                    chunk["content"],
                    packed,
                )
                for chunk, packed in zip(
                    chunks,
                    packed_embeddings,
                )
            ],
        )

    return {
        "document_id": document_id,
        "chunks": len(chunks),
        "embedding_dim": embedding_dim,
    }


def get_index_stats(connection):
    documents = connection.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()[0]
    chunks = connection.execute(
        "SELECT COUNT(*) FROM chunks"
    ).fetchone()[0]

    return {
        "documents": int(documents),
        "chunks": int(chunks),
    }


def ensure_not_empty(connection):
    stats = get_index_stats(connection)

    if stats["documents"] == 0 or stats["chunks"] == 0:
        raise RAGIndexEmptyError(RAG_INDEX_EMPTY_MESSAGE)

    return stats


def search(
    connection,
    query_embedding,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE,
):
    ensure_not_empty(connection)

    top_k = max(1, min(int(top_k), MAX_TOP_K))
    min_score = max(0.0, min(float(min_score), 1.0))
    normalized_query, query_dim = normalize_vector(query_embedding)

    rows = connection.execute(
        """
        SELECT
            d.path,
            d.title,
            c.start_char,
            c.end_char,
            c.content,
            c.embedding
        FROM chunks AS c
        JOIN documents AS d ON d.id = c.document_id
        """
    ).fetchall()

    results = []

    for row in rows:
        embedding = unpack_vector(row["embedding"])

        if len(embedding) != query_dim:
            raise RAGIndexError(
                "A dimensao do embedding consultado difere da dimensao "
                "do indice. Reindexe com --force."
            )

        score = cosine_similarity(normalized_query, embedding)

        if score < min_score:
            continue

        results.append(
            {
                "path": row["path"],
                "title": row["title"],
                "range": f"{row['start_char']}-{row['end_char']}",
                "start_char": row["start_char"],
                "end_char": row["end_char"],
                "score": round(score, 6),
                "content": row["content"],
            }
        )

    results.sort(
        key=lambda item: (
            -item["score"],
            item["path"],
            item["start_char"],
        )
    )

    return results[:top_k]


def normalize_vector(vector):
    if isinstance(vector, (str, bytes, bytearray)):
        raise RAGIndexError("Embedding invalido.")

    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError) as exc:
        raise RAGIndexError("Embedding invalido.") from exc

    if not values or any(not math.isfinite(value) for value in values):
        raise RAGIndexError("Embedding invalido.")

    norm = math.sqrt(sum(value * value for value in values))

    if norm == 0:
        raise RAGIndexError("Embedding com norma zero.")

    return [value / norm for value in values], len(values)


def pack_vector(vector):
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(blob):
    if not blob or len(blob) % 4 != 0:
        raise RAGIndexError("Embedding armazenado invalido.")

    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def cosine_similarity(left, right):
    if len(left) != len(right):
        raise RAGIndexError(
            "Os vetores possuem dimensoes diferentes."
        )

    return sum(a * b for a, b in zip(left, right))
