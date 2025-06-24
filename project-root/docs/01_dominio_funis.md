# Domínio: Funis

---

## Objetivo

Gerenciar funis de marketing e vendas, etapas, movimentação de leads e histórico de progresso.

---

## Regras de Negócio

- Cada funil possui etapas ordenadas.
- Etapas podem ser criadas, editadas, removidas e reordenadas.
- Leads podem ser movidos entre etapas.
- Histórico de movimentação é registrado para cada lead.
- Não é permitido excluir etapas se houver leads ativos nelas.
- Templates de funis podem ser aplicados para replicação rápida.

---

## Endpoints

- `GET /api/funnels`
- `POST /api/funnels`
- `GET /api/funnels/:id`
- `PUT /api/funnels/:id`
- `DELETE /api/funnels/:id`
- `POST /api/funnels/:funnelId/steps`
- `PUT /api/funnels/:funnelId/steps/:stepId`
- `DELETE /api/funnels/:funnelId/steps/:stepId`
- `POST /api/funnels/:funnelId/steps/reorder`

---

## Contratos

- Funil: id, nome, descrição, etapas, data de criação.
- Etapa: id, funilId, título, tipo, ordem, data de criação.
- Histórico: leadId, funilId, etapaId, data, ação.

---

## Integrações

- Integração com módulo de leads para movimentação.
- Integração com automações ao avançar etapas.

---

## Observações

- Toda mudança estrutural em funis/etapas deve ser registrada em histórico.
- Nenhuma lógica de negócio implementada em controller.
