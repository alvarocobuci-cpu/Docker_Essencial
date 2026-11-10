# PROMPTS.md — Histórico de desenvolvimento do SynapseShop

Este arquivo reúne os principais prompts e o trabalho realizado com apoio de IA durante a evolução do projeto `Docker_Essencial`, do ambiente inicial com Docker à camada de assistência por IA.

**Observação:** os prompts abaixo são resumos representativos do trabalho realizado, não transcrições literais de todas as conversas. Nas aulas em que não há registro integral do diálogo, o conteúdo descreve apenas as atividades e tecnologias documentadas no projeto.

---

## 1. Objetivo do documento

Registrar os objetivos de cada etapa, os principais pedidos feitos durante o desenvolvimento, as alterações implementadas e as validações conhecidas. A intenção é manter um histórico útil para acompanhar a evolução do projeto e entender as decisões técnicas adotadas.

O mesmo repositório foi utilizado ao longo do curso. A aplicação começou como um serviço simples com Flask, Docker e PostgreSQL e evoluiu para uma estrutura com Django REST Framework, um microsserviço de inventário com FastAPI, persistência, mensageria assíncrona, testes automatizados, documentação OpenAPI e um serviço de assistência por LLM.

---

## 2. Tecnologias utilizadas ao longo do projeto

- Python 3.12
- Flask
- Django 5.2.6 e Django REST Framework 3.16.1
- `djangorestframework-simplejwt` e `django-filter`
- FastAPI e Uvicorn
- PostgreSQL 16
- SQLAlchemy e Alembic
- Docker e Docker Compose
- Redis e `redis-py`
- Apache Kafka
- pytest, pytest-cov e HTTPX
- OpenAPI, Swagger UI, ReDoc, Redocly CLI e Postman
- Git e GitHub

A lista reúne tecnologias utilizadas em diferentes etapas. Isso não significa que todas sejam chamadas por todos os serviços.

---

## Aula 3 — Docker Essencial

### Objetivo

Preparar uma aplicação Python em contêineres, com uma API e PostgreSQL, aplicando boas práticas de construção e execução de imagens.

### Principais prompts utilizados — resumo

1. Criar um Dockerfile para executar a aplicação Python no contêiner.
2. Organizar um build em múltiplas etapas para separar a instalação das dependências da imagem final.
3. Aproveitar o cache de dependências durante o build.
4. Executar a aplicação com um usuário sem privilégios de root.
5. Configurar a API e o PostgreSQL no Docker Compose, com volume persistente e healthcheck do banco.
6. Documentar a estrutura, os comandos de execução, os testes e as dificuldades encontradas.

### Desenvolvimento registrado

O projeto começou com uma aplicação Flask e PostgreSQL. O Dockerfile utilizou build multistage, instalação de dependências em uma etapa separada e execução da aplicação em uma imagem final com usuário não-root. O Docker Compose foi configurado para iniciar a API e o banco, incluindo persistência e verificação de saúde do PostgreSQL.

### Validações

Foram utilizados comandos do Docker Compose para construir a imagem, iniciar os serviços e verificar o funcionamento da aplicação e do banco.

---

## Aula 4 — CRUD da API principal com Django REST Framework

### Objetivo

Reaproveitar a estrutura da Aula 3 para criar uma API REST com Django REST Framework, sem começar outro projeto do zero.

### Principais prompts utilizados

1. **Adaptação do projeto:** aproveitar o projeto existente com Docker e PostgreSQL para desenvolver a API Django.
2. **Configuração do Django:** integrar Django e Django REST Framework ao ambiente Docker.
3. **PostgreSQL:** configurar a aplicação para utilizar o banco já disponível no Docker Compose.
4. **Modelos:** criar `Category` e `Item` com os campos necessários e o relacionamento entre eles.
5. **Serializers:** criar `ModelSerializer` e validar os campos recebidos.
6. **CRUD:** disponibilizar operações de criação, consulta, atualização e exclusão por meio de `ModelViewSet`.
7. **Rotas:** configurar `DefaultRouter` e os endpoints sob `/api/v1/`.
8. **Testes:** verificar operações e respostas HTTP esperadas.
9. **Documentação:** organizar a coleção de testes do Postman e registrar as etapas no `PROMPTS.md`.

### Desenvolvimento registrado

Foram adicionados os modelos `Category` e `Item`, serializers com validações, viewsets e rotas para as operações CRUD. O projeto continuou utilizando Docker Compose e PostgreSQL.

### Validações

A validação da atividade incluiu verificar os endpoints e seus códigos HTTP, bem como documentar as operações no Postman.

---

## Aula 5 — Microsserviço de inventário com FastAPI

### Objetivo

Acrescentar um microsserviço de inventário à solução, separado da API principal em Django.

### Principais prompts utilizados — resumo

1. Criar uma API de inventário com FastAPI.
2. Separar os schemas de entrada e saída da lógica de persistência.
3. Integrar o serviço ao PostgreSQL utilizando SQLAlchemy.
4. Organizar o código em módulos de banco de dados, modelos, repositórios e serviços.
5. Executar o microsserviço no Docker Compose e disponibilizar a documentação automática da API.

### Desenvolvimento registrado

O projeto passou a conter o serviço `inventory`, desenvolvido com FastAPI, SQLAlchemy e PostgreSQL. O código foi organizado em módulos como `database.py`, `models.py`, `repositories.py`, `services.py`, `schemas.py` e `main.py`.

### Validações

A aplicação foi preparada para execução em contêiner e para testes das operações HTTP e da persistência do inventário. Não é mantido aqui um resultado numérico de testes específico da Aula 5.

---

## Aula 6 — Persistência, transações e validação

### Objetivo

Aprimorar a consistência das operações de banco de dados e organizar o tratamento de falhas na camada de persistência.

### Principais prompts utilizados — resumo

1. Validar os dados recebidos antes de alterar o banco.
2. Organizar regras de negócio em serviços e acesso a dados em repositórios.
3. Utilizar transações e rollback para evitar persistência parcial em caso de falha.
4. Testar cenários de sucesso e de erro durante operações de banco de dados.

### Desenvolvimento registrado

A documentação do projeto registra o uso de padrões Repository e Service, validação de dados, transações e rollback como parte da evolução do backend. Esta seção é um resumo dos temas documentados no projeto, não uma transcrição literal de prompts da aula.

### Validações

Foram previstos cenários para conferir o comportamento das operações e o tratamento de falhas. Não há, neste registro, um total específico de testes atribuído exclusivamente à Aula 6.

---

## Aula 7 — Autenticação e controle de acesso

### Objetivo

Adicionar autenticação e diferenciar o acesso às operações da API.

### Principais prompts utilizados — resumo

1. Integrar autenticação JWT à API Django REST Framework.
2. Configurar os endpoints necessários para obter e atualizar tokens.
3. Proteger operações e aplicar permissões por papel de usuário.
4. Validar solicitações autenticadas e não autenticadas.

### Desenvolvimento registrado

O projeto passou a utilizar `djangorestframework-simplejwt` e regras de permissão. A configuração evoluiu para incluir autenticação, controle de acesso por papéis e limitação de requisições (*throttling*).

### Validações

A validação dessa funcionalidade envolve conferir acesso autorizado e rejeição de solicitações sem a autenticação ou permissão necessária. Não há, neste registro, um total específico de testes atribuído exclusivamente à Aula 7.

---

## Aula 8 — Cache com Redis

### Objetivo

Utilizar Redis como cache auxiliar para reduzir consultas repetidas e praticar o padrão cache-aside.

### Principais prompts utilizados — resumo

1. Integrar Redis à aplicação Python.
2. Implementar leitura do cache antes de consultar a fonte persistente.
3. Tratar ausência de valores e expiração de chaves.
4. Garantir que o PostgreSQL continue sendo a fonte persistente dos dados.

### Desenvolvimento registrado

O Redis foi incorporado ao ambiente como cache auxiliar. O projeto registra o uso de cache-aside e da biblioteca `redis-py`; o PostgreSQL permanece como fonte de dados persistente.

### Validações

Os cenários relevantes incluem consulta em cache, ausência de chave e recuperação dos dados persistidos. Não há, neste registro, um total específico de testes atribuído exclusivamente à Aula 8.

---

## Aulas 9 e 10 — Mensageria assíncrona com Kafka

### Objetivo

Desacoplar o recebimento de pedidos do processamento em segundo plano, utilizando eventos, consumidores e mecanismos de recuperação de falhas.

### Principais prompts utilizados — resumo

1. Integrar Apache Kafka ao ambiente Docker Compose.
2. Publicar um evento quando a API recebe um pedido.
3. Criar workers consumidores independentes da API.
4. Configurar tópicos, partições e grupos de consumidores.
5. Implementar retentativas com backoff, idempotência e dead-letter queue (DLQ).
6. Registrar instruções para iniciar o ambiente e verificar o processamento das mensagens.

### Desenvolvimento registrado

A API publica o evento `PedidoCriado` no tópico `pedidos.criado`. Um worker independente consome o evento e registra o pedido no PostgreSQL. O ambiente inclui inicialização repetível dos tópicos por meio do serviço `kafka-init`, retentativas de processamento e encaminhamento para o tópico `pedidos.criado.dlq` após falhas persistentes.

A configuração documentada utiliza três partições para `pedidos.criado`, uma partição para `pedidos.criado.dlq`, retenção de três dias para o tópico principal e de 30 dias para a DLQ. O ambiente local utiliza um broker KRaft com fator de replicação 1 e, portanto, não oferece alta disponibilidade.

### Validações

Foram verificados o consumo das mensagens e o funcionamento dos workers no ambiente local. O projeto também registra um teste em que o atraso de consumo (*lag*) chegou a zero.

---

## Aula 11 — Fluxo de pedido, pagamento e notificação

### Objetivo

Expandir o processamento assíncrono para incluir pagamento simulado e notificação interna após a persistência de um pedido.

### Principais prompts utilizados — resumo

1. Publicar `PagamentoSolicitado` após a persistência do pedido.
2. Implementar um `payment-worker` para consumir a solicitação, validar dados e registrar o pagamento simulado.
3. Publicar `PagamentoProcessado` após o processamento do pagamento.
4. Implementar um `notification-worker` para registrar a notificação interna.
5. Manter retentativas, DLQ e proteção contra registros duplicados.

### Desenvolvimento registrado

O `payment-worker` consome `pagamentos.solicitados`, registra o pagamento simulado no PostgreSQL e publica `PagamentoProcessado` em `pagamentos.processados`. O `notification-worker` consome esse evento, registra a notificação no PostgreSQL e publica `NotificacaoEnviada` em `notificacoes.enviadas`.

Os modelos `Pagamento` e `Notificacao` possuem relacionamento um-para-um com `Pedido`. Os consumidores têm grupos separados e utilizam mecanismos de retentativa e DLQ. O pagamento da atividade é simulado e aprovado automaticamente na implementação registrada.

### Validações

O teste local confirmou o caminho de pedido criado, pagamento aprovado e notificação registrada no PostgreSQL. Os registros temporários de teste e as chaves de Redis relacionadas foram removidos ao final.

---

## Aula 12 — Testes automatizados e cobertura

### Objetivo

Estruturar a suíte de testes automatizados para validar schemas, serviços, cache, persistência, idempotência e contratos de eventos.

### Principais prompts utilizados — resumo

1. Organizar testes unitários e de integração com pytest.
2. Criar fixtures compartilhadas e dependências simuladas para isolar os testes.
3. Testar o microsserviço de inventário com banco SQLite em memória.
4. Medir cobertura com pytest-cov e configurar um limite mínimo para os módulos selecionados.
5. Documentar comandos de execução no PowerShell e Docker.

### Desenvolvimento registrado

A estrutura de testes inclui `tests/conftest.py`, `tests/unit/`, `tests/integration/`, `pytest.ini` e `.coveragerc`. Os testes utilizam fixtures, FakeRedis, relógio fixo e banco SQLite em memória em cenários apropriados.

### Validações

Na validação registrada da Aula 12, a suíte apresentou 52 testes aprovados e 100% de cobertura nos módulos medidos: `inventory`, `aula4api.idempotency` e `aula4api.event_contracts`. Esse valor não representa 100% de cobertura da aplicação inteira.

---

## Aula 13 — OpenAPI, Swagger e Postman

### Objetivo do apoio de IA

Inspecionar os endpoints existentes e preparar a documentação das APIs com um contrato OpenAPI, interfaces de documentação e uma coleção de requisições para integração.

### Principais prompts utilizados

1. Inspecionar a aplicação e documentar rotas, schemas, parâmetros e respostas compatíveis com o código.
2. Criar um contrato OpenAPI para a API Django REST Framework e o serviço FastAPI.
3. Configurar Swagger UI e ReDoc para apresentar o contrato.
4. Validar a especificação com Redocly CLI e registrar as exceções necessárias.
5. Criar a coleção Postman e um ambiente local com valores de exemplo, sem credenciais reais.
6. Atualizar README, CHANGELOG e checklist para integradores.

### Desenvolvimento registrado

Foi criado o contrato `docs/openapi.yaml`, junto com a configuração `redocly.yaml`, o checklist `docs/integrator-checklist.md`, a coleção Postman e seu ambiente local. O Django disponibiliza o contrato combinado, Swagger UI e ReDoc.

### Validações

- O contrato OpenAPI passou pelo lint do Redocly CLI.
- Os endpoints locais de OpenAPI, Swagger UI e ReDoc foram consultados e retornaram HTTP 200.
- Os arquivos da coleção Postman e do ambiente foram validados como JSON.

### Observações e limites conhecidos

- `X-Trace-Id` está documentado como convenção futura, mas não é processado pela aplicação.
- A resposta de erro ainda não segue integralmente RFC 7807 com `application/problem+json`.
- A API FastAPI de inventário não implementa paginação, filtros, ordenação ou autenticação JWT.
- O contrato documenta algumas convenções futuras que não são suportadas pelas rotas atuais; as diferenças estão descritas em `docs/integrator-checklist.md`.

---

## Aula 14 — Assistente de IA e `llm_service`

### Objetivo do apoio de IA

Desenvolver uma camada de assistência capaz de resumir e explicar logs de aplicações, com atenção à privacidade, à resiliência de chamadas externas, à estimativa de custos e à telemetria.

### Principais prompts utilizados — resumo

1. Criar um serviço para comunicar com um provedor de LLM usando configurações e credenciais em variáveis de ambiente.
2. Implementar timeout limitado a cinco segundos, retentativas com backoff exponencial e jitter e circuit breaker.
3. Criar templates de prompt para os modos `summarize` e `explain`, tratando logs como dados não confiáveis.
4. Redigir padrões conhecidos de informações pessoais e segredos antes do envio dos logs e também na resposta do modelo.
5. Criar o endpoint `POST /api/v1/assist`, com validação de modo, logs, temperatura e limite de tokens.
6. Implementar respostas de erro e telemetria de latência, falhas, tokens e custo estimado.
7. Criar testes simulados de timeout, HTTP 429, HTTP 5xx, indisponibilidade do provedor, resposta inválida e circuit breaker.
8. Atualizar a documentação e identificar melhorias futuras.

### Desenvolvimento registrado

O serviço está em `app/aula4api/llm_service.py`. O endpoint aceita `summarize` ou `explain`; os logs podem ser texto ou lista de textos. A temperatura é limitada a 0–1 e `max_tokens` a 1–256, com padrão de 256. A chamada usa timeout limitado a cinco segundos e até três tentativas, conforme a configuração. O serviço inclui backoff com jitter, circuit breaker, redação de padrões conhecidos de dados sensíveis e métricas agregadas.

As variáveis de configuração incluem URL, chave e modelo do provedor, timeout, tentativas, parâmetros do circuit breaker, limite de caracteres de entrada e tarifas usadas para estimar o custo. O `.env.example` contém valores de exemplo, não credenciais reais.

### Validações executadas

- A imagem Docker da API foi reconstruída.
- Os arquivos Python verificados foram compilados sem erros de sintaxe.
- `python app/manage.py check` não identificou problemas.
- Os testes do `llm_service` apresentaram 14 aprovações.
- Os testes do endpoint apresentaram 11 aprovações.
- A suíte completa apresentou 77 testes aprovados e um aviso de depreciação relacionado ao Starlette/AnyIO.

### Observações e limites conhecidos

- Os testes utilizaram chamadas simuladas. Não foi realizada uma chamada real a um provedor externo.
- A estimativa de custos depende das tarifas configuradas para o modelo utilizado; os valores padrão são zero.
- A redação de dados sensíveis é baseada em padrões conhecidos e não garante a detecção de todas as informações confidenciais.
- As métricas agregadas são mantidas em memória e são perdidas quando o processo reinicia.
- Melhorias futuras incluem persistir ou exportar métricas, ampliar os testes de redação e validar a integração real em ambiente controlado.

---

## Aula 20 — Dashboard de Desempenho da API

### Objetivo do apoio de IA

Construir um painel de observabilidade em Streamlit para visualizar métricas de desempenho da API de pedidos, com KPIs, gráficos interativos, filtros e cache de consultas, integrado ao Docker Compose.

### Principais prompts utilizados — resumo

1. Projetar um dashboard em Streamlit que consuma eventos HTTP armazenados no Redis, sem acoplar o painel ao banco principal.
2. Criar cards de KPI para total de requisições, latência média, latência p95 e taxa de erro.
3. Criar gráfico de linha para latência média por minuto e gráfico de barras para throughput.
4. Criar gráfico de pizza para a distribuição dos grupos de status HTTP (2xx, 4xx, 5xx).
5. Adicionar filtros de período, endpoint e status HTTP na barra lateral, mantendo os demais gráficos sincronizados.
6. Usar `@st.cache_data` para evitar consultas repetidas ao Redis e documentar o TTL escolhido.
7. Separar a leitura/transformação dos dados em um módulo testável, sem depender de Streamlit nos testes.
8. Adicionar uma seção de cache do inventário lendo os contadores já gravados no Redis.
9. Preparar uma seção de mensageria com estado vazio amigável, sem instrumentar produtores e consumidores nesta etapa.
10. Configurar o serviço `performance-dashboard` no `docker-compose.yml` e documentar build, acesso e variáveis de ambiente.
11. Escrever testes unitários para a montagem dos eventos, normalização, filtros, KPIs e agregações.
12. Atualizar README, CHANGELOG, `.env.example` e este arquivo com as decisões e limitações.

### Desenvolvimento registrado

O middleware `config.metrics_middleware.APIMetricsMiddleware` mede apenas requisições sob `/api/v1/` e grava eventos no Redis por meio de `config/metrics.py`. O dashboard fica em `app/performance_dashboard/streamlit_app.py` e usa `app/performance_dashboard/metrics_data.py` para parse, filtros, KPIs e agregações. O Streamlit é exposto na porta `8502` pelo serviço `performance-dashboard`.

Os KPIs e gráficos usam os eventos filtrados. A seção de cache lê `cache:metrics:inventory_list` e `cache:metrics:inventory_detail`. A seção de mensageria lê a chave `synapseshop:observability:messaging` e informa quando não há eventos.

### Validações executadas

- `docker compose config` validado após a correção do `docker-compose.yml`.
- Imagem do `performance-dashboard` construída e serviço iniciado.
- Endpoint de saúde do Streamlit consultado em `http://localhost:8502/_stcore/health`.
- Requisições de teste enviadas à API para popular os KPIs e filtros.
- Testes unitários de `config/metrics.py` e `performance_dashboard/metrics_data.py` executados com pytest.

### Observações e limites conhecidos

- O painel depende do Redis; se o serviço estiver indisponível, as seções mostram aviso de erro.
- A instrumentação de mensageria (produtores e consumidores Kafka) não faz parte desta etapa; a seção existe, mas fica vazia até essa instrumentação ser adicionada.
- O middleware não mede o microsserviço de inventário; apenas os contadores de cache são exibidos.
- A retenção padrão das métricas é de sete dias e é aplicada no momento da escrita.

---

## Aula 21 — Consulta em linguagem natural (Text-to-SQL)

### Objetivo do apoio de IA

Implementar um endpoint que converte perguntas de negócio em português para SQL somente leitura, com validação de segurança, execução controlada e uma página no dashboard para consulta.

### Principais prompts utilizados — resumo

1. Projetar o fluxo pergunta → prompt → SQL → validação → execução → resposta JSON.
2. Definir um contexto de schema curado, com apenas tabelas e colunas necessárias, ocultando dados pessoais e tabelas internas.
3. Reutilizar o `llm_service` existente, incluindo resiliência, circuit breaker e telemetria, sem redigir o SQL de saída.
4. Validar o SQL com `sqlparse`: uma única instrução, apenas `SELECT`/`WITH`, sem comentários, sem comandos de escrita ou administração e sem `SELECT *`.
5. Bloquear identificadores sensíveis e tabelas não permitidas, com suporte a CTEs.
6. Executar em transação somente leitura, com `statement_timeout` e limite de linhas.
7. Expor `POST /api/v1/ask_sql` com autenticação JWT e mapeamento de erros.
8. Criar uma página Streamlit multipágina no dashboard de vendas, com login, renovação de token, exemplos e exibição do SQL e da tabela.
9. Escrever testes unitários para extração, validação, serialização, endpoint, cliente HTTP e geração de SQL.
10. Atualizar README, CHANGELOG, OpenAPI e `.env.example`.

### Desenvolvimento registrado

O endpoint fica em `app/aula4api/views.py` e delega para `app/aula4api/ask_sql.py`. O contexto de schema, as listas de permissão e as validações ficam nesse módulo. A geração usa `llm_service.generate_sql`, que reutiliza o pipeline de retentativas e circuit breaker com `temperature=0.0`.

A execução usa `connection.cursor()` dentro de `transaction.atomic()`, com `SET TRANSACTION READ ONLY` e `SET LOCAL statement_timeout`. O resultado é serializado para tipos JSON e limitado por `ASK_SQL_MAX_ROWS`.

O painel usa `app/dashboard/ask_sql_client.py` para chamar a API e `app/dashboard/pages/2_Consulta_IA.py` para a interface. O login usa `/api/token/`; o refresh usa `/api/token/refresh/`.

### Validações executadas

- `docker compose config` para validar o Compose.
- Testes unitários de validação, endpoint, cliente HTTP e `generate_sql`.
- Execução somente leitura validada contra o PostgreSQL local com SQL conhecido e CTE.
- Endpoint sem autenticação retornou `401`; página validada com AppTest sem exceções.
- Health check do dashboard verificado.
- A validação com LLM real não foi executada por ausência de `LLM_API_KEY`.

### Observações e limites conhecidos

- A qualidade do SQL depende do modelo e do contexto de schema; o validador reduz, mas não elimina, o risco de consultas incorretas.
- A execução é somente leitura e limitada, mas o usuário do banco ainda deve ter permissões mínimas.
- O `ASK_SQL_API_TOKEN` é opcional e deve ser tratado como segredo; sem ele, o painel solicita login.
- A validação com LLM real exige credenciais configuradas; sem elas, o endpoint retorna `503`.

---

## Aula 22 — Pipeline de CI com GitHub Actions

### Objetivo do apoio de IA

Automatizar lint, testes e validação do build Docker em GitHub Actions, mantendo segredos fora do repositório e garantindo que o teste de integração Text-to-SQL rode contra PostgreSQL real.

### Principais prompts utilizados — resumo

1. Analisar a suíte pytest e identificar dependências externas, especialmente o teste de integração que exige PostgreSQL com TLS.
2. Estruturar `.github/workflows/ci.yml` com `push`, `pull_request` e `workflow_dispatch`.
3. Separar os jobs `test-and-lint` e `docker-build`.
4. Escolher Ruff, criar `requirements-dev.txt` e `.ruff.toml` sem adicionar ferramentas de lint à imagem de runtime.
5. Abstrair `SECRET_KEY` por variável de ambiente e usar secrets do GitHub com fallback para CI.
6. Subir PostgreSQL 16 efêmero com TLS no runner, executar migrações e rodar `pytest` com relatórios.
7. Validar o build da imagem com `docker build -t synapseshop-api:test .`.
8. Atualizar README, badge, CHANGELOG e este histórico.

### Desenvolvimento registrado

O workflow fica em `.github/workflows/ci.yml`. O job `test-and-lint` instala `requirements-dev.txt`, executa `ruff check --no-cache .`, inicia um container PostgreSQL com o entrypoint TLS do projeto, roda `python app/manage.py migrate --noinput` e executa a suíte completa. Os relatórios JUnit e cobertura são enviados como artifact. O job `docker-build` valida o empacotamento da imagem da API.

O `SECRET_KEY` passou a ser lido do ambiente em `app/config/settings.py`, com fallback local. O CI usa `secrets.SECRET_KEY` e `secrets.DB_PASSWORD` quando configurados; caso contrário, usa valores efêmeros de teste.

### Validações executadas

- Parse do YAML do workflow.
- `ruff check --no-cache .` no repositório.
- Suíte completa com `pytest`.
- Build local da imagem com `docker build`.
- Inicialização do PostgreSQL efêmero com TLS e `pg_isready`.

### Observações e limites conhecidos

- Publicação em registry, deploy e cache avançado de dependências foram implementados na Aula 23.
- O workflow real só pode ser executado no GitHub após o push.
- Segredos reais devem ser configurados no painel do GitHub; os fallbacks existem apenas para o CI.

---

## Aula 23 — Cache, orquestração e publicação no DockerHub

### Objetivo do apoio de IA

Reduzir o tempo do pipeline, validar a subida conjunta dos serviços com Docker Compose e configurar a publicação da imagem da API no DockerHub sem versionar credenciais.

### Principais prompts utilizados — resumo

1. Revisar o workflow da Aula 22 e identificar onde adicionar cache de dependências Python e camadas Docker.
2. Adicionar cache `pip` ao `actions/setup-python@v5`.
3. Estruturar um job de validação com `docker compose config`, build, migrações e healthchecks.
4. Definir healthchecks para `api` e `dashboard` e ajustar a dependência entre eles.
5. Validar API → PostgreSQL, painel → PostgreSQL e painel → API.
6. Configurar `docker/login-action` e `docker/build-push-action` com tags `latest` e SHA.
7. Restringir a publicação a push em `main`/`master` e `workflow_dispatch`.
8. Atualizar README, CHANGELOG e este histórico.

### Desenvolvimento registrado

O job `test-and-lint` passou a usar cache `pip` com `cache-dependency-path` para os arquivos de requirements. O antigo job `docker-build` foi substituído por `compose-validation`, que constrói as imagens da API e do painel, sobe `db`, `redis` e `kafka`, executa `kafka-init`, aplica migrações e inicia `api` e `dashboard` com healthchecks.

A comunicação é verificada em três direções: a API abre uma conexão Django com o PostgreSQL, o painel executa `SELECT 1` via SQLAlchemy e o painel consulta `/openapi.yaml` da API. Em caso de falha, o workflow imprime o estado e os logs do Compose e publica `compose-logs.txt` como artifact; a limpeza usa `docker compose down -v --remove-orphans`.

O job `publish` usa `docker/setup-buildx-action`, `docker/login-action` e `docker/build-push-action`. Ele publica somente a imagem da API, com tags `latest` e o SHA do commit, e usa cache GHA no escopo `api`. A execução ocorre em push para `main`/`master` ou em `workflow_dispatch`, nunca em `pull_request`.

### Validações executadas

- Parse do YAML do workflow.
- `docker compose config --quiet`.
- `ruff check --no-cache .`.
- Suíte completa com `pytest`.
- Build das imagens da API e do painel com Docker Compose.
- Subida de `db`, `redis`, `kafka`, `api` e `dashboard`, com migrações e healthchecks.
- Checagens de API → PostgreSQL, painel → PostgreSQL e painel → API.
- `git diff --check`.

### Observações e limites conhecidos

- O push real ao DockerHub depende dos secrets `DOCKERHUB_USERNAME` e `DOCKERHUB_TOKEN` e só ocorre no GitHub Actions.
- O cache GHA não é reproduzido localmente.
- A validação do Compose não sobe workers, inventory nem performance-dashboard.
- O workflow real só pode ser executado no GitHub após o push.

---

## Aula 24 — Assistente RAG sobre a documentação

### Objetivo do apoio de IA

Projetar e implementar um assistente que responde perguntas usando somente a documentação do projeto, com recuperação de trechos, citações e guardrails contra respostas sem evidência.

### Principais prompts utilizados — resumo

1. Comparar armazenamento do índice em SQLite, PostgreSQL e vetor dedicado; escolher a opção compatível com o escopo da aula.
2. Definir ingestão explícita por comando e reindexação com `--force`.
3. Definir autenticação JWT obrigatória e variáveis `EMBEDDING_*` com fallback para `LLM_API_KEY`.
4. Planejar chunking com offsets, sobreposição e busca por similaridade de cosseno.
5. Definir guardrails para índice vazio, ausência de trechos acima de `min_score` e citações obrigatórias.
6. Planejar persistência do índice no Docker Compose e cópia do `README.md` na imagem.
7. Atualizar OpenAPI, README, CHANGELOG e testes automatizados.

### Desenvolvimento registrado

O índice foi implementado em SQLite, com tabelas `documents` e `chunks`, embeddings em BLOB float32 normalizados e busca por cosseno. A ingestão calcula hash SHA-256 do conteúdo e ignora arquivos inalterados quando o modelo de embedding também não mudou.

O cliente de embeddings usa uma API OpenAI-compatible, processa textos em lotes, aplica timeout e retries com backoff e valida quantidade, índices, dimensões e valores finitos. As falhas reutilizam a taxonomia de erros do `llm_service`, permitindo o mesmo mapeamento HTTP do endpoint `ask_docs`.

O endpoint `POST /api/v1/ask_docs` exige JWT, aceita `top_k` de 1 a 5 e `min_score` de 0 a 1. Se o índice estiver vazio, retorna 503 antes de chamar o provedor. Se nenhum trecho passar pelo limite de similaridade, retorna 200 com resposta fixa e `sources: []`, sem chamar o LLM. Quando há trechos, o contexto é montado com identificadores `[caminho#inicio-fim]` e enviado ao prompt de documentação.

O Compose passou a montar `rag_index_data:/data` na API e a definir `RAG_INDEX_PATH=/data/rag_index.sqlite3`. A imagem copia o `README.md` e cria `/data` com permissão para `appuser`.

### Validações executadas

- Testes unitários de chunking, offsets, busca, filtros, reindexação, embeddings, guardrails e mapeamento HTTP.
- Teste de integração indexando `README.md` e `docs/openapi.yaml` com embedder falso.
- `ruff check --no-cache .`.
- Suíte completa com `pytest`.
- `python app/manage.py check`.
- `docker compose config --quiet`.
- Build da imagem da API e validação do comando `ingest_docs` no Compose.

### Observações e limites conhecidos

- A qualidade real das respostas depende de credenciais e modelos externos; os testes usam provedores falsos.
- A indexação é explícita e não há watcher ou reindexação automática.
- O índice SQLite é local ao container; múltiplas réplicas exigiriam compartilhamento ou reindexação por réplica.
- As citações são os trechos recuperados; o conteúdo textual retornado pelo LLM não é validado semanticamente.
- Não foi adicionada interface de chat ao painel.

---

## 3. Convenções gerais de uso de IA

- Os prompts apresentados neste documento são resumos representativos, não transcrições completas.
- O código deve ser validado com testes e verificações do projeto; uma sugestão da IA não é, por si só, prova de funcionamento.
- Credenciais, tokens e segredos reais não devem ser incluídos em prompts, arquivos versionados ou exemplos públicos.
- Os resultados de testes são registrados com seu escopo. Uma porcentagem de cobertura de módulos selecionados não deve ser apresentada como cobertura total da aplicação.
- Limitações conhecidas devem permanecer documentadas até que a implementação e os testes confirmem sua resolução.
