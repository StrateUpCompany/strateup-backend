# Blueprint Inicial Backend StrateUp

---

## 1. Mapeamento de Endpoints Esperados

### 1.1. FUNIS (`/funnels`)
- `GET /api/funnels` — Listar funis
- `GET /api/funnels/:id` — Detalhar funil (inclui etapas)
- `POST /api/funnels` — Criar funil
- `PUT /api/funnels/:id` — Editar funil
- `DELETE /api/funnels/:id` — Deletar funil

#### ETAPAS DO FUNIL
- `POST /api/funnels/:funnelId/steps` — Criar etapa
- `PUT /api/funnels/:funnelId/steps/:stepId` — Editar etapa
- `DELETE /api/funnels/:funnelId/steps/:stepId` — Remover etapa
- `POST /api/funnels/:funnelId/steps/reorder` — Reordenar etapas

---

### 1.2. LEADS/CRM (`/leads`)
- `GET /api/leads` — Listar leads
- `GET /api/leads/:id` — Detalhar lead
- `POST /api/leads` — Criar lead (ex: via diagnóstico ou captura)
- `PUT /api/leads/:id` — Editar lead
- `DELETE /api/leads/:id` — Remover lead

#### DIAGNÓSTICO
- `POST /api/leads/:leadId/diagnostic` — Submeter respostas de diagnóstico

---

### 1.3. DASHBOARD / ANALYTICS (`/dashboard`)
- `GET /api/dashboard/kpis` — Buscar KPIs globais (leads, conversão, vendas, LTV, CAC, ROI)
- `GET /api/dashboard/funnels` — Dados de conversão por funil/etapa
- `GET /api/dashboard/insights` — Recomendações automáticas

---

### 1.4. AUTOMAÇÃO / SEQUÊNCIAS (`/automations`)
- `GET /api/automations` — Listar automações/sequências
- `POST /api/automations` — Criar automação
- `POST /api/automations/trigger` — Disparar automação manualmente

---

### 1.5. AUTH/USUÁRIOS (`/auth`)
- `POST /api/auth/login` — Login
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Dados do usuário logado
- `POST /api/auth/register` — Cadastro (se aplicável)
- `GET /api/auth/roles` — Listar roles/permissões

---

### 1.6. INTEGRAÇÕES
- `GET /api/integrations` — Listar integrações conectadas
- `POST /api/integrations` — Salvar/editar chaves de API

---

## 2. Definição dos Schemas (Exemplo TypeScript)

```typescript name=types/index.ts
// Funil
export interface Funnel {
  id: string;
  name: string;
  description?: string;
  steps: FunnelStep[];
  createdAt: string;
}

export interface FunnelStep {
  id: string;
  funnelId: string;
  title: string;
  type: "diagnostic" | "capture" | "sales" | "thankyou" | "custom";
  order: number;
  pageId?: string;
}

// Lead
export interface Lead {
  id: string;
  name: string;
  email: string;
  phone?: string;
  temperature: "frio" | "morno" | "quente";
  score: number;
  createdAt: string;
  diagnostics?: DiagnosticAnswer[];
}

export interface DiagnosticAnswer {
  questionId: string;
  answer: string;
  points: number;
  submittedAt: string;
}

// Usuário
export interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "manager" | "user";
  createdAt: string;
}

// Dashboard KPI
export interface DashboardKPI {
  leads: number;
  conversionRate: number;
  sales: number;
  ltv: number;
  cac: number;
  roi: number;
  updatedAt: string;
}
```

---

## 3. Orquestração de Fluxos de Negócio

### Exemplo: Novo Lead cadastrado via Diagnóstico

**Fluxo:**
1. Recebe payload do formulário de diagnóstico (`POST /api/leads`)
2. Salva lead no banco (deduplicação por e-mail)
3. Salva respostas do diagnóstico e calcula score/temperatura
4. Salva evento em analytics (FactInteractions)
5. Inscreve lead em automação apropriada (baseado em temperatura)
6. Retorna dados completos para frontend (lead + diagnóstico + automação acionada)

---

## 4. Blueprint Inicial do Banco de Dados (Star Schema + Operacional)

- Tabelas principais:
  - `funnels`, `funnel_steps`
  - `leads`, `diagnostic_answers`
  - `users`, `roles`
  - `automations`, `automation_steps`
  - `integrations`
- Star Schema:
  - FactInteractions (eventos: lead criado, diagnóstico, compra, etc)
  - FactSales (compras)
  - DimCustomer, DimFunnel, DimPage, DimChannel, DimDate, etc.

---

## 5. Implementação Modular Recomendada

1. **Banco de Dados**  
   - Migrations para tabelas operacionais e fatos/dimensões.
2. **Services/Domain Layer**
   - Funções para regras de negócio de cada domínio (leadService, funnelService, analyticsService, etc).
3. **API Layer**
   - Endpoints RESTful, validando e orquestrando requests/responses.
4. **Frontend**
   - Integração via React Query ou fetcher.

---

## 6. Documentação

- Cada endpoint documentado com:
  - Método, rota, payload de entrada e saída
  - Exemplo de request/response
  - Regras de negócio envolvidas
- Cada serviço/domain documentado (função, contratos, side effects)
- Blueprint do banco de dados desenhado e comentado

---

**Quer que eu gere o detalhamento (endpoint + schema + fluxo) para um módulo específico primeiro? Qual?**