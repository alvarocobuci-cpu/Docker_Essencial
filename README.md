# Aula 4 - CRUD da API Principal com Django REST Framework

## Objetivo

Este projeto foi desenvolvido como parte da Aula 4 do curso, com foco na criação de uma API REST utilizando Django REST Framework.

A aplicação foi desenvolvida aproveitando a estrutura Docker da Aula 3 e integrada ao PostgreSQL por meio do Docker Compose.

Nesta etapa foram implementados modelos, serializers, ViewSets e rotas para disponibilizar operações completas de CRUD para categorias e itens.

## Tecnologias utilizadas

- Python 3.12
- Django 5.2.6
- Django REST Framework 3.16.1
- PostgreSQL 16
- Docker
- Docker Compose
- Postman

## Estrutura do projeto

```text
Docker_Essencial/

├── app/
│   ├── aula4api/
│   │   ├── migrations/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   └── views.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── flask_app_aula3.py
│   └── manage.py
│
├── postman/
│   └── Aula4_DRF_Collection.json
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── requirements.txt
├── README.md
└── PROMPTS.md