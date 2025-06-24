# Visão Geral — Backend StrateUp

---

## Objetivo

Desenvolver um backend robusto, escalável e auditável para a plataforma StrateUp, alinhado aos princípios de arquitetura limpa, separação de domínios, centralização da lógica de negócio e rastreabilidade total dos fluxos de marketing, vendas e automação.

---

## Princípios Fundamentais

- **Domínios separados:** Cada módulo (funis, leads, automação, analytics, auth, integrações) é isolado em regras, banco e endpoints.
- **Lógica de negócio centralizada:** Nenhuma regra é implementada em controller ou endpoint, apenas em services/domain layer.
- **Persistência confiável:** Banco relacional (Postgres), modelagem Star Schema para analytics, tabelas operacionais para CRUD.
- **Rastreabilidade:** Todos os eventos relevantes são registrados para BI, auditoria e evolução de produto.
- **Segurança e governança:** Autenticação forte, RBAC, logs de acesso/erro, validação de payload.
- **Integrações dinâmicas:** Configurações e chaves de API sempre via painel, nunca hardcoded.
- **Documentação viva:** Todo fluxo, regra, contrato e decisão está registrado nos arquivos desta pasta e deve ser atualizado em cada evolução.

---

## Responsabilidades dos Módulos

- **Funis:** Gerenciar funis de marketing/vendas, etapas, reordenação, histórico e templates.
- **Leads/Diagnóstico:** Captura, qualificação, deduplicação, histórico de diagnóstico e segmentação.
- **Automação:** Orquestração e execução de sequências multicanal, lógica de fallback, integração com eventos de negócio.
- **Analytics/Dashboard:** Cálculo de KPIs, registros de eventos, star schema, funil visual, recomendações automáticas.
- **Auth/Usuários:** Gerenciamento de usuários, autenticação, controle de acesso, RBAC.
- **Integrações:** Cadastro, validação e manutenção de chaves de API e integrações externas.

---

## Fluxo Macro

1. **Lead capturado** → diagnóstico → qualificação → entrada em funil → automação → oportunidade/venda → pós-venda/onboarding → analytics.
2. **Eventos de usuário, marketing e vendas** registrados em star schema para BI, dashboard e insights.
3. **Automações** disparadas conforme regras de negócio, com monitoria de entrega, abertura e fallback.
4. **Painel administrativo** controla funis, leads, automações, produtos, integrações e analytics.

---

## Arquitetura de Alto Nível

- **API Layer:** Endpoints RESTful padronizados, versionados, sem lógica de negócio direta.
- **Services/Domain Layer:** Toda regra de negócio, validação, orquestração de fluxos.
- **Persistence Layer:** Acesso ao banco relacional, queries otimizadas, migrations versionadas.
- **Analytics Layer:** Star schema, ingestão de eventos, processamento de KPIs.
- **Integration Layer:** Comunicação com fornecedores externos (email, WhatsApp, pagamentos, etc), parametrizável via painel.

---

## Governança

- Toda funcionalidade, alteração ou novo fluxo deve ser refletido na documentação antes do desenvolvimento.
- Nenhuma funcionalidade entra em produção sem documentação, teste e validação de regra de negócio.
- O conhecimento do produto reside nesta pasta; qualquer dúvida de arquitetura ou negócio deve ser resolvida aqui.

---

## Referência

Para detalhes de cada domínio, endpoints, banco e fluxos, consulte os arquivos específicos desta pasta conforme o índice aprovado.
