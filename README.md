# Docker_Essencial — SynapseShop

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
│   │   ├── settings.py
│   │   └── urls.py
│   ├── inventory/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── services.py
│   │   ├── schemas.py
│   │   └── main.py
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
│       └── test_assist_api.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
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
