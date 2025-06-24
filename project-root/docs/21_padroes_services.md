# Padrão de Implementação Service/Domain Layer

---

## Objetivo

Centralizar toda lógica de negócio, regras, orquestração e integrações em serviços de domínio, nunca em controllers/endpoints.

---

## Convenções

- Cada domínio possui seu próprio service, isolado dos demais.
- Regras de negócio, validação, deduplicação, orquestração de fluxos e integrações externas sempre no service.
- Controllers só recebem/parsing de request e delegam para services.
- Services são testáveis de forma isolada.
- Nenhum acesso direto ao banco fora do service.

---

## Estrutura Recomendada

- `/services/FunilService.ts`
- `/services/LeadService.ts`
- `/services/AutomacaoService.ts`
- `/services/AnalyticsService.ts`
- `/services/AuthService.ts`
- `/services/IntegracaoService.ts`

---

## Observações

- Toda alteração de regra exige ajuste no respectivo service e documentação.
- Services devem ser agnósticos de framework (podem ser migrados de stack).
