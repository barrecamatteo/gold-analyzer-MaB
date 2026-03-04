-- ============================================
-- GOLD ANALYZER - Schema Supabase
-- Esegui questo SQL nel SQL Editor di Supabase
-- ============================================

-- Tabella utenti
CREATE TABLE IF NOT EXISTS gold_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabella analisi
CREATE TABLE IF NOT EXISTS gold_analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES gold_users(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    gold_price NUMERIC,
    total_score INTEGER,
    bias TEXT,
    scores_json JSONB,
    claude_response TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_gold_analyses_user_date
    ON gold_analyses(user_id, analysis_date DESC);

CREATE INDEX IF NOT EXISTS idx_gold_analyses_date
    ON gold_analyses(analysis_date DESC);

-- Row Level Security (RLS)
ALTER TABLE gold_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE gold_analyses ENABLE ROW LEVEL SECURITY;

-- Policy: ogni utente vede solo i propri dati
CREATE POLICY "Users can read own data" ON gold_users
    FOR SELECT USING (true);

CREATE POLICY "Users can insert" ON gold_users
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Users read own analyses" ON gold_analyses
    FOR SELECT USING (true);

CREATE POLICY "Users insert own analyses" ON gold_analyses
    FOR INSERT WITH CHECK (true);

-- (Opzionale) Tabella per riserve banche centrali (fallback manuale)
CREATE TABLE IF NOT EXISTS gold_cb_reserves (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    quarter TEXT NOT NULL,
    net_purchases_tonnes NUMERIC,
    top_buyers TEXT,
    source TEXT DEFAULT 'manual',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
