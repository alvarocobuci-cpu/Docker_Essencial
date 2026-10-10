# SynapseShop - Checklist do Integrador Externo

## 1. URLs de ambiente

Ambiente local com Docker Compose:

- Django REST Framework: http://localhost:8000
- Contrato OpenAPI combinado: http://localhost:8000/openapi.yaml
- Swagger UI: http://localhost:8000/docs/
- ReDoc: http://localhost:8000/redoc/
- FastAPI de inventario: http://localhost:8001
- Swagger UI do inventario: http://localhost:8001/docs
- ReDoc do inventario: http://localhost:8001/redoc
- OpenAPI JSON do inventario: http://localhost:8001/openapi.json

Dentro da rede Docker, os nomes dos servicos sao api:8000 e inventory:8001.

## 2. Autenticacao

1. Enviar POST /api/token/ com username e password.
2. Guardar o campo access retornado.
3. Enviar o token nas rotas protegidas usando Authorization: Bearer <access-token>.
4. Renovar o token usando POST /api/token/refresh/ com o campo refresh.

Os endpoints de categorias e itens requerem usuario autenticado que pertença ao grupo admin.
O endpoint de criacao de pedidos requer autenticacao JWT, mas nao exige o grupo admin.

Nunca versionar senhas, access tokens ou refresh tokens em arquivos compartilhados.

## 3. Catalogo Django

As rotas de catalogo usam o prefixo /api/v1/.

Categorias:
- GET /api/v1/categories/
- POST /api/v1/categories/
- GET, PUT, PATCH e DELETE /api/v1/categories/{id}/

Itens:
- GET /api/v1/items/
- POST /api/v1/items/
- GET, PUT, PATCH e DELETE /api/v1/items/{id}/

Listagens suportam:
- page: numero da pagina; tamanho padrao 10
- category: filtro pelo identificador da categoria
- search: busca por nome ou descricao do item
- ordering: id, name, price ou quantity; prefixe com menos para ordem decrescente

A resposta paginada do Django REST Framework inclui count, next, previous e results.

## 4. Pedidos e idempotencia

POST /api/v1/pedidos/ requer:
- Authorization: Bearer <access-token>
- Idempotency-Key: chave unica do cliente
- Corpo JSON com item_id e quantidade

Uma repeticao com a mesma chave pode retornar HTTP 202 com duplicate=true.
A reutilizacao da chave com conteudo diferente pode retornar HTTP 409.
Falhas de dependencias ou de publicacao podem retornar HTTP 503.

X-Trace-Id aparece na especificacao como convencao reservada, mas o codigo atual ainda nao le nem propaga esse cabecalho. Nao dependa dele para rastreamento ate que a implementacao exista.

## 5. API de inventario FastAPI

A API de inventario usa a porta local 8001:
- GET /health
- GET /cache/metrics
- GET /inventory
- POST /inventory
- GET /inventory/{item_id}
- PUT /inventory/{item_id}/quantity?quantity=12
- DELETE /inventory/{item_id}

No estado atual, essa API nao exige JWT e nao implementa paginacao, filtros ou ordenacao na lista de inventario.

## 6. Limites de utilizacao

Configuracao identificada no Django REST Framework:
- Anonimo: 10 requisicoes por minuto
- Autenticado: 30 requisicoes por minuto

Clientes externos devem tratar HTTP 429 e aplicar espera progressiva antes de novas tentativas.
Os limites podem ser alterados pela configuracao da aplicacao.

## 7. Formato de erros

A aplicacao retorna erros JSON nos formatos atuais do Django REST Framework, SimpleJWT e FastAPI.
O esquema ErrorSchema do contrato descreve esses formatos de forma abrangente; a aplicacao ainda nao padroniza todas as respostas segundo RFC 7807 e nao deve ser tratada como emitindo application/problem+json.

Codigos observados/documentados incluem:
- 400: corpo ou regra de negocio invalida
- 401: autenticacao ausente ou invalida
- 403: usuario sem permissao
- 404: recurso nao encontrado
- 409: conflito de idempotencia
- 429: limite de utilizacao excedido
- 503: dependencia indisponivel
- 422: validacao de parametros da API FastAPI

## 8. Headers documentados

- Authorization: Bearer JWT nas rotas Django protegidas.
- Idempotency-Key: obrigatorio na criacao de pedidos.
- X-Trace-Id: convencao futura documentada, ainda nao implementada.

## 9. Postman

Importar os arquivos:
- postman/SynapseShop_Aula13.postman_collection.json
- postman/environments/SynapseShop_Local.postman_environment.json

Selecionar o ambiente SynapseShop - Local.
Substituir os valores placeholders pelas credenciais locais validas.
Executar primeiro o login de administrador para guardar o token.
Executar o login de usuario comum apenas com uma conta que nao pertença ao grupo admin.

As requisicoes de exclusao sao destrutivas. Execute-as apenas com dados de teste.

## 10. Versionamento e alteracoes

O prefixo /api/v1/ identifica a versao corrente da API Django de catalogo e pedidos.
Alteracoes incompativeis devem ser avaliadas para uma nova versao de rota.
Alteracoes de contrato devem ser registradas no CHANGELOG.md e validadas pelo Redocly CLI.
Atualizar colecao Postman e exemplos quando contratos ou parametros forem alterados.

## 11. Validacao local

Iniciar os servicos:
docker compose up --build -d api inventory

Validar a especificacao:
npx --yes @redocly/cli lint ./docs/openapi.yaml

Verificar o estado dos servicos:
docker compose ps


## 12. Convencoes ainda nao suportadas

O contrato documenta os parametros que a aplicacao aceita hoje. As convencoes abaixo foram consideradas no plano de padronizacao, mas nao devem ser enviadas como se fossem funcionalidade implementada:

- limit: nao configura o tamanho da pagina. O Django usa PAGE_SIZE=10.
- nextCursor: nao ha paginacao por cursor; a resposta atual usa count, next, previous e results.
- status: nao existe filtro de status nas listagens de catalogo documentadas.
- sort=createdAt:desc: o Django aceita ordering com campos id, name, price e quantity.
- X-Trace-Id: ainda nao e processado nem propagado pela aplicacao.

Para utilizar esses parametros, sera necessaria uma alteracao futura no codigo e nos testes, acompanhada de uma nova versao do contrato.
