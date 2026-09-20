# PROMPTS.md

## Objetivo

Este arquivo registra os principais prompts utilizados durante o desenvolvimento da infraestrutura Docker da Aula 3.

## 1. Criação do Dockerfile

### Prompt utilizado

> Crie um Dockerfile para uma aplicação Python Flask simples utilizando multistage build, cache de dependências e execução com usuário não-root. A aplicação deve utilizar a porta 8000 e possuir uma etapa de build separada da etapa de runtime.

### Resultado

Foi criado um Dockerfile com duas etapas:

- `builder`: responsável pela instalação das dependências;
- `runtime`: responsável pela execução da aplicação.

Também foi utilizado cache do pip durante a instalação das dependências.

---

## 2. Revisão do Dockerfile

### Prompt utilizado

> Revise este Dockerfile verificando se ele utiliza multistage build, cache eficiente de dependências e usuário não-root. Identifique possíveis problemas e sugira melhorias mantendo o projeto simples e dentro do escopo da Aula 3.

### Resultado

A estrutura foi revisada para garantir:

- separação entre build e runtime;
- aproveitamento do cache do pip;
- execução da aplicação com o usuário `appuser`;
- exposição da porta 8000.

---

## 3. Criação do Docker Compose

### Prompt utilizado

> Crie um docker-compose.yml simples para uma API Flask e um banco PostgreSQL. A API deve ser construída a partir de um Dockerfile e o banco deve utilizar variáveis de ambiente essenciais, volume persistente e healthcheck. A API deve aguardar o banco ficar saudável antes de iniciar.

### Resultado

Foi criado um Compose com dois serviços:

- `api`;
- `db`.

Foi configurado um healthcheck para o PostgreSQL e uma dependência entre os serviços.

---

## 4. Correções e validações

Durante a execução foram realizadas validações práticas do ambiente.

Foi verificado que:

- a API iniciou corretamente;
- o PostgreSQL iniciou corretamente;
- a rota `/health` respondeu com status `ok`;
- a conexão com o banco foi identificada como `connected`;
- o container da API executou com o usuário não-root `appuser`;
- o histórico da imagem foi analisado com `docker history`;
- os logs dos containers foram analisados com `docker compose logs`.

## 5. Conceitos aplicados

Os principais conceitos utilizados foram:

- Dockerfile;
- imagens e containers;
- multistage build;
- cache de dependências;
- usuário não-root;
- Docker Compose;
- variáveis de ambiente;
- healthcheck;
- volumes;
- logs;
- health check da aplicação.