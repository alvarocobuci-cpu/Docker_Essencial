from flask import Flask, jsonify
import os
import psycopg

app = Flask(__name__)


def verificar_banco():
    try:
        conexao = psycopg.connect(
            host=os.getenv("DB_HOST", "db"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("POSTGRES_DB", "appdb"),
            user=os.getenv("POSTGRES_USER", "appuser"),
            password=os.getenv("POSTGRES_PASSWORD", "apppassword"),
            connect_timeout=3,
        )

        conexao.close()
        return True

    except Exception:
        return False


@app.get("/health")
def health():
    banco_ok = verificar_banco()

    if banco_ok:
        return jsonify({
            "status": "ok",
            "database": "connected"
        }), 200

    return jsonify({
        "status": "ok",
        "database": "unavailable"
    }), 200


@app.get("/")
def home():
    return jsonify({
        "message": "API funcionando!"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)