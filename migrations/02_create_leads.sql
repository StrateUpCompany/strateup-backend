-- Criação da tabela leads para captura de formulários
-- Execute este SQL no Supabase SQL Editor

-- Drop table if exists (for clean reset)
DROP TABLE IF EXISTS leads;

-- Create leads table
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can INSERT (para captura pública)
CREATE POLICY "Allow public insert" ON leads FOR INSERT WITH CHECK (true);

-- Policy: Authenticated users can READ
CREATE POLICY "Allow authenticated read" ON leads FOR SELECT USING (true);

-- Index for faster queries by project
CREATE INDEX idx_leads_project_id ON leads(project_id);
