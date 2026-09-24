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

---

## 3. Estrutura geral do projeto

Atualmente, o projeto possui uma estrutura semelhante a esta:

```text
Docker_Essencial/

├── app/
│   ├── aula4api/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── permissions.py
│   │   ├── serializers.py
│   │   ├── tests.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── inventory/
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── services.py
│   │   ├── schemas.py
│   │   ├── main.py
│   │   ├── transaction_test.py
│   │   └── performance_test.py
│   │
│   ├── flask_app_aula3.py
│   └── manage.py
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 2eda063b9f92_create_inventory_items.py
│
├── postman/
│   └── Aula4_DRF_Collection.json
│
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .dockerignore
├── .gitignore
├── PROMPTS.md
└── README.md