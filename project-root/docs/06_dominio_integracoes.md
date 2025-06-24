# Domínio: Integrações

---

## Objetivo

Gerenciar integrações externas (e-mail, WhatsApp, pagamentos, analytics, etc) e configuração dinâmica de chaves/API keys.

---

## Regras de Negócio

- Toda integração configurada via painel.
- Chaves criptografadas e nunca hardcoded.
- Validação de conexão/teste obrigatório.
- Permite múltiplas integrações por categoria.
- Logs de uso e erro das integrações.

---

## Endpoints

- `GET /api/integrations`
- `POST /api/integrations`

---

## Contratos

- Integração: id, tipo, chave, status, data de criação.
- Log: integraçãoId, data, evento, status.

---

## Integrações

- Com automação, analytics e demais domínios.
- Painel administrativo para gestão.

---

## Observações

- Segregação de acesso por role.
- Toda alteração registrada em log.
