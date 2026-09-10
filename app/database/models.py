"""
SQL schema (DDL) for every table used by the bot.

Kept as plain SQL strings (no ORM) to keep memory usage and dependency
count as low as possible, per the 1GB-RAM constraint.
"""

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        first_name TEXT,
        language TEXT NOT NULL DEFAULT 'fa',
        selected_model TEXT,
        memory_enabled INTEGER NOT NULL DEFAULT 1,
        notifications_enabled INTEGER NOT NULL DEFAULT 1,
        response_style TEXT NOT NULL DEFAULT 'normal',
        is_blocked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_telegram_user_id ON users(telegram_user_id);",
    """
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE NOT NULL,
        title TEXT,
        mode TEXT NOT NULL DEFAULT 'mention',
        language TEXT NOT NULL DEFAULT 'fa',
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_groups_chat_id ON groups(chat_id);",
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_type TEXT NOT NULL,           -- 'user' | 'group'
        owner_id INTEGER NOT NULL,          -- telegram_user_id or chat_id
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(owner_type, owner_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner_type, owner_id);",
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL,                 -- 'system' | 'user' | 'assistant'
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);",
    "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);",
    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_type TEXT NOT NULL,           -- 'user' | 'group'
        owner_id INTEGER NOT NULL,
        provider TEXT,
        model TEXT,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_usage_owner ON usage(owner_type, owner_id);",
    "CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage(created_at);",
    """
    CREATE TABLE IF NOT EXISTS admin_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_telegram_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_admin_actions_created_at ON admin_actions(created_at);",
]
