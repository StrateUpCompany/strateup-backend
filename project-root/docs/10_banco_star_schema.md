# Banco de Dados: Operacional e Star Schema

---

## Objetivo

Definir a modelagem relacional para operações diárias e Star Schema para analytics e BI.

---

## Tabelas Operacionais

- `funnels`, `funnel_steps`
- `leads`, `diagnostic_answers`
- `users`, `roles`
- `automations`, `automation_steps`
- `integrations`

---

## Star Schema (Analytics)

- Fatos: `fact_interactions`, `fact_sales`
- Dimensões: `dim_customer`, `dim_funnel`, `dim_product`, `dim_page`, `dim_channel`, `dim_date`

---

## Regras

- Toda tabela operacional prioriza desempenho, integridade e rastreabilidade.
- Star Schema garante performance e flexibilidade analítica.
- Tabelas de eventos/fatos só recebem dados via orquestração de negócio.

---

## Integração

- Operacional alimenta o Star Schema de acordo com regras definidas em `11_fluxos_negocio.md`.

---

## Observações

- Alterações de estrutura exigem atualização da documentação e migração controlada.
