
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO state VALUES ('mode','observe');
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, started_at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS locks (name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS metrics (day TEXT NOT NULL, object_id TEXT NOT NULL, level TEXT NOT NULL, name TEXT, spend REAL NOT NULL, leads INTEGER NOT NULL, conversations INTEGER NOT NULL, impressions INTEGER NOT NULL, clicks INTEGER NOT NULL, synced_at TEXT NOT NULL, PRIMARY KEY(day,object_id,level));
CREATE TABLE IF NOT EXISTS objects (id TEXT PRIMARY KEY, level TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, managed INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL, synced_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lead_jobs (id TEXT PRIMARY KEY, ad_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, next_attempt INTEGER NOT NULL DEFAULT 0, error TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY, ad_id TEXT NOT NULL, created_at TEXT NOT NULL, contact_json TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'new', notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, object_id TEXT, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS competitors (id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, observation TEXT NOT NULL, observed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS briefs (id TEXT PRIMARY KEY, at TEXT NOT NULL, content TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, name TEXT NOT NULL, adset_id TEXT NOT NULL, post_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', meta_ad_id TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS lead_jobs_due ON lead_jobs(status,next_attempt);
CREATE INDEX IF NOT EXISTS lead_stages ON leads(stage,created_at);

CREATE TABLE IF NOT EXISTS whatsapp_alert_jobs (lead_id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, next_attempt INTEGER NOT NULL DEFAULT 0, message_id TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS whatsapp_alert_due ON whatsapp_alert_jobs(status,next_attempt);
