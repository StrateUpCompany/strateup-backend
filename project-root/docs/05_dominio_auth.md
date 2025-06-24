# Domínio: Auth/Usuários

---

## Objetivo

Gerenciar autenticação, autorização, usuários e controle de acesso ao sistema.

---

## Regras de Negócio

- Autenticação via e-mail/senha e/ou provedores externos.
- RBAC: roles como admin, gerente, operador.
- Sessão segura, expiração e revogação.
- Logs de acesso e tentativas.
- Cadastro e gerenciamento de usuários restrito por permissão.

---

## Endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

---

## Contratos

- Usuário: id, nome, e-mail, role, status.
- Sessão: token, expiração, usuárioId.

---

## Integrações

- Com todos módulos via controle de permissão.
- Logs para auditoria.

---

## Observações

- Segurança é prioridade: criptografia, validação, auditoria.
