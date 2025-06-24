# Clareza Total - Backend

# Plano de Backend StrateUp — Lógica de Negócio Aplicada

---

## 1. Princípios Inegociáveis

- **Cada endpoint, tabela e regra de negócio deriva de uma necessidade clara do frontend e dos fluxos de negócio mapeados.**
- **Nada de endpoints ou tabelas “para testar”. Tudo tem propósito, contrato e validação.**
- **A lógica de negócio é centralizada em services/domain layer, nunca espalhada em controllers ou actions.**
- **Cada fluxo (lead, funil, automação, venda, analytics) será explicitamente mapeado, documentado e validado.**
- **Star Schema será a base para analytics e rastreio de eventos.**

---

## 2. Módulos e Responsabilidades

### 2.1. FUNIL
- CRUD de Funis e Etapas.
- Regras: reordenação, ativação/desativação de etapas, associação de páginas/posts, histórico de movimentação de leads no funil.

### 2.2. LEAD/DIAGNÓSTICO
- CRUD de Leads.
- Deduplicação (base e-mail).
- Registro de histórico de diagnósticos (pontuação, dor, temperatura).
- Regra: Um lead pode ter múltiplos diagnósticos, com histórico e score para cada, mas e-mail é único.

### 2.3. AUTOMAÇÃO
- CRUD de sequências e automações.
- Gatilhos: ao preencher diagnóstico, ao avançar etapa, ao comprar, ao não abrir e-mail, etc.
- Lógica de fallback (ex: não abriu e-mail → tentar WhatsApp).
- Orquestração do envio no melhor horário (“horário preferencial” do lead).

### 2.4. DASHBOARD/ANALYTICS
- KPIs: leads, conversão, vendas, LTV, CAC, ROI, funil visual.
- Registro de cada evento relevante (lead criado, diagnóstico, etapa avançada, compra, abertura de e-mail, clique no WhatsApp).
- Cálculo e atualização automática de analytics.

### 2.5. AUTH/USUÁRIOS
- Login/logout, RBAC, sessão.
- Controle de permissões via roles (admin, gerente, operador).

### 2.6. INTEGRAÇÕES
- Cadastro/edição de chaves de API (e-mail, WhatsApp, pagamentos, GTM, Pixel, etc).
- Nenhuma configuração será hardcoded.

---

## 3. Star Schema e Banco de Dados

### 3.1. Tabelas Operacionais (CRUD)
- funnels, funnel_steps, leads, diagnostic_answers, users, roles, automations, automation_steps, integrations

### 3.2. Tabelas Analíticas (Star Schema)
- fact_interactions (eventos: lead, diagnóstico, etapa, compra, e-mail, whatsapp)
- fact_sales
- dim_customer, dim_funnel, dim_product, dim_page, dim_channel, dim_date

---

## 4. Endpoints RESTful (Contratos Fixos)

### FUNIS
- `GET /api/funnels` — lista funis
- `POST /api/funnels` — cria funil
- `GET /api/funnels/:id` — detalhes (inclui etapas)
- `PUT /api/funnels/:id` — edita funil
- `DELETE /api/funnels/:id` — remove funil
- `POST /api/funnels/:funnelId/steps` — cria etapa
- `PUT /api/funnels/:funnelId/steps/:stepId` — edita etapa
- `DELETE /api/funnels/:funnelId/steps/:stepId` — remove etapa
- `POST /api/funnels/:funnelId/steps/reorder` — reordena etapas

### LEADS/DIAGNÓSTICO
- `GET /api/leads`
- `POST /api/leads`
- `GET /api/leads/:id`
- `PUT /api/leads/:id`
- `DELETE /api/leads/:id`
- `POST /api/leads/:leadId/diagnostic` — submete diagnóstico, calcula score, salva histórico

### AUTOMAÇÃO
- `GET /api/automations`
- `POST /api/automations`
- `POST /api/automations/trigger` — dispara automação manualmente

### DASHBOARD/ANALYTICS
- `GET /api/dashboard/kpis`
- `GET /api/dashboard/funnels`
- `GET /api/dashboard/insights`

### AUTH/USUÁRIOS
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### INTEGRAÇÕES
- `GET /api/integrations`
- `POST /api/integrations`

---

## 5. Fluxos de Negócio (Regra, Não Exemplo)

- **Captação de Lead:**  
  - Recebe dados do lead.  
  - Valida e deduplica (base e-mail).  
  - Salva lead e evento em analytics.  
  - Se diagnóstico, processa score, dor, temperatura e histórico.  
  - Inscreve em automação correta (base temperatura/dor).  
  - Retorna lead, status, automação acionada.

- **Movimentação no Funil:**  
  - Avanço de etapa registra evento no fact_interactions.  
  - Pode acionar automação se houver.  
  - Atualiza status de lead no funil.

- **Automação:**  
  - Disparada por evento (diagnóstico, etapa, compra, etc).  
  - Envia via canal preferencial.  
  - Se não aberto, fallback para outro canal.  
  - Registra evento de entrega e abertura/ação.

- **Compra:**  
  - Recebe confirmação de pagamento (webhook).  
  - Atualiza status do lead para cliente.  
  - Aciona automação pós-venda.  
  - Atualiza analytics (fact_sales).

---

## 6. Como Garantir a Aplicação da Lógica

- **Cada endpoint deve chamar obrigatoriamente o service/domain layer do seu domínio.**
- **Cada regra de negócio (deduplicação, score, fallback, etc) será função dedicada, testada e documentada.**
- **Não será permitido lógica “direto no controller” — sempre via orchestration service.**
- **Analytics e audit log sempre atualizados a cada evento relevante.**
- **Painel de integrações obrigatório para configuração dinâmica de chaves.**

---

## 7. Governança

- **Cada rota, tabela, regra e serviço será documentado e versionado.**
- **Testes unitários para regras críticas.**
- **Todo fluxo de negócio documentado, sem espaço para dúvida ou “interpretação”.**

---

## 8. Ordem de Implementação

1. Banco de dados (migrations)
2. Services/domain layer (regra de negócio centralizada)
3. API layer (endpoints RESTful, contratos fixos)
4. Integração com frontend
5. Painel de integrações/configurações
6. Testes e documentação

---

**Com este blueprint, o backend será 100% alinhado à lógica de negócio, sem espaço para improviso ou incerteza.**  
Se quiser, posso gerar os arquivos iniciais de migration, contracts/types, ou serviços para um domínio específico — só pedir!