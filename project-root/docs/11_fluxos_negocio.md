# Fluxos de Negócio

---

## Objetivo

Orquestrar e documentar todos os fluxos críticos do sistema, do lead ao pós-venda, passando por automação e analytics.

---

## Fluxos Principais

- Captação de Lead: cadastro, deduplicação, diagnóstico, segmentação.
- Movimentação em Funil: avanço de etapa, histórico, gatilho de automação.
- Disparo de Automação: evento, fallback, tracking.
- Conversão/Venda: confirmação externa, atualização de status, pós-venda.
- Analytics: registro de eventos, cálculo de KPIs, geração de insights.

---

## Regras

- Cada fluxo tem início, processamento e fim bem definidos.
- Toda transição relevante gera evento registrado para auditoria e BI.
- Orquestração ocorre sempre na camada de service/domain, nunca no controller.

---

## Integração

- Todos os domínios contribuem para os fluxos, com contratos claros e rastreáveis.

---

## Observações

- Nenhum fluxo pode ser alterado sem atualização deste documento.
