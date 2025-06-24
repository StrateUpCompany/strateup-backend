# Documentação Completa: Lógica de Negócio + Modelo de Dados (Star Schema)

---

## 1. Visão Geral da Lógica de Negócio StrateUp

### Missão
Construir um ecossistema de marketing e vendas automatizado, guiando o cliente pela Escada de Valor, baseado nos livros Dotcom/Expert/Traffic Secrets e Marketing 4.0.

### Macro Fluxos de Negócio
- Aquisição e Segmentação (Diagnóstico, Dream 100, rastreamento de origem)
- Conteúdo (Blog, Lead Magnets, Páginas)
- Funis e Automação (Sequências, Multicanal, Testes A/B)
- Vendas (Checkout, Produtos, LTV)
- Inteligência (Analytics, Recomendações)

---

## 2. Padrão de Modelagem: Star Schema

### O que é?
Um modelo de dados com:
- **Fact Table (Fato):** métricas do negócio (ex: vendas, eventos, interações).
- **Dimension Tables (Dimensões):** descrevem o contexto (ex: tempo, cliente, produto, canal).

---

## 3. Proposta de Star Schema para StrateUp

### 3.1. **Fact Tables (Tabelas Fato)**

#### a) Fato de Interação (FactInteractions)
- id (PK)
- datetime_key (FK)
- customer_key (FK)
- funnel_key (FK)
- page_key (FK)
- channel_key (FK)
- event_type (ex: "lead_captured", "diagnostic_completed", "purchase", "email_opened", "whatsapp_clicked")
- event_value (ex: valor da venda, score, etc)
- session_id

#### b) Fato de Vendas (FactSales)
- id (PK)
- datetime_key (FK)
- customer_key (FK)
- product_key (FK)
- order_id
- quantity
- total_value
- discount
- payment_status

---

### 3.2. **Dimension Tables (Tabelas Dimensão)**

#### DimDate
- datetime_key (PK)
- date
- year
- month
- day
- hour
- week

#### DimCustomer
- customer_key (PK)
- email
- nome
- telefone
- segmento
- temperatura
- data_cadastro

#### DimProduct
- product_key (PK)
- nome
- categoria
- tipo
- preco_base

#### DimFunnel
- funnel_key (PK)
- nome
- tipo
- descricao

#### DimPage
- page_key (PK)
- url
- tipo (blog, página de venda, página de captura)
- titulo

#### DimChannel
- channel_key (PK)
- nome (Facebook, Google, WhatsApp, Orgânico, etc)
- utm_source
- utm_medium
- origem (Dream 100, Ads, SEO, Referral)

---

## 4. Exemplos de Consulta (SQL)

- **Quantos leads foram capturados por canal?**
  ```sql
  SELECT ch.nome, COUNT(*) AS leads
    FROM FactInteractions fi
    JOIN DimChannel ch ON fi.channel_key = ch.channel_key
   WHERE fi.event_type = 'lead_captured'
GROUP BY ch.nome
  ```

- **Taxa de conversão por funil:**
  ```sql
  SELECT f.nome, 
         COUNT(DISTINCT CASE WHEN fi.event_type='lead_captured' THEN fi.customer_key END) AS leads,
         COUNT(DISTINCT CASE WHEN fi.event_type='purchase' THEN fi.customer_key END) AS clientes,
         (COUNT(DISTINCT CASE WHEN fi.event_type='purchase' THEN fi.customer_key END) * 100.0) / 
         NULLIF(COUNT(DISTINCT CASE WHEN fi.event_type='lead_captured' THEN fi.customer_key END),0) AS taxa_conversao
    FROM FactInteractions fi
    JOIN DimFunnel f ON fi.funnel_key = f.funnel_key
GROUP BY f.nome
  ```

---

## 5. Como Documentar Cada Módulo

Para cada módulo (Diagnóstico, Funis, Blog, Produtos, Automação):

- **Lógica de Negócio:**  
  - Qual o objetivo do módulo?
  - Quais eventos/fatos ele gera?
  - Quais dimensões ele referencia?
  - Quais KPIs ele alimenta?

- **Exemplo**
  - Diagnóstico:
    - Objetivo: Segmentar leads e identificar principal dor.
    - Fato gerado: `event_type = 'diagnostic_completed'` em FactInteractions.
    - Referencia dimensões: customer, funnel, page, channel, datetime.
    - KPIs: Distribuição de dores, taxa de conversão para compra.

---

## 6. Benefícios esperados dessa abordagem

- **Extrema clareza e rastreabilidade dos dados e fluxos.**
- **Facilidade para criar dashboards e relatórios sem refazer queries complexas.**
- **Escalabilidade para integrar novas fontes/canais/dimensões (ex: Instagram, TikTok, etc).**
- **Pronto para Data Lake, BI, e IA no futuro.**

---

## 7. Próximos Passos

1. Finalizar documentação detalhada de cada módulo (um arquivo por módulo).
2. Desenhar o modelo físico no Supabase/Postgres (DDL).
3. Migrar/adaptar os services e actions do backend para usar o novo modelo.
4. Escrever queries de analytics e dashboards usando o star schema.

---

**Se quiser, posso criar um arquivo de documentação para cada módulo, já seguindo esse padrão, e gerar o DDL (SQL) inicial para seu banco. Me diga por qual módulo começar!**