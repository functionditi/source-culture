PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS contributors (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, verified INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('practice','variation','source','correction')),
 slug TEXT NOT NULL UNIQUE, owner_id TEXT NOT NULL REFERENCES contributors(id),
 parent_id TEXT REFERENCES entities(id), target_id TEXT REFERENCES entities(id),
 status TEXT NOT NULL DEFAULT 'submitted' CHECK(status IN ('draft','submitted','needs changes','published','declined','withdrawn')),
 published_revision_id TEXT REFERENCES revisions(id), demo INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
 id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id), number INTEGER NOT NULL,
 content TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(entity_id, number)
);
CREATE TABLE IF NOT EXISTS citations (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), block_id TEXT,
 source_id TEXT NOT NULL REFERENCES entities(id), relationship TEXT NOT NULL, locator TEXT, annotation TEXT
);
CREATE TABLE IF NOT EXISTS media (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), owner_id TEXT NOT NULL REFERENCES contributors(id),
 storage_key TEXT NOT NULL, alt TEXT NOT NULL, caption TEXT, credit TEXT, permission INTEGER NOT NULL, licence TEXT
);
CREATE TABLE IF NOT EXISTS permissions (
 id TEXT PRIMARY KEY, revision_id TEXT NOT NULL REFERENCES revisions(id), owner_id TEXT NOT NULL REFERENCES contributors(id),
 consent_version TEXT NOT NULL, publication INTEGER NOT NULL, reuse TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confirmations (
 revision_id TEXT PRIMARY KEY REFERENCES revisions(id), owner_id TEXT NOT NULL REFERENCES contributors(id), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
 id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id), revision_id TEXT NOT NULL REFERENCES revisions(id),
 editor_id TEXT NOT NULL REFERENCES contributors(id), action TEXT NOT NULL, feedback TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id), author_id TEXT NOT NULL REFERENCES contributors(id),
 body TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (slug TEXT PRIMARY KEY, entity_id TEXT NOT NULL REFERENCES entities(id));
CREATE TABLE IF NOT EXISTS login_tokens (digest TEXT PRIMARY KEY, contributor_id TEXT NOT NULL REFERENCES contributors(id), expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, contributor_id TEXT NOT NULL REFERENCES contributors(id), csrf TEXT NOT NULL, expires REAL NOT NULL);
CREATE INDEX IF NOT EXISTS entities_public ON entities(status, demo, kind);
CREATE INDEX IF NOT EXISTS revisions_entity ON revisions(entity_id, number);
CREATE INDEX IF NOT EXISTS citations_source ON citations(source_id);
