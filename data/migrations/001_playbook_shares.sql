CREATE TABLE IF NOT EXISTS playbook_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_slug TEXT UNIQUE NOT NULL,
    playbook JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_playbook_shares_slug ON playbook_shares (share_slug);
