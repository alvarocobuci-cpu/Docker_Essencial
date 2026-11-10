# SynapseShop — Docker Essencial

[![CI](https://github.com/alvarocobuci-cpu/Docker_Essencial/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/alvarocobuci-cpu/Docker_Essencial/actions/workflows/ci.yml)

SynapseShop é um sistema de vendas e estoque desenvolvido durante o curso de Programação em Python do Senac. O projeto começou como uma aplicação Flask com Docker e PostgreSQL e evoluiu para uma arquitetura com API Django REST Framework, microsserviço de inventário em FastAPI, mensageria com Apache Kafka, cache com Redis, assistência por IA, dashboards em Streamlit, testes automatizados e pipeline de CI/CD.

O objetivo é simular um backend real de vendas, aplicando na prática conceitos de APIs REST, persistência, transações, idempotência, autenticação JWT, controle de acesso, mensageria assíncrona, observabilidade, segurança, engenharia de prompts e integração contínua.

---

## Sumário

- [Visão geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Stack tecnológica](#stack-tecnológica)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como executar](#como-executar)
- [Serviços e portas](#serviços-e-portas)
- [Endpoints](#endpoints)
- [Modelo de dados](#modelo-de-dados)
- [Configuração e variáveis de ambiente](#configuração-e-variáveis-de-ambiente)
- [Testes](#testes)
- [CI/CD](#cicd)
- [Segurança e privacidade](#segurança-e-privacidade)
- [Limitações conhecidas](#limitações-conhecidas)
- [Histórico do projeto](#histórico-do-projeto)
- [Documentação relacionada](#documentação-relacionada)

---

## Visão geral

O SynapseShop cobre o ciclo básico de um pedido:

1. Um cliente autenticado cria um pedido informando item e quantidade, com uma chave de idempotência.
2. A API publica o evento `PedidoCriado` no Kafka e responde imediatamente com HTTP 202.
3. Um worker consome o evento e persiste o pedido no PostgreSQL.
4. O worker solicita o pagamento, que é processado por outro consumidor e registrado no banco.
5. Um terceiro consumidor registra a notificação do pedido e publica o evento final.

Além do fluxo de pedidos, o projeto oferece:

- catálogo de categorias e itens com CRUD protegido;
- microsserviço de estoque com cache-aside;
- dashboard de vendas e dashboard de desempenho da API;
- endpoints de IA para resumir logs, consultar o banco em linguagem natural e responder perguntas sobre a documentação (RAG);
- testes unitários e de integração, lint e validação do Docker Compose no GitHub Actions.

---

## Arquitetura

### Visão dos componentes

```text
Cliente / Postman / Swagger
        │ HTTP + JWT
        ▼
┌──────────────────────────────┐        ┌──────────────────┐
│ API Django + DRF  (:8000)    │───────▶│ PostgreSQL 16    │
│ catálogo, pedidos, IA, docs  │        │ dados principais │
└───────┬──────────────┬───────┘        └──────────────────┘
        │              │
        │              └───────────────▶ Provedor LLM / Embeddings
        │                                  (OpenAI-compatible)
        ├──────────────────────────────▶ Redis 7 (métricas e cache)
        │
        └──────────────────────────────▶ Kafka (eventos de pedidos)

┌──────────────────────────────┐        PostgreSQL + Redis
│ Inventory FastAPI  (:8001)   │───────▶ cache-aside de estoque
└──────────────────────────────┘

┌──────────────────────────────┐        API Django + PostgreSQL
│ Dashboard de Vendas (:8501)  │───────▶ pedidos, faturamento e Consulta IA
└──────────────────────────────┘

┌──────────────────────────────┐
│ Performance Dashboard (:8502)│───────▶ Redis (métricas HTTP e cache)
└──────────────────────────────┘
```

### Fluxo assíncrono de pedidos

```text
POST /api/v1/pedidos/
        │ evento PedidoCriado
        ▼
pedidos.criado (3 partições)
        │ grupo pedidos-worker-v1
        ▼
worker → PostgreSQL (Pedido)
        │ evento PagamentoSolicitado
        ▼
pagamentos.solicitados
        │ grupo pagamentos-worker-v1
        ▼
payment-worker → PostgreSQL (Pagamento)
        │ evento PagamentoProcessado
        ▼
pagamentos.processados
        │ grupo notificacoes-worker-v1
        ▼
notification-worker → PostgreSQL (Notificacao)
        │ evento NotificacaoEnviada
        ▼
notificacoes.enviadas
```

Cada etapa possui retentativas com backoff e tópico de DLQ. A entrega do Kafka é pelo menos uma vez, portanto a persistência é idempotente para tolerar reprocessamentos.

---

## Funcionalidades

### Catálogo e autenticação

- CRUD de categorias e itens via Django REST Framework.
- Autenticação JWT com `POST /api/token/` e renovação em `POST /api/token/refresh/`.
- Rotas de catálogo restritas a usuários autenticados pertencentes ao grupo `admin`.
- Paginação de 10 registros por página.
- Filtro por categoria, busca por nome/descrição e ordenação por `id`, `name`, `price` e `quantity`.
- Throttling de 10 requisições por minuto para anônimos e 30 por minuto para usuários autenticados.

### Pedidos assíncronos

- `POST /api/v1/pedidos/` com `Idempotency-Key` obrigatório.
- Validação de item e quantidade; cálculo de preço unitário e valor total no servidor.
- Publicação de `PedidoCriado` no Kafka com resposta HTTP 202.
- Chave de idempotência armazenada no Redis com TTL padrão de 24 horas.
- Repetição da mesma chave retorna `202` com `duplicate=true`; conteúdo diferente retorna `409`.
- Falha de publicação ou indisponibilidade de dependências retorna `503`.
- Worker valida o contrato do evento, persiste o pedido e trata reentregas.

### Pagamento e notificação

- `payment-worker` consome `pagamentos.solicitados`, valida pedido e valor, registra o pagamento simulado e publica `PagamentoProcessado`.
- O pagamento é simulado e, na implementação atual, aprovado automaticamente.
- `notification-worker` consome `pagamentos.processados`, registra uma notificação interna e publica `NotificacaoEnviada`.
- `Pagamento` e `Notificacao` têm relacionamento um-para-um com `Pedido`, evitando duplicidade por pedido.
- Falhas após três tentativas são encaminhadas ao tópico de DLQ correspondente.

### Inventário com cache-aside

- Microsserviço FastAPI com CRUD de itens de estoque.
- Cache Redis para lista e detalhe, com invalidação nas operações de escrita.
- TTL de 60 segundos para a lista (`inventory:list`) e 300 segundos para o detalhe (`inventory:{id}`).
- Endpoint `GET /cache/metrics` com lookups, hits, misses e hit rate por endpoint.
- Tabela `inventory_items` criada por migrações Alembic.

### Assistência por IA

- `POST /api/v1/assist`: resume ou explica logs técnicos com modos `summarize` e `explain`.
- Redação de padrões sensíveis antes do envio e na resposta do modelo.
- Timeout por chamada, até três tentativas com backoff exponencial e jitter, circuit breaker (`closed`, `open`, `half-open`) e limite de entrada.
- Telemetria de latência, tokens e custo estimado.
- `POST /api/v1/ask_sql`: converte perguntas em português para SQL somente leitura, valida a instrução e executa em transação read-only com `statement_timeout` e limite de linhas.
- `POST /api/v1/ask_docs`: RAG sobre `README.md` e `docs/openapi.yaml`, com recuperação por similaridade de cosseno, citações e resposta fixa quando não há evidência suficiente.

### Observabilidade e dashboards

- Middleware `APIMetricsMiddleware` registra requisições sob `/api/v1/` no Redis.
- Dashboard de desempenho com KPIs de total de requisições, latência média, p95 e taxa de erro.
- Gráficos de latência e throughput por minuto, distribuição de status HTTP, cache do inventário e tabela detalhada.
- Filtros por período, endpoints e grupos de status, com cache de 10 a 30 segundos.
- Dashboard de vendas com pedidos, faturamento, ticket médio, produtos mais vendidos, exportação CSV e página **Consulta IA**.

---

## Stack tecnológica

| Categoria | Tecnologias |
| --- | --- |
| Linguagem | Python 3.12 |
| API principal | Django 5.2.6, Django REST Framework 3.16.1 |
| Autenticação | djangorestframework-simplejwt 5.5.1 |
| Filtros | django-filter 26.1 |
| Microsserviço | FastAPI 0.117.1, Uvicorn 0.36.0, Pydantic |
| Persistência | PostgreSQL 16, SQLAlchemy 2.0.43, Alembic 1.16.5, psycopg 3.2.10 |
| Mensageria | Apache Kafka 4.2.2 (KRaft), kafka-python 3.0.11 |
| Cache | Redis 7, redis-py 5.2.1 |
| IA | HTTPX 0.28.1, provedores OpenAI-compatible para chat e embeddings |
| SQL | sqlparse 0.5.3 |
| Dashboards | Streamlit 1.66.1, pandas, Plotly |
| Testes | pytest 9.1.1, pytest-cov 7.1.0, HTTPX, freezegun 1.5.1 |
| Qualidade | Ruff 0.17.4 |
| Containers | Docker, Docker Compose, BuildKit |
| CI/CD | GitHub Actions, cache pip e GHA, DockerHub |
| Documentação | OpenAPI 3.0.3, Swagger UI, ReDoc, Redocly CLI, Postman |

---

## Estrutura do projeto

```text
Docker_Essencial/
├── app/
│   ├── aula4api/
│   │   ├── migrations/
│   │   ├── management/commands/ingest_docs.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── ask_sql.py
│   │   ├── event_contracts.py
│   │   ├── idempotency.py
│   │   ├── kafka_producer.py
│   │   ├── llm_service.py
│   │   ├── models.py
│   │   ├── notification_worker.py
│   │   ├── payment_worker.py
│   │   ├── permissions.py
│   │   ├── rag.py
│   │   ├── rag_embeddings.py
│   │   ├── rag_index.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── worker.py
│   ├── config/
│   │   ├── metrics.py
│   │   ├── metrics_middleware.py
│   │   ├── settings.py
│   │   └── urls.py
│   ├── dashboard/
│   │   ├── pages/2_Consulta_IA.py
│   │   ├── ask_sql_client.py
│   │   ├── db.py
│   │   └── streamlit_app.py
│   ├── inventory/
│   │   ├── cache.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── schemas.py
│   │   └── services.py
│   ├── performance_dashboard/
│   │   ├── metrics_data.py
│   │   └── streamlit_app.py
│   ├── flask_app_aula3.py
│   └── manage.py
├── docs/
│   ├── integrator-checklist.md
│   ├── issues-aula12.md
│   └── openapi.yaml
├── migrations/
│   └── versions/
├── postman/
│   ├── environments/SynapseShop_Local.postman_environment.json
│   └── SynapseShop_Aula13.postman_collection.json
├── scripts/
│   ├── kafka-init.sh
│   └── postgres-ssl-entrypoint.sh
├── tests/
│   ├── conftest.py
│   ├── integration/
│   └── unit/
├── .github/workflows/ci.yml
├── .env.example
├── .coveragerc
├── .ruff.toml
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.dashboard
├── Dockerfile.performance-dashboard
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── requirements-dashboard.txt
├── requirements-performance-dashboard.txt
├── redocly.yaml
├── CHANGELOG.md
├── PROMPTS.md
└── README.md
```

---

## Como executar

### Pré-requisitos

- Docker Desktop com Docker Compose v2.
- Git.
- OpenSSL para gerar os certificados TLS locais do PostgreSQL.
- Opcional: Node.js/npm para validar o OpenAPI com Redocly.
- Opcional: Python 3.12 para executar ferramentas fora dos containers.

### 1. Clonar o repositório

```powershell
git clone https://github.com/alvarocobuci-cpu/Docker_Essencial.git
cd Docker_Essencial
```

### 2. Criar o arquivo `.env`

```powershell
Copy-Item .env.example .env
```

Preencha apenas o necessário para o seu ambiente. As chaves de IA podem ficar vazias para a maioria dos testes; os endpoints de IA real exigem `LLM_API_KEY`, `LLM_API_URL`, `LLM_MODEL` e, para RAG, as variáveis `EMBEDDING_*`.

Nunca versione o `.env` nem chaves reais. O `.gitignore` já ignora esse arquivo.

### 3. Gerar os certificados TLS do PostgreSQL

O serviço `db` usa SSL obrigatório (`DB_SSLMODE=require`) e espera os arquivos em `certs/`.

```powershell
New-Item -ItemType Directory -Force certs | Out-Null
openssl req -x509 -newkey rsa:2048 -nodes `
  -keyout certs/server.key `
  -out certs/server.crt `
  -days 365 `
  -subj "/CN=localhost"
```

Se o OpenSSL não estiver disponível no Windows, execute o comando em um ambiente Linux/WSL ou via container com OpenSSL. Os certificados são locais e não devem ser versionados.

### 4. Subir a stack

```powershell
docker compose up -d --build
```

O Compose sobe PostgreSQL, Redis, Kafka, inicializa os tópicos, e inicia a API, os workers, o inventário e os dashboards. Acompanhe o estado com:

```powershell
docker compose ps
```

### 5. Executar as migrações

Django:

```powershell
docker compose exec api python app/manage.py migrate
```

Inventário (Alembic):

```powershell
docker compose exec -w /workspace inventory alembic upgrade head
```

### 6. Criar usuário administrador e grupo `admin`

```powershell
docker compose exec api python app/manage.py createsuperuser
docker compose exec api python app/manage.py shell -c "from django.contrib.auth.models import Group; Group.objects.get_or_create(name='admin')"
```

Depois, associe o usuário ao grupo `admin` pelo Django Admin (`http://localhost:8000/admin/`) ou por shell. As rotas de categorias e itens exigem esse grupo.

### 7. Indexar a documentação para o RAG

```powershell
docker compose exec api python app/manage.py ingest_docs
```

O comando indexa `README.md` e `docs/openapi.yaml` por padrão. Use `--force` após trocar o modelo de embeddings ou os parâmetros de chunking. O índice fica no volume `rag_index_data`.

### 8. Acessar os serviços

| Serviço | URL |
| --- | --- |
| API Django | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs/ |
| ReDoc | http://localhost:8000/redoc/ |
| Contrato OpenAPI | http://localhost:8000/openapi.yaml |
| Django Admin | http://localhost:8000/admin/ |
| Inventário FastAPI | http://localhost:8001 |
| Swagger do inventário | http://localhost:8001/docs |
| Dashboard de vendas | http://localhost:8501 |
| Dashboard de desempenho | http://localhost:8502 |

Para gerar dados no dashboard de desempenho, faça requisições autenticadas a `/api/v1/` usando o Postman ou o Swagger. O middleware registra apenas caminhos sob `/api/v1/`.

---

## Serviços e portas

| Serviço | Imagem/Build | Porta | Função |
| --- | --- | --- | --- |
| `api` | `Dockerfile` | 8000 | API Django + DRF |
| `inventory` | `Dockerfile` | 8001 | Microsserviço FastAPI de estoque |
| `dashboard` | `Dockerfile.dashboard` | 8501 | Dashboard de vendas + Consulta IA |
| `performance-dashboard` | `Dockerfile.performance-dashboard` | 8502 | Painel de desempenho da API |
| `worker` | `Dockerfile` | — | Consumidor de pedidos |
| `payment-worker` | `Dockerfile` | — | Consumidor de pagamentos |
| `notification-worker` | `Dockerfile` | — | Consumidor de notificações |
| `db` | `postgres:16-alpine` | interna 5432 | PostgreSQL com TLS |
| `redis` | `redis:7-alpine` | interna 6379 | Cache e métricas |
| `kafka` | `apache/kafka:4.2.2` | 9092 / interna 19092 | Broker KRaft |
| `kafka-init` | `apache/kafka:4.2.2` | — | Criação dos tópicos |

---

## Endpoints

### Autenticação

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| POST | `/api/token/` | Pública | Obtém access e refresh tokens |
| POST | `/api/token/refresh/` | Pública | Renova o access token |

### Catálogo

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| GET/POST | `/api/v1/categories/` | JWT + grupo `admin` | Lista/cria categorias |
| GET/PUT/PATCH/DELETE | `/api/v1/categories/{id}/` | JWT + grupo `admin` | Detalhe e alteração |
| GET/POST | `/api/v1/items/` | JWT + grupo `admin` | Lista/cria itens |
| GET/PUT/PATCH/DELETE | `/api/v1/items/{id}/` | JWT + grupo `admin` | Detalhe e alteração |

Parâmetros de listagem de itens: `page`, `category`, `search` e `ordering` (`id`, `name`, `price`, `quantity`; prefixo `-` para ordem decrescente).

### Pedidos

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| POST | `/api/v1/pedidos/` | JWT | Cria pedido e publica evento no Kafka |

Cabeçalhos obrigatórios: `Authorization: Bearer <token>` e `Idempotency-Key: <chave-única>`.

Exemplo:

```json
{
  "item_id": 1,
  "quantidade": 2
}
```

### IA e documentação

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| POST | `/api/v1/assist` | JWT | Resume ou explica logs |
| POST | `/api/v1/ask_sql` | JWT | Converte pergunta em SQL somente leitura |
| POST | `/api/v1/ask_docs` | JWT | Responde perguntas sobre a documentação indexada |
| GET | `/openapi.yaml` | Pública | Contrato OpenAPI combinado |
| GET | `/docs/` | Pública | Swagger UI |
| GET | `/redoc/` | Pública | ReDoc |

Exemplo de `/api/v1/assist`:

```json
{
  "mode": "summarize",
  "logs": [
    "Aplicação iniciada",
    "Erro de conexão com o banco"
  ],
  "temperature": 0.2,
  "max_tokens": 256
}
```

`mode` aceita `summarize` ou `explain`; `logs` aceita texto ou lista de textos; `temperature` vai de `0.0` a `1.0`; `max_tokens` vai de 1 a 256.

Exemplo de `/api/v1/ask_sql`:

```json
{
  "question": "Quais os 5 últimos usuários cadastrados?"
}
```

A resposta inclui `question`, `sql`, `columns`, `rows`, `row_count`, `truncated` e `meta` com latência, tokens e custo estimado. O SQL é validado antes da execução: apenas um `SELECT`/`WITH`, sem comentários, sem comandos de escrita, sem `SELECT *`, sem identificadores proibidos e apenas com as tabelas permitidas.

Exemplo de `/api/v1/ask_docs`:

```json
{
  "question": "Como subir a API e o painel com Docker Compose?",
  "top_k": 3,
  "min_score": 0.25
}
```

A resposta inclui `answer`, `sources` (caminho, título, faixa de caracteres e score) e `meta`. Se o índice estiver vazio, retorna HTTP 503 com instrução para executar `ingest_docs`. Se nenhum trecho atingir `min_score`, retorna HTTP 200 com resposta de informação insuficiente e `sources: []`, sem chamar o LLM.

### Inventário (FastAPI)

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| GET | `/` | Pública | Identificação do serviço |
| GET | `/health` | Pública | Healthcheck |
| GET | `/cache/metrics` | Pública | Métricas de cache por endpoint |
| GET | `/inventory` | Pública | Lista itens de estoque |
| POST | `/inventory` | Pública | Cria item de estoque |
| GET | `/inventory/{item_id}` | Pública | Detalha item e disponibilidade |
| PUT | `/inventory/{item_id}/quantity?quantity=12` | Pública | Atualiza quantidade |
| DELETE | `/inventory/{item_id}` | Pública | Remove item |

O microsserviço de inventário ainda não possui autenticação JWT, paginação, filtros ou ordenação na listagem.

### Códigos de erro comuns

| Código | Significado |
| --- | --- |
| 400 | Payload ou regra de negócio inválida |
| 401 | Autenticação ausente ou inválida |
| 403 | Usuário sem permissão |
| 404 | Recurso não encontrado |
| 409 | Conflito de idempotência |
| 422 | Falha de execução não recuperável (Text-to-SQL/validação) |
| 429 | Limite de requisições ou do provedor de IA |
| 502 | Resposta inválida do provedor de IA |
| 503 | Dependência indisponível, configuração ausente ou índice RAG vazio |

A aplicação não padroniza integralmente as respostas como RFC 7807 (`application/problem+json`).

---

## Modelo de dados

### Django (PostgreSQL)

```text
Category 1 ──── N Item
                   │
                   │ 1
                   ▼
                Pedido N ──── 1 Item
                   │
        ┌──────────┴──────────┐
        │ 1                   │ 1
        ▼                     ▼
    Pagamento             Notificacao
```

- **Category**: `id`, `name` (único).
- **Item**: `id`, `name`, `description`, `price`, `quantity`, `category`.
- **Pedido**: UUID, item, quantidade, preço unitário, valor total, `idempotency_key` único, status (`CRIADO`, `PAGO`, `NOTIFICADO`) e data de criação.
- **Pagamento**: UUID, pedido (um-para-um), valor, status (`APROVADO`, `RECUSADO`), referência simulada única e data.
- **Notificacao**: UUID, pedido (um-para-um), canal, status (`ENVIADA`), mensagem e data.

### Inventário (SQLAlchemy)

- **InventoryItem** (`inventory_items`): `id`, `name`, `quantity`, `minimum_quantity`, com restrições de quantidade não negativa e índice em `name`.

### Índice RAG (SQLite)

- Documentos e chunks com offsets de caracteres, embeddings e metadados.
- Localmente em `app/data/rag_index.sqlite3`; no Compose em `/data/rag_index.sqlite3`, persistido no volume `rag_index_data`.

---

## Configuração e variáveis de ambiente

O arquivo `.env.example` contém os valores de exemplo. Copie para `.env` e ajuste conforme o ambiente. Nenhum valor real de secret deve ser versionado.

### Aplicação e banco

| Variável | Padrão | Uso |
| --- | --- | --- |
| `SECRET_KEY` | fallback de desenvolvimento | Chave do Django |
| `DB_HOST` | `db` | Host do PostgreSQL |
| `DB_PORT` | `5432` | Porta do PostgreSQL |
| `DB_NAME` | `appdb` | Nome do banco |
| `DB_USER` | `appuser` | Usuário do banco |
| `DB_PASSWORD` | `apppassword` | Senha do banco (defina a sua) |
| `DB_SSLMODE` | `require` | Modo SSL obrigatório |
| `DB_CONNECT_TIMEOUT_SECONDS` | `5` | Timeout de conexão |
| `DB_POOL_SIZE` | `5` | Pool SQLAlchemy |
| `DB_MAX_OVERFLOW` | `10` | Overflow do pool |
| `DB_POOL_TIMEOUT_SECONDS` | `10` | Timeout do pool |
| `DB_POOL_RECYCLE_SECONDS` | `1800` | Reciclagem de conexões |
| `DB_CONN_MAX_AGE` | `60` | Idade máxima de conexão no Django |
| `REDIS_URL` | `redis://redis:6379/0` | Cache e métricas |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:19092` | Broker Kafka |
| `PEDIDO_IDEMPOTENCY_TTL_SECONDS` | `86400` | TTL da chave de idempotência |
| `PEDIDOS_MAX_ATTEMPTS` | `3` | Tentativas por mensagem |
| `PEDIDOS_RETRY_BASE_SECONDS` | `1` | Base do backoff |

### Métricas e observabilidade

| Variável | Padrão | Uso |
| --- | --- | --- |
| `API_METRICS_REDIS_KEY` | `synapseshop:observability:requests` | Eventos HTTP |
| `API_METRICS_RETENTION_SECONDS` | `604800` | Retenção (7 dias) |
| `API_CACHE_METRICS_REDIS_KEY` | `synapseshop:observability:cache` | Métricas de cache |
| `API_MESSAGING_METRICS_REDIS_KEY` | `synapseshop:observability:messaging` | Métricas de mensageria |

### LLM e assistência

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LLM_API_URL` | `https://api.openai.com/v1/chat/completions` | Endpoint do provedor |
| `LLM_API_KEY` | vazio | Chave do provedor |
| `LLM_MODEL` | placeholder | Modelo de chat |
| `LLM_TIMEOUT_SECONDS` | `5` | Timeout por tentativa |
| `LLM_MAX_RETRIES` | `3` | Tentativas HTTP |
| `LLM_RETRY_BASE_SECONDS` | `0.2` | Base do backoff |
| `LLM_CIRCUIT_FAILURE_THRESHOLD` | `3` | Falhas para abrir o circuito |
| `LLM_CIRCUIT_RESET_SECONDS` | `30` | Tempo para half-open |
| `LLM_COST_INPUT_PER_1K_TOKENS` | `0` | Custo de entrada por 1k tokens |
| `LLM_COST_OUTPUT_PER_1K_TOKENS` | `0` | Custo de saída por 1k tokens |
| `LLM_MAX_INPUT_CHARS` | `12000` | Limite de entrada |

### Text-to-SQL

| Variável | Padrão | Uso |
| --- | --- | --- |
| `ASK_SQL_MAX_ROWS` | `200` | Limite de linhas retornadas |
| `ASK_SQL_STATEMENT_TIMEOUT_MS` | `5000` | Timeout da consulta |
| `API_BASE_URL` | `http://api:8000` | URL usada pelo dashboard |
| `ASK_SQL_API_TOKEN` | vazio | Token JWT opcional para o painel |

### Embeddings e RAG

| Variável | Padrão | Uso |
| --- | --- | --- |
| `EMBEDDING_API_URL` | `https://api.openai.com/v1/embeddings` | Endpoint de embeddings |
| `EMBEDDING_API_KEY` | vazio | Chave; usa `LLM_API_KEY` se vazia |
| `EMBEDDING_MODEL` | placeholder | Modelo de embeddings |
| `EMBEDDING_TIMEOUT_SECONDS` | `10` | Timeout por tentativa |
| `EMBEDDING_MAX_RETRIES` | `3` | Tentativas HTTP |
| `EMBEDDING_RETRY_BASE_SECONDS` | `0.2` | Base do backoff |
| `EMBEDDING_BATCH_SIZE` | `32` | Textos por requisição |
| `RAG_INDEX_PATH` | `/data/rag_index.sqlite3` no Compose | Caminho do índice |
| `RAG_CHUNK_TOKENS` | `400` | Tamanho aproximado do chunk |
| `RAG_CHUNK_OVERLAP_TOKENS` | `80` | Sobreposição entre chunks |

---

## Testes

A suíte usa `pytest`, `pytest-cov`, `HTTPX` e `freezegun`. Os testes unitários usam SQLite em memória, fakes e mocks para isolar dependências externas. Os testes de integração usam `TestClient` e também validam a execução somente leitura do Text-to-SQL contra PostgreSQL real no CI.

### Estrutura

- `tests/conftest.py`: fixtures compartilhadas, banco efêmero, cliente HTTP, FakeRedis e relógio fixo.
- `tests/unit/`: schemas, serviços, cache, banco, idempotência, contratos de eventos, métricas, LLM, RAG, Text-to-SQL, clientes e dashboard.
- `tests/integration/`: testes HTTP de inventário, ingestão real do RAG e execução somente leitura contra PostgreSQL.
- `pytest.ini`: descoberta dos testes e marcadores `unit` e `integration`.
- `.coveragerc`: escopo de cobertura e limite mínimo de 85% para os módulos medidos.

### Executar com Docker (PowerShell)

Reconstruir a imagem após mudanças nas dependências:

```powershell
docker compose build api
```

Testes unitários:

```powershell
$appPath = (Resolve-Path ".\app").Path
$testsPath = (Resolve-Path ".\tests").Path
$pytestConfigPath = (Resolve-Path ".\pytest.ini").Path
$coveragePath = (Resolve-Path ".\.coveragerc").Path

docker compose run --rm `
    -v "${appPath}:/app/app" `
    -v "${testsPath}:/app/tests" `
    -v "${pytestConfigPath}:/app/pytest.ini:ro" `
    -v "${coveragePath}:/app/.coveragerc:ro" `
    api pytest -v -m unit tests
```

Testes de integração:

```powershell
docker compose run --rm `
    -v "${appPath}:/app/app" `
    -v "${testsPath}:/app/tests" `
    -v "${pytestConfigPath}:/app/pytest.ini:ro" `
    -v "${coveragePath}:/app/.coveragerc:ro" `
    api pytest -v -m integration tests
```

Suíte completa com cobertura:

```powershell
docker compose run --rm `
    -v "${appPath}:/app/app" `
    -v "${testsPath}:/app/tests" `
    -v "${pytestConfigPath}:/app/pytest.ini:ro" `
    -v "${coveragePath}:/app/.coveragerc:ro" `
    api pytest -v `
        --cov=inventory `
        --cov=aula4api.idempotency `
        --cov=aula4api.event_contracts `
        --cov-config=/app/.coveragerc `
        --cov-report=term-missing tests
```

### Cobertura

A meta mínima é de 85% para os módulos medidos: `inventory`, `aula4api.idempotency` e `aula4api.event_contracts`. Esse percentual não representa a aplicação inteira; views Django, workers e outros módulos possuem testes próprios, mas não entram nesse recorte de cobertura.

---

## CI/CD

O workflow `.github/workflows/ci.yml` roda em `push` e `pull_request` para `main`/`master` e também pode ser executado manualmente (`workflow_dispatch`). O status aparece no badge no topo deste README.

### Jobs

1. **`test-and-lint`**
   - checkout com `actions/checkout@v4`;
   - Python 3.12 com `actions/setup-python@v5` e cache `pip`;
   - instalação de `requirements-dev.txt`;
   - `ruff check --no-cache .`;
   - PostgreSQL 16 efêmero com TLS na porta `55432`;
   - migrações Django;
   - suíte completa com `pytest`, relatório JUnit e cobertura XML;
   - upload de `reports/` como artifact.

2. **`compose-validation`**
   - geração de certificados TLS;
   - `docker compose config --quiet`;
   - build das imagens da API e do dashboard;
   - subida de `db`, `redis` e `kafka` com healthchecks;
   - inicialização dos tópicos Kafka;
   - migrações e validação do comando `ingest_docs --help`;
   - subida de `api` e `dashboard`;
   - verificação de HTTP, API → PostgreSQL, dashboard → PostgreSQL e dashboard → API;
   - coleta de logs em falha e `docker compose down -v --remove-orphans`.

3. **`publish`**
   - executa apenas em `push` para `main`/`master` ou `workflow_dispatch`;
   - usa `docker/login-action` e `docker/build-push-action@v6`;
   - publica `<DOCKERHUB_USERNAME>/synapseshop-api:latest` e `<DOCKERHUB_USERNAME>/synapseshop-api:<commit-sha>`;
   - usa cache GHA com escopo `api`.

### Secrets do GitHub

Configure em **Settings → Secrets and variables → Actions**:

| Nome | Uso |
| --- | --- |
| `SECRET_KEY` | Chave do Django. No CI há fallback apenas para testes. |
| `DB_PASSWORD` | Senha do PostgreSQL efêmero. No CI há fallback `apppassword`. |
| `DOCKERHUB_USERNAME` | Usuário ou organização do DockerHub. |
| `DOCKERHUB_TOKEN` | Token com permissão de push no repositório. |

`LLM_API_KEY` e `EMBEDDING_API_KEY` não são necessárias no CI; os testes usam provedores falsos/mocks.

### Execução local equivalente

```powershell
python -m pip install -r requirements-dev.txt
ruff check --no-cache .
docker build -t synapseshop-api:test .

docker compose config --quiet
docker compose build api dashboard
docker compose up -d --wait db redis kafka
docker compose run --rm kafka-init
docker compose run --rm api python app/manage.py migrate --noinput
docker compose up -d --wait --no-deps api dashboard
curl.exe -fsS http://localhost:8000/openapi.yaml
curl.exe -fsS http://localhost:8501/_stcore/health
docker compose down
```

Evite `docker compose down -v` localmente se quiser preservar dados. No CI o runner é efêmero, por isso o volume é removido.

---

## Segurança e privacidade

- **Autenticação**: JWT via SimpleJWT; rotas de catálogo exigem grupo `admin`.
- **Autorização**: `IsAuthenticated` nas rotas de pedidos e IA; `IsAdminRole` no catálogo.
- **Throttling**: 10 requisições/minuto para anônimos e 30 para autenticados.
- **Idempotência**: `Idempotency-Key` no Redis evita pedidos duplicados e conflitos retornam `409`.
- **Text-to-SQL**: schema curado, tabelas permitidas, colunas sensíveis bloqueadas, apenas `SELECT`/`WITH`, transação read-only, `statement_timeout` e limite de linhas.
- **Privacidade na IA**: redação de padrões de e-mails, CPFs, telefones, senhas, tokens e chaves antes do envio e na resposta. Logs são tratados como dados não confiáveis no prompt.
- **RAG**: a pergunta do usuário e os trechos recuperados são tratados como dados não confiáveis; o modelo é instruído a não seguir instruções embutidas no conteúdo.
- **Segredos**: `SECRET_KEY`, senhas, chaves de LLM/embeddings e tokens do DockerHub vêm de variáveis de ambiente; nada real deve ser versionado.
- **Banco**: PostgreSQL com TLS obrigatório (`sslmode=require`).
- **Containers**: executam com usuário não-root.

A redação é baseada em padrões e não garante detectar toda informação sensível. A telemetria registra metadados das chamadas, sem armazenar o conteúdo integral dos logs ou das respostas.

---

## Limitações conhecidas

- **Kafka**: ambiente local com um único broker em KRaft e fator de replicação 1; demonstra particionamento e consumo concorrente, mas não alta disponibilidade.
- **Entrega**: semântica pelo menos uma vez; reprocessamentos e publicações duplicadas podem ocorrer em falhas entre persistência e confirmação de offset. A persistência é idempotente para mitigar.
- **Dashboard de desempenho**: mede apenas a API Django sob `/api/v1/`; o inventário é monitorado apenas pelas estatísticas de cache.
- **Mensageria no painel**: a seção está pronta, mas a instrumentação de produtores/consumidores Kafka não é registrada no Redis nesta versão; a seção exibe estado vazio.
- **OpenAPI**: `limit`, `nextCursor`, filtro `status` e `sort=createdAt:desc` não são suportados pelas rotas atuais. `X-Trace-Id` está documentado como convenção futura, mas não é processado.
- **Erros**: não há padronização integral como RFC 7807 `application/problem+json`.
- **Inventário**: sem autenticação JWT, paginação, filtros ou ordenação.
- **RAG**: indexação explícita; mudanças em `README.md` ou `docs/openapi.yaml` exigem novo `ingest_docs`. O índice SQLite é local do container; múltiplas réplicas exigiriam armazenamento compartilhado. O endpoint não valida semanticamente cada citação retornada pelo modelo.
- **IA**: a validação automatizada usa provedores falsos e não mede a qualidade real das respostas. A qualidade depende do provedor e do modelo configurados.
- **Circuit breaker**: o estado é em memória por processo; múltiplas instâncias não compartilham o estado.
- **Cobertura**: a meta de 85% vale apenas para os módulos medidos, não para a aplicação inteira.
- **CI**: o PostgreSQL do CI é efêmero e não persiste dados; o cache GHA não é reproduzido localmente.

---

## Histórico do projeto

| Aula | Tema |
| --- | --- |
| 3 | Aplicação Flask com Docker e PostgreSQL |
| 5 | Microsserviço de inventário com FastAPI |
| 6 | Persistência com SQLAlchemy e migrações Alembic |
| 7 | Autenticação JWT e segurança |
| 8 | Cache-aside com Redis |
| 11 | Mensageria com Kafka, pagamento e notificação |
| 12 | Testes automatizados e cobertura |
| 13 | OpenAPI, Swagger, ReDoc e Postman |
| 14 | Assistente de IA e `llm_service` |
| 20 | Dashboard de desempenho da API |
| 21 | Consulta em linguagem natural (Text-to-SQL) |
| 22 | Pipeline de CI com GitHub Actions |
| 23 | Cache, Docker Compose e publicação no DockerHub |
| 24 | Assistente RAG sobre a documentação |

O detalhamento de cada entrega está em [`CHANGELOG.md`](CHANGELOG.md). O registro do trabalho com apoio de IA está em [`PROMPTS.md`](PROMPTS.md).

---

## Documentação relacionada

- [`docs/openapi.yaml`](docs/openapi.yaml): contrato combinado das APIs Django e inventário.
- [`docs/integrator-checklist.md`](docs/integrator-checklist.md): convenções, autenticação, limites e diferenças para integradores externos.
- [`postman/SynapseShop_Aula13.postman_collection.json`](postman/SynapseShop_Aula13.postman_collection.json): coleção com os fluxos principais.
- [`postman/environments/SynapseShop_Local.postman_environment.json`](postman/environments/SynapseShop_Local.postman_environment.json): ambiente local.
- [`CHANGELOG.md`](CHANGELOG.md): histórico de alterações.
- [`PROMPTS.md`](PROMPTS.md): engenharia de prompts e registro de uso de IA.
- [`redocly.yaml`](redocly.yaml): configuração do lint do contrato OpenAPI.

### Validar o contrato OpenAPI

```powershell
npx --yes @redocly/cli lint ./docs/openapi.yaml
```

### Importar a coleção Postman

Importe a coleção e o ambiente, selecione `SynapseShop - Local` e substitua as credenciais de exemplo pelas credenciais locais. Os tokens são armazenados no ambiente após o login.

---

Projeto desenvolvido durante o curso de Programação em Python do Senac, mantido no mesmo repositório para acompanhar a evolução das atividades.
