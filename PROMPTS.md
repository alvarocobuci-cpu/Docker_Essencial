# PROMPTS.md — Aula 4
## CRUD da API Principal com Django REST Framework

Este arquivo registra os principais prompts utilizados durante o desenvolvimento da Aula 4, as etapas realizadas com apoio de IA e as intervenções manuais feitas no projeto.

---

## 1. Objetivo da atividade

Desenvolver uma API REST utilizando Django REST Framework, integrada ao ambiente Docker e ao PostgreSQL já utilizado na Aula 3.

A atividade foi realizada aproveitando a estrutura do projeto `Docker_Essencial`, mantendo o código da Aula 3 e adaptando a aplicação para Django REST Framework.

---

## 2. Tecnologias utilizadas

- Python 3.12
- Django 5.2.6
- Django REST Framework 3.16.1
- PostgreSQL 16
- Docker
- Docker Compose
- Postman / Django REST Framework Browsable API

---

## 3. Principais prompts utilizados

### Prompt 1 — Adaptação do projeto da Aula 3

> Quero aproveitar o projeto da Aula 3 com Docker e PostgreSQL para desenvolver a Aula 4 utilizando Django REST Framework, sem criar outro projeto do zero.

### Prompt 2 — Configuração do Django

> Como configurar o Django dentro do Docker e integrar o Django REST Framework ao projeto existente?

### Prompt 3 — PostgreSQL

> Como configurar o Django para utilizar o PostgreSQL já existente no Docker Compose?

### Prompt 4 — Criação dos modelos

> Criar os modelos Category e Item utilizando Django ORM, com relacionamento entre eles e campos adequados para a API.

### Prompt 5 — Serializers

> Criar ModelSerializers para Category e Item, incluindo validações para os campos recebidos pela API.

### Prompt 6 — CRUD

> Criar ModelViewSets para Category e Item utilizando Django REST Framework.

### Prompt 7 — Rotas

> Configurar DefaultRouter para disponibilizar os endpoints da API em /api/v1/.

### Prompt 8 — Testes

> Testar os endpoints CRUD e verificar os códigos HTTP 200, 201, 204, 400 e 404.

### Prompt 9 — Documentação

> Organizar a coleção de testes do Postman e registrar as etapas realizadas no PROMPTS.md.

---

## 4. Desenvolvimento realizado

### 4.1 Configuração do ambiente

O projeto da Aula 3 foi reutilizado.

O Dockerfile foi adaptado para executar o Django:

```text
python app/manage.py runserver 0.0.0.0:8000