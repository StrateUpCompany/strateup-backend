# Domínio: Automação

---

## Objetivo

Gerenciar automações multicanal (e-mail, WhatsApp, etc), sequências, gatilhos e execução baseada em eventos ou regras de negócio.

---

## Regras de Negócio

- Automação é composta por etapas, canais e regras de envio.
- Gatilhos: diagnóstico, avanço de etapa, compra, abandono, etc.
- Lógica de fallback: se canal principal não funcionar, tenta próximo.
- Horário de disparo considera preferência do lead.
- Registro de toda execução e status (enviado, entregue, aberto, clicado, etc).

---

## Endpoints

- `GET /api/automations`
- `POST /api/automations`
- `POST /api/automations/trigger`

---

## Contratos

- Automação: id, nome, etapas, gatilhos, status.
- Execução: leadId, automacaoId, canal, status, data.

---

## Integrações

- Com leads e funis (gatilhos).
- Com integrações externas (provedores de e-mail, WhatsApp, etc).
- Com analytics (resultados e tracking).

---

## Observações

- Nenhuma configuração hardcoded.
- Toda execução registrada para auditoria.
