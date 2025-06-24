# Domínio: Leads/Diagnóstico

---

## Objetivo

Gerenciar leads, suas informações, diagnósticos, qualificação, histórico e segmentação.

---

## Regras de Negócio

- Lead é identificado por e-mail único.
- Pode ter múltiplos diagnósticos, cada um com score, dor, temperatura.
- Histórico completo de interações.
- Deduplicação obrigatória no cadastro.
- Segmentação dinâmica por critérios de diagnóstico.
- Leads podem ser associados a funis e etapas.

---

## Endpoints

- `GET /api/leads`
- `POST /api/leads`
- `GET /api/leads/:id`
- `PUT /api/leads/:id`
- `DELETE /api/leads/:id`
- `POST /api/leads/:leadId/diagnostic`

---

## Contratos

- Lead: id, nome, e-mail, telefone, temperatura, score, data de criação.
- Diagnóstico: leadId, respostas, score, data.
- Histórico: leadId, ação, data.

---

## Integrações

- Com funis (movimentação).
- Com automações (disparo pós-diagnóstico).
- Com analytics (registro de eventos).

---

## Observações

- Toda interação relevante é registrada em histórico e analytics.
- Não existe lógica de negócio fora do service/domain layer.
