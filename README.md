## Aula 6 — Modelagem Relacional, Índices e Migrações

Nesta etapa, o projeto foi ampliado para utilizar persistência de dados no PostgreSQL por meio do SQLAlchemy e do Alembic.

### Modelagem do banco de dados

Foi criada a entidade `InventoryItem`, responsável pelo armazenamento dos itens do estoque.

A tabela `inventory_items` possui os seguintes campos:

- `id`: identificador único do item.
- `name`: nome do produto.
- `quantity`: quantidade disponível em estoque.
- `minimum_quantity`: quantidade mínima definida para o estoque.

Foram utilizadas restrições de integridade para impedir valores negativos nos campos `quantity` e `minimum_quantity`.

### Índices

Foi criado um índice no campo `name`:

`ix_inventory_items_name`

O objetivo é melhorar a eficiência de consultas que utilizem o nome do item.

### Migrações com Alembic

O Alembic foi configurado para controlar a evolução do schema da tabela `inventory_items`.

A primeira migração criou:

- tabela `inventory_items`;
- chave primária;
- restrição para quantidade não negativa;
- restrição para quantidade mínima não negativa;
- índice no campo `name`.

A migração foi aplicada com sucesso utilizando:

```bash
alembic upgrade head