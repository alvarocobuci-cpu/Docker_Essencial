import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = int(os.environ.get(name, str(default)))

    if not minimum <= value <= maximum:
        raise ValueError(
            f"{name} deve estar entre {minimum} e {maximum}."
        )

    return value


DB_USER = os.environ.get("DB_USER") or os.environ.get(
    "POSTGRES_USER", "appuser"
)
DB_PASSWORD = os.environ.get("DB_PASSWORD") or os.environ.get(
    "POSTGRES_PASSWORD", ""
)
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = _env_int("DB_PORT", 5432, 1, 65535)
DB_NAME = os.environ.get("DB_NAME") or os.environ.get(
    "POSTGRES_DB", "appdb"
)
DB_SSLMODE = os.environ.get("DB_SSLMODE", "require").strip().lower()

if not DB_PASSWORD:
    raise RuntimeError(
        "Configure DB_PASSWORD ou POSTGRES_PASSWORD no ambiente."
    )

if DB_SSLMODE != "require":
    raise ValueError(
        "DB_SSLMODE deve ser 'require' nesta configuracao."
    )


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=_env_int("DB_POOL_SIZE", 5, 1, 20),
    max_overflow=_env_int("DB_MAX_OVERFLOW", 10, 0, 50),
    pool_timeout=_env_int("DB_POOL_TIMEOUT_SECONDS", 10, 1, 120),
    pool_recycle=_env_int("DB_POOL_RECYCLE_SECONDS", 1800, 60, 86400),
    connect_args={
        "sslmode": DB_SSLMODE,
        "connect_timeout": _env_int(
            "DB_CONNECT_TIMEOUT_SECONDS", 5, 1, 30
        ),
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()