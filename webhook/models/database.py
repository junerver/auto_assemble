import sqlite3

from ..config import DB_FILE


def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建tasks表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            prod_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            author TEXT,
            commit_title TEXT,
            commit_message TEXT,
            commit_url TEXT,
            priority INTEGER DEFAULT 0,
            retries INTEGER DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT NOT NULL,
            error TEXT,
            commit_hash TEXT
        )
    """
    )

    # 创建项目配置表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_config (
            id TEXT PRIMARY KEY,
            project_url TEXT NOT NULL UNIQUE,
            prod_name TEXT NOT NULL,
            hbx_version TEXT,
            uniapp_id TEXT,
            uniapp_appkey TEXT,
            uniapp_is_cli BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    """
    )

    # 创建第三方字典表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS third_party_dict (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            dict_key TEXT NOT NULL,
            dict_value TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            UNIQUE(provider, dict_key)
        )
    """
    )

    # 创建第三方配置表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS third_party_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            dict_key TEXT NOT NULL,
            config_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (project_id) REFERENCES project_config(id),
            FOREIGN KEY (dict_key) REFERENCES third_party_dict(dict_key),
            UNIQUE(project_id, dict_key)
        )
    """
    )

    # 创建webhook请求记录表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS webhook_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            request_body TEXT NOT NULL,
            headers TEXT,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        """
    )

    # 创建构建任务产物元数据表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS build_task_metadata
        (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id      TEXT    NOT NULL,
            package_name TEXT    NOT NULL,
            version_name TEXT    NOT NULL,
            version_code INTEGER NOT NULL,
            build_type   TEXT    NOT NULL,
            flavor       TEXT    NOT NULL,
            build_date   TEXT    NOT NULL,
            file_size    INTEGER NOT NULL,
            md5          TEXT    NOT NULL,
            created_at   TIMESTAMP DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """
    )

    # 创建派生任务表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fork_tasks
        (
            id                    TEXT PRIMARY KEY,
            source_task_id        TEXT      NOT NULL,
            source_branch TEXT NOT NULL,
            target_branch         TEXT      NOT NULL,
            target_version_name   TEXT      NOT NULL,
            target_version_code   TEXT      NOT NULL,
            commit_message        TEXT      NOT NULL,
            created_at            TIMESTAMP NOT NULL,
            FOREIGN KEY (source_task_id) REFERENCES tasks (id)
        )
        """
    )
    conn.commit()
    conn.close()
