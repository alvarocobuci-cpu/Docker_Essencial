# Docker_Essencial — SynapseShop

[![CI](https://github.com/alvarocobuci-cpu/Docker_Essencial/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/alvarocobuci-cpu/Docker_Essencial/actions/workflows/ci.yml)

Projeto desenvolvido durante as aulas do curso de Programação em Python do Senac.

O projeto começou como uma aplicação simples utilizando Flask, Docker e PostgreSQL e foi evoluindo ao longo das aulas. Depois foram adicionadas uma API em Django REST Framework, um microsserviço de estoque com FastAPI, persistência com PostgreSQL, SQLAlchemy, migrações com Alembic e autenticação JWT.

A ideia principal é simular uma estrutura de sistema de vendas e estoque, permitindo praticar conceitos de desenvolvimento backend, APIs, bancos de dados, containers, segurança e organização de código.

---

## 1. Objetivo do projeto

O objetivo é desenvolver, de forma gradual, uma aplicação backend utilizando as tecnologias estudadas durante o curso.

Durante as aulas foram trabalhados conceitos como:

- Python

- Flask

- Django

- Django REST Framework

- FastAPI

- Docker e Docker Compose

- PostgreSQL

- SQLAlchemy

- Alembic

- APIs REST

- CRUD

- validação de dados

- transações e rollback

- migrações de banco

- Repository e Service

- autenticação JWT

- controle de acesso por papéis

- throttling

- paginação, filtros, busca e ordenação

- testes com Postman

- Git e GitHub

- integração com modelos de linguagem (LLM)

- engenharia de prompts para análise de logs

- redação de dados pessoais e segredos antes do envio

- timeout, retentativas, backoff exponencial e jitter

- circuit breaker para falhas do provedor

- telemetria de chamadas, latência, tokens e custo estimado

O projeto foi mantido no mesmo repositório para acompanhar a evolução das atividades.

---

## 2. Tecnologias utilizadas

- **Python 3.12**

- **Django 5.2.6**

- **Django REST Framework 3.16.1**

- **djangorestframework-simplejwt 5.5.1**

- **django-filter 26.1**

- **FastAPI 0.117.1**

- **Uvicorn 0.36.0**

- **SQLAlchemy 2.0.43**

- **Alembic 1.16.5**

- **PostgreSQL 16**

- **Docker**

- **Docker Compose**

- **Git e GitHub**

- **Postman**

- **Redis 7** — cache-aside

- **redis-py 5.2.1** — integração do Python com Redis

- **HTTPX** — chamadas HTTP ao provedor de IA

- **pytest e pytest-cov** — testes automatizados e cobertura

- **Streamlit** — dashboard de desempenho da API

- **Plotly** — gráficos interativos do dashboard

- **pandas** — tratamento dos eventos de métricas

---

## 3. Estrutura geral do projeto

Atualmente, o projeto possui uma estrutura semelhante a esta:

```text
Docker_Essencial/
├── app/
│   ├── aula4api/
│   │   ├── migrations/
│   │   ├── event_contracts.py
│   │   ├── idempotency.py
│   │   ├── llm_service.py
│   │   ├── models.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── config/
│   │   ├── metrics.py
│   │   ├── metrics_middleware.py
│   │   ├── settings.py
│   │   └── urls.py
│   ├── inventory/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── services.py
│   │   ├── schemas.py
│   │   └── main.py
│   ├── performance_dashboard/
│   │   ├── metrics_data.py
│   │   └── streamlit_app.py
│   ├── flask_app_aula3.py
│   └── manage.py
├── docs/
│   ├── openapi.yaml
│   └── integrator-checklist.md
├── migrations/
├── postman/
│   ├── SynapseShop_Aula13.postman_collection.json
│   └── environments/
│       └── SynapseShop_Local.postman_environment.json
├── tests/
│   ├── integration/
│   └── unit/
│       ├── test_llm_service.py
│       ├── test_assist_api.py
│       ├── test_metrics.py
│       └── test_performance_dashboard_data.py
├── .env.example
├── Dockerfile
├── Dockerfile.performance-dashboard
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── requirements-performance-dashboard.txt
├── pytest.ini
├── .coveragerc
├── PROMPTS.md
└── README.md
```

## Mensageria assíncrona

O projeto utiliza Apache Kafka para separar o recebimento dos pedidos do seu processamento em segundo plano. Quando a API recebe uma solicitação em `POST /api/v1/pedidos/`, ela publica o evento `PedidoCriado` no tópico `pedidos.criado`. Um worker independente consome esse evento e registra o pedido no PostgreSQL.

O worker valida os eventos, aplica controle de idempotência e realiza novas tentativas com espera progressiva (backoff). Quando uma mensagem falha após três tentativas, ela é encaminhada para o tópico `pedidos.criado.dlq`, destinado às mensagens que não puderam ser processadas.

A escolha do Kafka permite manter produtores e consumidores desacoplados, armazenar eventos em tópicos e acompanhar o processamento por meio de partições e offsets. O ambiente atual utiliza um único broker em modo KRaft, adequado para desenvolvimento local, mas sem alta disponibilidade.

## Configuração do Kafka

O serviço `kafka-init` executa o script `scripts/kafka-init.sh` depois que o broker fica saudável. O script configura os tópicos de forma repetível, sem recriar tópicos existentes nem reduzir suas partições.

- `pedidos.criado`: três partições e retenção de três dias.

- `pedidos.criado.dlq`: uma partição e retenção de 30 dias.

- Grupo de consumidores: `pedidos-worker-v1`.

As partições permitem distribuir o processamento entre consumidores do mesmo grupo. Os offsets registram a posição de leitura, enquanto o `LAG` indica quantas mensagens ainda faltam consumir. No teste local, duas instâncias do worker processaram mensagens das três partições e o atraso chegou a zero.

O ambiente de desenvolvimento utiliza um único broker e fator de replicação 1. Portanto, ele demonstra os conceitos de particionamento e consumo concorrente, mas não oferece alta disponibilidade.

## Aula 11 — Fluxo de pedido, pagamento e notificacao

O fluxo de pedidos foi ampliado com dois consumidores independentes. Depois de persistir o pedido no PostgreSQL, o worker publica `PagamentoSolicitado` no topico `pagamentos.solicitados`.

O `payment-worker` consome a solicitacao, valida o pedido e o valor, registra o pagamento simulado no PostgreSQL e publica `PagamentoProcessado` no topico `pagamentos.processados`. O pagamento desta atividade e simulado e, na implementacao atual, e aprovado automaticamente.

O `notification-worker` consome `PagamentoProcessado`, confere os dados persistidos, registra uma notificacao interna no PostgreSQL e publica `NotificacaoEnviada` no topico `notificacoes.enviadas`.

Os modelos `Pagamento` e `Notificacao` possuem relacionamento um-para-um com `Pedido`, ajudando a impedir registros duplicados para o mesmo pedido. O Redis e usado como cache auxiliar; o PostgreSQL permanece como fonte persistente dos dados.

Os consumidores possuem grupos separados:

- Pedidos: `pedidos-worker-v1`.

- Pagamentos: `pagamentos-worker-v1`.

- Notificacoes: `notificacoes-worker-v1`.

As falhas de processamento possuem retentativas com backoff e topicos de DLQ. Como a entrega e pelo menos uma vez, a persistencia idempotente e importante para lidar com reprocessamentos; publicacoes de eventos podem se repetir em caso de falhas entre a persistencia e a confirmacao do offset.

O teste local confirmou o caminho pedido criado, pagamento aprovado e notificacao registrada no PostgreSQL. O registro temporario de teste e suas chaves relacionadas do Redis foram removidos ao final.

## Aula 12 - Testes automatizados e cobertura

A suite utiliza pytest, pytest-cov, HTTPX e freezegun. Os testes rodam em container e usam SQLite em memoria para testar o microsservico de inventario sem alterar o PostgreSQL de desenvolvimento.

### Estrutura

- `tests/conftest.py`: fixtures compartilhadas, banco efemero, cliente HTTP, FakeRedis e relogio fixo.

- `tests/unit/`: schemas, servicos, cache, sessao do banco, idempotencia e contratos de eventos.

- `tests/integration/`: testes HTTP de criacao, consulta, atualizacao, exclusao e erros.

- `pytest.ini`: descoberta dos testes e marcadores unit e integration.

- `.coveragerc`: escopo de cobertura e limite minimo.

### Convencoes

Mocks e fakes isolam dependencias externas. O SQLite em memoria e recriado para cada teste. Os testes de integracao usam TestClient e conferem os status HTTP e os efeitos no banco. A fixture frozen_time fixa o horario para testes deterministas.

### Executar no Windows com PowerShell e Docker

Reconstruir a imagem apos mudancas nas dependencias:

```powershell

docker compose build api

```

Executar os testes unitarios:

```powershell

$appPath = (Resolve-Path ".\app").Path

$testsPath = (Resolve-Path ".\tests").Path

$pytestConfigPath = (Resolve-Path ".\pytest.ini").Path

$coveragePath = (Resolve-Path ".\\.coveragerc").Path

docker compose run --rm `

    -v "${appPath}:/app/app" `

    -v "${testsPath}:/app/tests" `

    -v "${pytestConfigPath}:/app/pytest.ini:ro" `

    -v "${coveragePath}:/app/.coveragerc:ro" `

    api pytest -v -m unit tests

```

Executar os testes de integracao:

```powershell

docker compose run --rm `

    -v "${appPath}:/app/app" `

    -v "${testsPath}:/app/tests" `

    -v "${pytestConfigPath}:/app/pytest.ini:ro" `

    -v "${coveragePath}:/app/.coveragerc:ro" `

    api pytest -v -m integration tests

```

Executar a suite completa com cobertura:

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

### Meta de cobertura

A meta minima e 85% para os modulos medidos: inventory, aula4api.idempotency e aula4api.event_contracts. A ultima execucao apresentou 52 testes aprovados e 100% de cobertura nesse escopo.

Esse resultado nao representa 100% da aplicacao inteira. As views Django, os workers e outros modulos ainda precisam de testes especificos. Scripts manuais de benchmark e experimentacao ficam fora do relatorio da API.

### Pendencias tecnicas

As melhorias da Aula 12 foram registradas como issues no GitHub. O arquivo `docs/issues-aula12.md` mantém o contexto e as propostas originais.

## Aula 13 - OpenAPI, Swagger e Postman

### Documentacao local

Com os servicos iniciados por Docker Compose:

- API Django: http://localhost:8000

- Contrato OpenAPI combinado: http://localhost:8000/openapi.yaml

- Swagger UI Django: http://localhost:8000/docs/

- ReDoc Django: http://localhost:8000/redoc/

- Swagger UI do inventario FastAPI: http://localhost:8001/docs

- ReDoc do inventario FastAPI: http://localhost:8001/redoc

- OpenAPI JSON do inventario: http://localhost:8001/openapi.json

### Arquivos da entrega

- `docs/openapi.yaml`: contrato combinado das APIs existentes.

- `redocly.yaml`: configuracao do lint do contrato.

- `docs/integrator-checklist.md`: instrucoes para integradores externos.

- `CHANGELOG.md`: historico de alteracoes.

- `postman/SynapseShop_Aula13.postman_collection.json`: colecao Postman.

- `postman/environments/SynapseShop_Local.postman_environment.json`: ambiente local.

- `PROMPTS.md`: registro do trabalho com apoio de IA.

### Validar a especificacao

```powershell

npx --yes @redocly/cli lint ./docs/openapi.yaml

```

### Importar a colecao Postman

Importe a colecao e o ambiente indicados acima, escolha `SynapseShop - Local` e substitua os valores de credenciais de exemplo pelas credenciais locais. Os tokens sao guardados no ambiente apos o login.

### Limites conhecidos do contrato

Os parametros limit, nextCursor, filtro status e sort=createdAt:desc ainda nao sao suportados pelas rotas atuais. Consulte docs/integrator-checklist.md para as convencoes existentes e as diferencas.

A API de inventario ainda nao possui paginacao, filtros, ordenacao ou autenticacao JWT.

O cabecalho `X-Trace-Id` esta documentado como convencao futura, mas ainda nao e processado pela aplicacao.

A resposta de erro atual nao e padronizada integralmente como RFC 7807 `application/problem+json`.

Essas diferencas estao descritas em `docs/integrator-checklist.md`.

---

## Aula 14 - Assistente de IA e llm_service

### Objetivo

Foi adicionada uma camada de assistência por IA para resumir logs técnicos ou explicar possíveis causas de falhas. O serviço fica em `app/aula4api/llm_service.py` e concentra a comunicação com o provedor, os prompts, as retentativas, o circuit breaker e a telemetria.

### Endpoint

- Método: `POST`
- Caminho: `/api/v1/assist`
- Acesso: exige autenticação conforme as configurações atuais do Django REST Framework.

Exemplo de requisição:

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

O campo `mode` aceita `summarize` ou `explain`. O campo `logs` aceita um texto ou uma lista de textos. A temperatura aceita valores de `0.0` a `1.0`; `max_tokens` aceita de 1 a 256 e usa 256 como padrão.

A resposta contém `answer` e `meta`, com tokens de entrada e saída, latência e custo estimado. Os valores variam de acordo com a resposta do provedor e as tarifas configuradas.

### Privacidade e prompts

Antes de enviar os logs, o serviço aplica regras de redação para padrões reconhecidos de dados sensíveis, como e-mails, CPFs, telefones, senhas, tokens e algumas chaves. A resposta do modelo também passa por redação. Os prompts orientam o modelo a tratar o conteúdo dos logs como dados não confiáveis e a não seguir instruções encontradas dentro deles.

A redação é baseada em padrões e não garante detectar toda informação sensível. Os logs devem continuar sendo tratados com cuidado. A telemetria registra metadados da chamada, sem registrar o conteúdo integral dos logs ou da resposta.

### Resiliência e limites

- Timeout por chamada limitado a 5 segundos.
- Até três tentativas para timeout e falhas de rede, HTTP 408, HTTP 429 e erros HTTP 5xx.
- Backoff exponencial com jitter entre as tentativas.
- Circuit breaker com estados `closed`, `open` e `half-open`.
- Limite de tamanho de entrada configurável por `LLM_MAX_INPUT_CHARS`.
- `LLM_API_KEY`, `LLM_API_URL` e `LLM_MODEL` são configurados por variáveis de ambiente. O arquivo `.env.example` contém exemplos, não uma chave real.

As tarifas `LLM_COST_INPUT_PER_1K_TOKENS` e `LLM_COST_OUTPUT_PER_1K_TOKENS` são usadas para estimar o custo. O padrão é zero; devem ser configuradas conforme o modelo utilizado para que a estimativa tenha utilidade. As métricas são agregadas em memória nesta versão e não possuem um endpoint público dedicado.

### Testes e validações

Os novos testes ficam em `tests/unit/test_llm_service.py` e `tests/unit/test_assist_api.py`. Eles simulam o provedor para validar timeout, HTTP 429, HTTP 5xx, indisponibilidade, resposta inválida, entrada inválida, circuit breaker, redação de dados sensíveis e códigos HTTP do endpoint. Não foi necessária uma chave real nem uma chamada real ao provedor.

Na validação da Aula 14, a suíte completa apresentou **77 testes aprovados** e um aviso de depreciação do Starlette/AnyIO. O aviso não impediu a execução dos testes. Essa contagem é o resultado dos testes executados nesta etapa; não representa uma afirmação de cobertura total do código.

### Melhorias futuras

- Validar a integração real em ambiente controlado com credenciais protegidas.
- Ampliar os testes das regras de redação para outros formatos de dados sensíveis.
- Avaliar a persistência e a exportação das métricas.
- Avaliar o comportamento do circuit breaker quando houver várias instâncias da API.
- Manter modelos, limites e tarifas alinhados à configuração do provedor utilizado.

---

## Aula 20 — Dashboard de Desempenho da API

### Objetivo

Disponibilizar um painel de observabilidade em Streamlit para acompanhar a performance da API de pedidos. As requisições feitas em `/api/v1/` são registradas pelo middleware `config.metrics_middleware.APIMetricsMiddleware` e armazenadas no Redis. O dashboard lê esses eventos, aplica filtros e exibe KPIs e gráficos.

### Serviços e portas

- Dashboard de desempenho (Streamlit): http://localhost:8502

- Dashboard de vendas (Streamlit): http://localhost:8501

- API Django: http://localhost:8000

- Inventário FastAPI: http://localhost:8001

### Como subir

Reconstruir a imagem do dashboard:

```powershell

docker compose build performance-dashboard

```

Subir a stack:

```powershell

docker compose up -d

```

Acessar `http://localhost:8502`. Para gerar dados, use a coleção Postman da Aula 13 ou faça requisições autenticadas a `/api/v1/`. O middleware registra apenas os caminhos sob `/api/v1/`; chamadas ao Swagger, ReDoc e ao inventário não aparecem no painel.

### O que o painel exibe

- KPIs: total de requisições, latência média, latência p95 e taxa de erro (%).

- Latência média ao longo do tempo, agrupada por minuto.

- Volume de requisições por minuto (throughput).

- Distribuição dos códigos HTTP (2xx, 4xx, 5xx) em gráfico de pizza.

- Estatísticas de cache do inventário: hits, misses e hit rate por endpoint.

- Eventos de mensageria agrupados por direção e resultado.

- Tabela detalhada das requisições.

### Filtros

- Período: última hora, 6 horas, 24 horas, 7 dias ou todo o período.

- Endpoints: seleção múltipla dos endpoints registrados.

- Status HTTP: seleção múltipla dos grupos de status.

Os dados são cacheados com `@st.cache_data` (10 segundos para requisições e mensageria; 30 segundos para cache) para evitar consultas repetidas ao Redis. O botão **Atualizar métricas** limpa os caches e recarrega os dados.

### Variáveis de ambiente

- `REDIS_URL`: endereço do Redis (padrão `redis://redis:6379/0`).

- `API_METRICS_REDIS_KEY`: chave dos eventos HTTP (padrão `synapseshop:observability:requests`).

- `API_METRICS_RETENTION_SECONDS`: retenção dos eventos (padrão `604800`, 7 dias).

- `API_CACHE_METRICS_REDIS_KEY`: chave das métricas de cache.

- `API_MESSAGING_METRICS_REDIS_KEY`: chave das métricas de mensageria.

### Limitações conhecidas

- A retenção é aplicada pelo processo que grava a métrica; eventos antigos são removidos no momento da escrita.

- O painel de mensageria está pronto para receber dados, mas a instrumentação de produtores e consumidores do Kafka não faz parte desta etapa. Até lá, a seção exibe um aviso de estado vazio.

- O middleware mede apenas a API Django sob `/api/v1/`; o microsserviço de inventário é monitorado apenas pelas estatísticas de cache.

### Testes

Os testes das métricas e das transformações do painel ficam em `tests/unit/test_metrics.py` e `tests/unit/test_performance_dashboard_data.py`.

```powershell

$appPath = (Resolve-Path ".\app").Path

$testsPath = (Resolve-Path ".\tests").Path

$pytestConfigPath = (Resolve-Path ".\pytest.ini").Path

docker compose run --rm `

    -v "${appPath}:/app/app" `

    -v "${testsPath}:/app/tests" `

    -v "${pytestConfigPath}:/app/pytest.ini:ro" `

    api pytest -v -m unit tests

```

### Troubleshooting

- Painel vazio: confirme que houve requisições a `/api/v1/` e que o Redis está saudável (`docker compose ps redis`).

- Erro de conexão com Redis: verifique `REDIS_URL` e se o serviço `redis` está em execução.

- Dados antigos: a retenção padrão é de 7 dias; ajuste `API_METRICS_RETENTION_SECONDS` se necessário.

---

## Aula 21 — Consulta em linguagem natural (Text-to-SQL)

### Objetivo

Permitir que perguntas de negócio em português sejam convertidas em SQL somente leitura e executadas com segurança sobre o banco da aplicação. A página **Consulta IA** do dashboard de vendas envia a pergunta para `POST /api/v1/ask_sql`; a API usa o `llm_service` para gerar a consulta, valida a instrução e devolve o SQL, as colunas, as linhas e metadados.

### Endpoint

- Método: `POST`
- Caminho: `/api/v1/ask_sql`
- Acesso: `IsAuthenticated` (JWT via `/api/token/`).

Exemplo de requisição:

```json
{
  "question": "Quais os 5 últimos usuários cadastrados?"
}
```

Exemplo de resposta:

```json
{
  "question": "Quais os 5 últimos usuários cadastrados?",
  "sql": "SELECT id, username FROM auth_user ORDER BY date_joined DESC LIMIT 5",
  "columns": ["id", "username"],
  "rows": [{"id": 1, "username": "ana"}],
  "row_count": 1,
  "truncated": false,
  "meta": {
    "latency_ms": 1234.5,
    "tokens_prompt": 800,
    "tokens_output": 60,
    "estimated_cost_usd": 0.001
  }
}
```

Erros: `400` para payload ou consulta inválida (inclui `sql` quando disponível), `401`/`403` para autenticação, `422` para falha de execução não recuperável, `429` para limite do provedor, `502`/`503` para falhas do provedor ou de configuração e `503` para banco indisponível.

### Schema e privacidade

O contexto do schema inclui apenas `aula4api_category`, `aula4api_item`, `aula4api_pedido`, `aula4api_pagamento`, `aula4api_notificacao` e `auth_user`. Em `auth_user`, apenas `id`, `username`, `date_joined` e `is_active` são expostos. Colunas sensíveis como `password`, `email`, `first_name`, `last_name`, `idempotency_key` e `mensagem` são bloqueadas. As tabelas internas do Django, do Alembic, do catálogo do PostgreSQL e do inventário não fazem parte do contexto.

A pergunta é tratada como dado não confiável no prompt. O SQL gerado é validado antes da execução: apenas uma instrução `SELECT` (ou `WITH`), sem comentários, sem comandos de escrita ou administração, sem `SELECT *`, sem `tabela.*`, sem identificadores proibidos e apenas com tabelas permitidas. A execução ocorre em transação somente leitura, com `statement_timeout` e limite de linhas.

### Dashboard

A página **Consulta IA** fica em `app/dashboard/pages/2_Consulta_IA.py` e é acessível pelo dashboard de vendas em http://localhost:8501. Ela oferece:

- login com usuário e senha via `/api/token/` (ou uso de `ASK_SQL_API_TOKEN`);
- renovação automática do token via `/api/token/refresh/` quando possível;
- campo de pergunta, exemplos e exibição do SQL gerado;
- tabela de resultados, contagem de linhas, indicador de truncamento e latência da IA.

### Variáveis de ambiente

- `ASK_SQL_MAX_ROWS`: limite de linhas retornadas (padrão `200`).
- `ASK_SQL_STATEMENT_TIMEOUT_MS`: timeout da consulta (padrão `5000`).
- `API_BASE_URL`: URL da API usada pelo dashboard (padrão `http://api:8000`).
- `ASK_SQL_API_TOKEN`: token JWT opcional para acesso direto pelo painel; quando vazio, use o login.

### Testes

```powershell
docker compose run --rm api pytest -v -m unit tests
```

Os testes cobrem extração e validação do SQL, serialização, execução somente leitura (mockada e de integração), endpoint, cliente HTTP e geração de SQL no `llm_service`. A validação com perguntas reais exige `LLM_API_KEY`, `LLM_API_URL` e `LLM_MODEL` configurados.

### Troubleshooting

- `503` de configuração: confira `LLM_API_KEY`, `LLM_API_URL` e `LLM_MODEL`.
- `401` no painel: faça login novamente ou atualize `ASK_SQL_API_TOKEN`.
- Consulta rejeitada: veja o campo `detail`; o SQL gerado é devolvido em `sql` para diagnóstico.
- Sem dados: confirme que o banco está migrado e que o usuário do banco tem permissão de leitura.

---

## Aula 22 — Pipeline de CI com GitHub Actions

### Objetivo

Automatizar lint, testes e validação do build Docker a cada `push` e `pull request` para `main` ou `master`, além de permitir execução manual. O workflow fica em `.github/workflows/ci.yml` e o status aparece no badge no topo deste README.

### Jobs

- **`test-and-lint`** (`ubuntu-latest`):
  - checkout com `actions/checkout@v4`;
  - Python 3.12 com `actions/setup-python@v5`;
  - instalação de `requirements-dev.txt`;
  - `ruff check --no-cache .`;
  - PostgreSQL 16 efêmero com TLS, usando `scripts/postgres-ssl-entrypoint.sh`;
  - `python app/manage.py migrate --noinput`;
  - suíte completa com `pytest`, relatório JUnit e cobertura XML;
  - upload de `reports/` como artifact.

- **`docker-build`** (`ubuntu-latest`):
  - checkout;
  - `docker build -t synapseshop-api:test .` com BuildKit.

### PostgreSQL no CI

Os testes unitários usam SQLite, fakes e mocks. O teste `tests/integration/test_ask_sql_integration.py` valida a execução somente leitura contra PostgreSQL real. Por isso o CI sobe um banco efêmero com SSL (`sslmode=require`), executa as migrações e só então roda a suíte.

O banco usa a porta `55432` no runner para evitar conflito com serviços locais. Os certificados são gerados em tempo de execução e não são versionados.

### Lint

O Ruff é instalado por `requirements-dev.txt` e configurado em `.ruff.toml` com as regras `E` e `F`. `E402` é ignorado por causa dos imports após ajustes de `sys.path` e `django.setup()`; `E501` é ignorado por causa de SQL e linhas longas existentes. O Ruff não faz parte da imagem de runtime.

### Secrets e variáveis no GitHub

Configure em **Settings → Secrets and variables → Actions**:

| Nome | Uso |
| --- | --- |
| `SECRET_KEY` | Chave do Django. No CI há um fallback apenas para testes. |
| `DB_PASSWORD` | Senha do PostgreSQL efêmero. No CI há fallback `apppassword`. |
| `LLM_API_KEY` | Não é necessário no CI; os testes mockam o provedor. |

O projeto usa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e `DB_SSLMODE` em vez de uma única `DB_URL`. Nenhum valor real deve ser versionado. O `SECRET_KEY` é lido do ambiente em `app/config/settings.py`; localmente, o fallback de desenvolvimento continua disponível.

### Execução local equivalente

```powershell
python -m pip install -r requirements-dev.txt
ruff check --no-cache .
docker build -t synapseshop-api:test .
```

Para a suíte completa no ambiente Docker do projeto:

```powershell
$appPath = (Resolve-Path ".\app").Path
$testsPath = (Resolve-Path ".\tests").Path
$pytestConfigPath = (Resolve-Path ".\pytest.ini").Path
docker compose run --rm `
  -v "${appPath}:/app/app" `
  -v "${testsPath}:/app/tests" `
  -v "${pytestConfigPath}:/app/pytest.ini:ro" `
  api pytest -v
```

### Limitações

- Publicação em registry, deploy e cache avançado de dependências foram implementados na Aula 23.
- O badge só exibe o status depois que o workflow rodar no GitHub.
- O PostgreSQL do CI é efêmero e não persiste dados.

---

## Aula 23 — Cache, Docker Compose e publicação no DockerHub

### Objetivo

Reduzir o tempo do pipeline com cache de dependências Python e camadas Docker, validar a orquestração real dos serviços com Docker Compose e publicar a imagem da API no DockerHub em execuções controladas.

### Pipeline

O workflow `.github/workflows/ci.yml` agora tem três jobs:

- **`test-and-lint`**: instala as dependências com cache `pip`, executa Ruff, sobe PostgreSQL 16 efêmero com TLS, roda migrações e a suíte completa.
- **`compose-validation`**: gera certificados TLS, valida a configuração do Compose, constrói as imagens da API e do painel, sobe `db`, `redis` e `kafka`, inicializa os tópicos, roda migrações, inicia `api` e `dashboard` e verifica a comunicação entre os serviços.
- **`publish`**: executa somente em `push` para `main`/`master` ou em `workflow_dispatch`. Usa `docker/login-action` e `docker/build-push-action` para publicar a imagem da API.

### Cache

- O cache de pacotes Python usa `actions/setup-python@v5` com `cache: pip` e inclui os arquivos `requirements*.txt`.
- O cache de camadas Docker usa o backend `type=gha` do `docker/build-push-action`, com o escopo `api`.
- O cache só é efetivo no GitHub Actions; execuções locais não compartilham esse cache.

### Validação com Docker Compose

O job `compose-validation` valida o caminho `db` → `api` → `dashboard`:

- `docker compose config --quiet`;
- `docker compose build api dashboard`;
- subida de `db`, `redis` e `kafka` com `--wait`;
- execução do `kafka-init`;
- migrações com `python app/manage.py migrate --noinput`;
- subida de `api` e `dashboard` com healthchecks;
- `curl` em `http://localhost:8000/openapi.yaml` e `http://localhost:8501/_stcore/health`;
- verificação de API → PostgreSQL, painel → PostgreSQL e painel → API;
- coleta de logs e `docker compose down -v --remove-orphans` ao final.

O healthcheck da API usa `/openapi.yaml`; a comunicação com o banco é verificada separadamente com uma conexão Django. O painel usa `/_stcore/health` e verifica o banco via SQLAlchemy.

### Publicação no DockerHub

Configure em **Settings → Secrets and variables → Actions**:

| Nome | Uso |
| --- | --- |
| `DOCKERHUB_USERNAME` | Usuário ou organização do DockerHub. |
| `DOCKERHUB_TOKEN` | Token de acesso com permissão de push no repositório. |

A imagem publicada é:

```text
<DOCKERHUB_USERNAME>/synapseshop-api:latest
<DOCKERHUB_USERNAME>/synapseshop-api:<commit-sha>
```

O job não publica em `pull_request`. Se os secrets não estiverem configurados, o job falha; nenhum valor deve ser versionado.

### Execução local equivalente

```powershell
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

### Limitações

- O push real ao DockerHub só ocorre no GitHub Actions com os secrets configurados.
- O cache GHA não é reproduzido localmente.
- A validação do Compose sobe apenas `db`, `redis`, `kafka`, `api` e `dashboard`; workers, inventory e performance-dashboard não são exercitados nesse job.
- O CI usa `docker compose down -v` porque o runner é efêmero; localmente, evite `-v` para preservar dados.
- O ambiente de CI é efêmero e não persiste dados.

## Aula 24 — Assistente RAG sobre a documentação

### Objetivo

Responder perguntas sobre o projeto usando somente a documentação indexada, com recuperação de trechos, citações e limites explícitos quando não há evidência suficiente.

### Arquitetura

- `app/aula4api/rag_index.py`: índice SQLite, chunking com offsets, armazenamento de embeddings e busca por similaridade de cosseno.
- `app/aula4api/rag_embeddings.py`: cliente OpenAI-compatible para gerar embeddings em lote.
- `app/aula4api/rag.py`: ingestão, recuperação, guardrails e montagem das citações.
- `app/aula4api/management/commands/ingest_docs.py`: comando explícito de indexação.
- `app/aula4api/views.py`: endpoint autenticado `POST /api/v1/ask_docs`.
- `app/aula4api/llm_service.py`: prompt de documentação, redação de dados sensíveis e geração da resposta.

O índice fica em um arquivo SQLite separado do PostgreSQL. Localmente, o caminho padrão é `app/data/rag_index.sqlite3`. No Docker Compose, o arquivo fica em `/data/rag_index.sqlite3`, persistido no volume nomeado `rag_index_data`.

### Ingestão

Por padrão, o comando indexa `README.md` e `docs/openapi.yaml`:

```powershell
python app/manage.py ingest_docs
```

Também é possível escolher arquivos, índice e forçar a reindexação:

```powershell
python app/manage.py ingest_docs --paths README.md docs/openapi.yaml
python app/manage.py ingest_docs --index app/data/rag_index.sqlite3
python app/manage.py ingest_docs --force
```

No Compose:

```powershell
docker compose exec api python app/manage.py ingest_docs
```

O comando ignora arquivos cujo conteúdo e modelo de embedding não mudaram. Use `--force` após trocar o modelo de embedding ou os parâmetros de chunking. Não há reindexação automática na subida da API.

### Endpoint

```http
POST /api/v1/ask_docs
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "question": "Como subir a API e o painel com Docker Compose?",
  "top_k": 3,
  "min_score": 0.25
}
```

`top_k` aceita valores de 1 a 5. `min_score` aceita valores de 0 a 1. A resposta inclui a resposta gerada, as fontes recuperadas e metadados:

```json
{
  "question": "Como subir a API e o painel com Docker Compose?",
  "answer": "Use docker compose up -d --wait ... [README.md#1200-2800]",
  "sources": [
    {
      "path": "README.md",
      "title": "Docker Essencial",
      "range": "1200-2800",
      "score": 0.82
    }
  ],
  "meta": {
    "top_k": 3,
    "min_score": 0.25,
    "retrieved": 1,
    "llm": {
      "latency_ms": 850.0,
      "tokens_prompt": 900,
      "tokens_output": 120
    }
  }
}
```

O campo `range` usa offsets de caracteres com fim exclusivo. Se o índice estiver vazio, o endpoint retorna HTTP 503 com a instrução de execução do `ingest_docs`. Se nenhum trecho atingir `min_score`, a API retorna HTTP 200 com uma resposta fixa de informação insuficiente e `sources: []`, sem chamar o LLM.

### Variáveis de ambiente

| Nome | Uso |
| --- | --- |
| `EMBEDDING_API_URL` | URL OpenAI-compatible do provedor de embeddings. |
| `EMBEDDING_API_KEY` | Chave do provedor; se vazia, usa `LLM_API_KEY`. |
| `EMBEDDING_MODEL` | Modelo de embeddings configurado. |
| `EMBEDDING_TIMEOUT_SECONDS` | Timeout por tentativa. |
| `EMBEDDING_MAX_RETRIES` | Número máximo de tentativas HTTP. |
| `EMBEDDING_RETRY_BASE_SECONDS` | Base do backoff exponencial. |
| `EMBEDDING_BATCH_SIZE` | Quantidade de textos por requisição. |
| `RAG_INDEX_PATH` | Caminho do arquivo SQLite do índice. |
| `RAG_CHUNK_TOKENS` | Tamanho aproximado do chunk em tokens. |
| `RAG_CHUNK_OVERLAP_TOKENS` | Sobreposição aproximada entre chunks. |

### Persistência no Docker

O Compose monta `rag_index_data:/data` na API e define `RAG_INDEX_PATH=/data/rag_index.sqlite3`. Para recriar a API mantendo o índice:

```powershell
docker compose up -d --build api
```

Para remover também o índice persistido, remova o volume explicitamente. Evite `docker compose down -v` em ambientes com dados que devem ser preservados.

### Limitações

- A indexação é explícita; mudanças em `README.md` ou `docs/openapi.yaml` exigem novo `ingest_docs`.
- A qualidade das respostas depende do provedor de embeddings e do modelo de linguagem configurados.
- O SQLite é um arquivo local do container; múltiplas réplicas da API exigiriam armazenamento compartilhado ou reindexação por réplica.
- O endpoint não valida semanticamente cada citação retornada pelo modelo; os `sources` são os trechos efetivamente recuperados.
- Não há interface de chat no painel; a entrega é pela API e pelo OpenAPI.
- Sem credenciais reais de embedding/LLM, a validação automatizada usa provedores falsos e não mede qualidade real das respostas.
