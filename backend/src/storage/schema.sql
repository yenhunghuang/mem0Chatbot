-- 對話會話資料表
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'archived', 'expired')),
    message_count INTEGER DEFAULT 0
);

-- 訊息資料表
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 記憶中繼資料表（向量儲存在 Chroma）
CREATE TABLE IF NOT EXISTS memory_metadata (
    memory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT CHECK(category IN ('preference', 'fact', 'behavior')),
    source_message_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    relevance REAL DEFAULT 0.0,
    FOREIGN KEY (source_message_id) REFERENCES messages(id) ON DELETE SET NULL
);

-- 索引以加快查詢
CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
ON conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_user_activity 
ON conversations(user_id, last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_status 
ON conversations(status);

CREATE INDEX IF NOT EXISTS idx_messages_conversation 
ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp 
ON messages(conversation_id, timestamp ASC);

CREATE INDEX IF NOT EXISTS idx_memory_user_id 
ON memory_metadata(user_id);

CREATE INDEX IF NOT EXISTS idx_memory_created 
ON memory_metadata(created_at DESC);
