# Padrão de Validação e Contratos

---

## Objetivo

Garantir integridade, segurança e clareza nos dados trafegados entre frontend, backend e integrações.

---

## Convenções

- Toda entrada de dados (payload) validada via schema (ex: Zod, Yup, Joi).
- Contratos de dados versionados e compartilhados quando possível.
- Validação ocorre antes de qualquer regra de negócio ou persistência.
- Mensagens de erro claras, detalhadas e padronizadas.
- Erros de contrato/validação nunca expõem stacktrace.

---

## Contratos

- Todos os domínios possuem arquivos de contratos/types.
- Contratos incluem: campos obrigatórios, tipos, enums, regras de formato.

---

## Observações

- Mudanças em contratos exigem atualização da documentação e testes.
- Validação é obrigatória em endpoints, services e integrações.
