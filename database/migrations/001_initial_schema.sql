-- Создание таблицы users с UUID
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    rate_limit INTEGER DEFAULT 100 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Создание таблицы tasks
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    white_bg BOOLEAN DEFAULT TRUE NOT NULL,
    progress INTEGER DEFAULT 0 NOT NULL,
    processed_files INTEGER DEFAULT 0 NOT NULL,
    total_files INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    error TEXT,
    result_data BYTEA
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_end_time ON tasks(end_time) WHERE end_time IS NOT NULL;

-- Создание таблицы thematic_categories
CREATE TABLE IF NOT EXISTS thematic_categories (
    main_category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (main_category, subcategory)
);

CREATE INDEX IF NOT EXISTS idx_thematic_main_category ON thematic_categories(main_category);
