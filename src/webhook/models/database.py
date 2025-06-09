import sqlite3

from webhook.config import DB_FILE


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
            commit_hash TEXT,
            response_hash TEXT,
            res_fp TEXT
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
            is_normalized BOOLEAN,
            is_obfuscated BOOLEAN,
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
            operator TEXT NULL,
            FOREIGN KEY (source_task_id) REFERENCES tasks (id)
        )
        """
    )
    # 25.05.08 迁移添加 operator 字段到 fork_tasks 表
    migrate_add_operator_to_fork_tasks_nullable(cursor)
    # 25.05.14 迁移添加 response_hash 字段到 tasks 表
    migrate_add_response_hash_to_tasks_nullable(cursor)
    # 25.05.28 迁移添加 is_normalized 和 is_obfuscated 字段到 metadata 表
    migrate_add_is_normalized_and_is_obfuscated_to_metadata_nullable(cursor)
    # 25.06.09 迁移添加 res_fp 字段到 tasks 表
    migrate_add_res_fp_to_tasks_nullable(cursor)

    # 提交更改并关闭连接
    conn.commit()
    conn.close()


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """
    检查表中是否存在指定列

    Args:
        cursor (sqlite3.Cursor): 数据库游标
        table_name (str): 表名
        column_name (str): 列名

    Returns:
        bool: 是否存在
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]  # 使用索引 1 获取列名
    return column_name in columns


def migrate_add_operator_to_fork_tasks_nullable(cursor: sqlite3.Cursor):
    """
    迁移添加operator字段为可空
    """
    if _column_exists(cursor, "fork_tasks", "operator"):
        return
    # 直接添加可空字段
    cursor.execute(
        """
        ALTER TABLE fork_tasks
            ADD COLUMN operator TEXT NULL
        """
    )


def migrate_add_response_hash_to_tasks_nullable(cursor: sqlite3.Cursor):
    """
    迁移添加response_hash字段为可空
    """
    if _column_exists(cursor, "tasks", "response_hash"):
        return
    # 直接添加可空字段
    cursor.execute(
        """
        ALTER TABLE tasks
            ADD COLUMN response_hash TEXT NULL
        """
    )


def migrate_add_is_normalized_and_is_obfuscated_to_metadata_nullable(cursor: sqlite3.Cursor):
    """
    迁移添加is_normalized和is_obfuscated字段为可空
    """
    try:
        # 分别检查和添加每个字段
        if not _column_exists(cursor, "build_task_metadata", "is_normalized"):
            cursor.execute(
                """
                ALTER TABLE build_task_metadata
                    ADD COLUMN is_normalized BOOLEAN NULL
                """
            )

        if not _column_exists(cursor, "build_task_metadata", "is_obfuscated"):
            cursor.execute(
                """
                ALTER TABLE build_task_metadata
                    ADD COLUMN is_obfuscated BOOLEAN NULL
                """
            )
    except sqlite3.Error as e:
        # 记录错误但不中断迁移过程
        print(f"迁移警告: 添加字段时出错 - {e}")


def migrate_add_res_fp_to_tasks_nullable(cursor: sqlite3.Cursor):
    """
    迁移添加res_fp字段为可空
    """
    if _column_exists(cursor, "tasks", "res_fp"):
        return
    # 直接添加可空字段
    cursor.execute(
        """
        ALTER TABLE tasks
            ADD COLUMN res_fp TEXT NULL
        """
    )
