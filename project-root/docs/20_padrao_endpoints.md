# Padrão de Endpoints RESTful

---

## Objetivo

Garantir uniformidade, clareza, versionamento e previsibilidade em todos os endpoints da API.

---

## Convenções

- Todos os endpoints seguem o padrão RESTful: recursos, métodos HTTP corretos, pluralização.
- Versão da API obrigatória no path: `/api/v1/`.
- Respostas sempre em JSON.
- Mensagens de erro padronizadas, com códigos claros e detalhes.
- Nenhum endpoint expõe lógica interna ou dados sensíveis.
- Paginação, filtro e ordenação disponíveis em endpoints de listagem.

---

## Métodos e Rotas

- `GET /api/v1/:resource` — Listar recursos
- `POST /api/v1/:resource` — Criar recurso
- `GET /api/v1/:resource/:id` — Detalhe do recurso
- `PUT /api/v1/:resource/:id` — Atualizar recurso
- `DELETE /api/v1/:resource/:id` — Remover recurso

---

## Padrão de Erros

- 400: Erro de validação ou dados inválidos
- 401: Não autenticado
- 403: Sem permissão
- 404: Não encontrado
- 409: Conflito ou duplicidade
- 422: Erro de regra de negócio
- 500: Erro interno

---

## Exemplo de resposta de erro

```json
{
  "error": {
    "code": 422,
    "message": "Lead já existe",
    "details": {}
  }
}
```

---

## Observações

- Nunca retornar stacktrace ou erro bruto para o cliente.
- Toda resposta deve ter contrato e estrutura documentados.
