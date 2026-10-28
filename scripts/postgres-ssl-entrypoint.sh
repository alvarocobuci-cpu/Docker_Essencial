#!/bin/sh
set -eu

TLS_SOURCE="/tls-source"
TLS_DIR="/var/lib/postgresql/tls"

if [ ! -f "$TLS_SOURCE/server.crt" ] || [ ! -f "$TLS_SOURCE/server.key" ]; then
    echo "ERRO: certificado ou chave TLS nao encontrado."
    exit 1
fi

mkdir -p "$TLS_DIR"

cp "$TLS_SOURCE/server.crt" "$TLS_DIR/server.crt"
cp "$TLS_SOURCE/server.key" "$TLS_DIR/server.key"

chown postgres:postgres "$TLS_DIR"
chown postgres:postgres "$TLS_DIR/server.crt" "$TLS_DIR/server.key"
chmod 755 "$TLS_DIR"
chmod 644 "$TLS_DIR/server.crt"
chmod 600 "$TLS_DIR/server.key"

exec /usr/local/bin/docker-entrypoint.sh "$@"