# Domínio: Analytics/Dashboard

---

## Objetivo

Registrar, calcular e disponibilizar KPIs, métricas de funil, eventos e insights para tomada de decisão.

---

## Regras de Negócio

- Todo evento relevante (lead, diagnóstico, etapa, automação, venda) é registrado.
- KPIs principais: leads, conversão, vendas, LTV, CAC, ROI.
- Funil visual mostra progresso, gargalos e taxas.
- Recomendações automáticas baseadas em dados históricos.
- Dados estruturados via Star Schema para BI.

---

## Endpoints

- `GET /api/dashboard/kpis`
- `GET /api/dashboard/funnels`
- `GET /api/dashboard/insights`

---

## Contratos

- Evento: id, tipo, entidade, data, valor.
- KPI: nome, valor, período, atualização.

---

## Integrações

- Com todos os domínios para ingestão de eventos.
- Com frontend para dashboards e relatórios.

---

## Observações

- Toda consulta retorna dados agregados e detalhados.
- Modelagem Star Schema é obrigatória.
