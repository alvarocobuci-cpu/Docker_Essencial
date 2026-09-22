# Template de Prompts - Aula 5

## Objetivo

Este arquivo apresenta um modelo para padronizar a utilização de inteligência artificial generativa durante o desenvolvimento do microsserviço de inventário.

## Estrutura do Prompt

### 1. Contexto

Descrever brevemente o projeto, a tecnologia utilizada e a funcionalidade que será desenvolvida.

### 2. Requisitos

Informar claramente o que deve ser criado ou alterado.

Exemplo:

- Criar um microsserviço utilizando FastAPI.
- Utilizar modelos Pydantic.
- Aplicar tipagem estática.
- Criar validações nos campos.
- Implementar as rotas mínimas necessárias.
- Integrar o serviço ao Docker Compose.

### 3. Restrições

Informar o que não deve ser implementado nesta etapa.

Exemplo:

- Não criar banco de dados.
- Não criar modelos relacionais.
- Não implementar autenticação.
- Não utilizar JWT.
- Não adicionar Redis ou mensageria.
- Não antecipar funcionalidades de aulas futuras.

### 4. Formato de Saída

Informar como a resposta da IA deve ser apresentada.

Exemplo:

- Apresentar os arquivos completos.
- Informar o caminho de cada arquivo.
- Explicar as alterações realizadas.
- Utilizar código compatível com Python 3.12.
- Manter o código simples e compatível com o escopo da atividade.

## Exemplo de Prompt

> Estou desenvolvendo um microsserviço complementar de estoque utilizando FastAPI e Python 3.12.
>
> Crie o esqueleto do serviço utilizando modelos Pydantic, tipagem estática e validação dos dados.
>
> O serviço deve possuir endpoints para health check e consulta de estoque.
>
> Utilize respostas tipadas e documentação automática do FastAPI.
>
> O serviço será executado em Docker Compose.
>
> Restrições:
> - Não utilizar banco de dados nesta etapa.
> - Não implementar autenticação ou JWT.
> - Não utilizar Redis.
> - Não implementar mensageria.
>
> Apresente os arquivos completos, seus respectivos caminhos e explique brevemente as alterações.

## Validação da Resposta da IA

Após utilizar uma sugestão gerada por IA, verificar:

- Se o código atende aos requisitos da atividade.
- Se a tipagem está correta.
- Se as validações funcionam.
- Se os códigos HTTP estão adequados.
- Se as rotas estão acessíveis.
- Se a documentação `/docs` funciona.
- Se nenhuma funcionalidade de aulas futuras foi adicionada.

## Intervenção Manual

As sugestões da IA devem ser revisadas e testadas manualmente antes de serem incorporadas ao projeto.

Durante a Aula 5, foram realizadas validações manuais através do Docker Compose e da documentação interativa do FastAPI.

## Escopo da Aula 5

Esta etapa contempla somente:

- FastAPI.
- Pydantic.
- Tipagem estática.
- Validação de dados.
- Rotas do microsserviço de inventário.
- Documentação automática.
- Integração com Docker Compose.

Banco de dados e autenticação não fazem parte desta etapa.