-- Create Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    url TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    local_path TEXT,
    error_msg TEXT,
    funnel_data JSONB
);

-- Create Leads Table
DROP TABLE IF EXISTS public.leads;
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    data JSONB NOT NULL, -- Stores name, email, phone, source, etc.
    project_id UUID REFERENCES public.projects(id)
);

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

-- Create Policies (Allow all for all for dev)
DROP POLICY IF EXISTS "Enable all access for projects" ON public.projects;
CREATE POLICY "Enable all access for projects" ON public.projects FOR ALL USING (true);

DROP POLICY IF EXISTS "Enable all access for leads" ON public.leads;
CREATE POLICY "Enable all access for leads" ON public.leads FOR ALL USING (true);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_leads_project_id ON public.leads(project_id);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON public.projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads ((data->>'source'));

-- Search Indexes (GIN)
CREATE INDEX IF NOT EXISTS idx_leads_data_gin ON public.leads USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_projects_url_gin ON public.projects USING GIN (to_tsvector('english', url || ' ' || coalesce(status, '')));

-- Webhooks Table
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,
    user_id TEXT -- Optional for now, will link to auth.users eventually
);

-- ==============================================================================
-- SPRINT 45: MULTI-TENANT ARCHITECTURE (AGENCY OS)
-- ==============================================================================

-- 1. Workspaces Table (The Digital Office)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    owner_id UUID REFERENCES auth.users(id)
);

-- 2. Workspace Members (The Team Badge)
CREATE TABLE IF NOT EXISTS workspace_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'member', 'viewer')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);

-- 3. RLS Policies (Security Layer)
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
-- Sprint 45: Workspace Tables (Already added)
-- ... (Keeping previous content)

-- Sprint 46: Monetization Engine (Brazil Focus)
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    plan_id TEXT NOT NULL, -- e.g., 'agency_brl_monthly'
    status TEXT NOT NULL CHECK (status IN ('active', 'past_due', 'canceled', 'trialing')),
    current_period_end TIMESTAMPTZ NOT NULL,
    stripe_subscription_id TEXT, -- or 'asaas_subscription_id'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID REFERENCES subscriptions(id) NOT NULL,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    amount INTEGER NOT NULL, -- in cents (e.g., 29700 for R$ 297.00)
    currency TEXT DEFAULT 'brl',
    status TEXT NOT NULL CHECK (status IN ('paid', 'open', 'void', 'uncollectible')),
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies for Monetization
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscription" ON subscriptions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own invoices" ON invoices
    FOR SELECT USING (auth.uid() = user_id);

-- Service Role (Backend) needs full access to manage subs
-- (Implicitly has access via service_role key, but explicit policy prevents confusion)
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- Workspace Access
CREATE POLICY "View my workspaces" ON workspaces
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_members.workspace_id = workspaces.id
            AND workspace_members.user_id = auth.uid()
        )
    );

CREATE POLICY "Create workspace" ON workspaces
    FOR INSERT WITH CHECK (true);

-- Member Access
CREATE POLICY "View team members" ON workspace_members
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM workspace_members as my_membership
            WHERE my_membership.workspace_id = workspace_members.workspace_id
            AND my_membership.user_id = auth.uid()
        )
    );

-- TODO: Add workspace_id column to projects and leads in migration step
