"""
sqlite_store.py — SQLite + FTS5 存储层

基于 Python 内置 sqlite3，无需任何额外安装。
提供 metadata 持久化 + FTS5 全文索引。

数据库文件位置：rag/data/metadata.db
"""

import sqlite3
import json
import os
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "rag" / "data" / "metadata.db"

_thread_local = threading.local()


def _get_db():
    """获取当前线程的数据库连接（延迟初始化）"""
    conn = getattr(_thread_local, "connection", None)
    if conn is not None:
        return conn

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    _thread_local.connection = conn
    return conn


def initialize():
    """初始化数据库表"""
    db = _get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK(source_type IN ('rule', 'reference', 'project')),
            category TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT '[]',
            scope TEXT NOT NULL DEFAULT 'common',
            tags TEXT NOT NULL DEFAULT '[]',
            priority INTEGER NOT NULL DEFAULT 3,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            title TEXT NOT NULL,
            chunk_type TEXT NOT NULL DEFAULT 'definition',
            text TEXT NOT NULL,
            category TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT '[]',
            scope TEXT NOT NULL DEFAULT 'common',
            tags TEXT NOT NULL DEFAULT '[]',
            priority INTEGER NOT NULL DEFAULT 3,
            source_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            heading_level INTEGER NOT NULL DEFAULT 1
        );
    """)

    # FTS5 全文索引
    try:
        db.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                title,
                text,
                tags,
                content='chunks',
                content_rowid='rowid'
            );

            INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');
        """)
    except sqlite3.OperationalError as e:
        print(f"[sqlite_store] FTS5 初始化警告: {e}")

    # 索引
    try:
        db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category);
            CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(priority);
            CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
        """)
    except sqlite3.OperationalError:
        pass

    print("[sqlite_store] 数据库初始化完成")


def upsert_document(doc):
    """插入或更新文档"""
    db = _get_db()
    db.execute(
        """INSERT OR REPLACE INTO documents
           (doc_id, title, source_path, source_type, category, stage, scope, tags, priority, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            doc["doc_id"],
            doc["title"],
            doc["source_path"],
            doc["source_type"],
            doc["category"],
            json.dumps(doc.get("stage", []), ensure_ascii=False),
            doc.get("scope", "common"),
            json.dumps(doc.get("tags", []), ensure_ascii=False),
            doc.get("priority", 3),
            doc.get("status", "active"),
        ),
    )
    db.commit()


def insert_chunks(chunks):
    """批量插入 chunks（事务）"""
    db = _get_db()

    insert_chunk_sql = """INSERT OR REPLACE INTO chunks
        (chunk_id, doc_id, title, chunk_type, text, category, stage, scope, tags, priority, source_type, source_path, heading_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

    insert_fts_sql = """INSERT INTO chunks_fts (chunk_id, title, text, tags)
        VALUES (?, ?, ?, ?)"""

    for chunk in chunks:
        db.execute(
            insert_chunk_sql,
            (
                chunk["chunk_id"],
                chunk["doc_id"],
                chunk["title"],
                chunk.get("chunk_type", "definition"),
                chunk["text"],
                chunk["category"],
                json.dumps(chunk.get("stage", []), ensure_ascii=False),
                chunk.get("scope", "common"),
                json.dumps(chunk.get("tags", []), ensure_ascii=False),
                chunk.get("priority", 3),
                chunk["source_type"],
                chunk["source_path"],
                chunk.get("heading_level", 1),
            ),
        )
        db.execute(
            insert_fts_sql,
            (
                chunk["chunk_id"],
                chunk["title"],
                chunk["text"],
                " ".join(chunk.get("tags", [])),
            ),
        )

    db.commit()


def _row_to_dict(row):
    """将 sqlite3.Row 转为 dict，并解析 JSON 字段"""
    if row is None:
        return None
    d = dict(row)
    for field in ("stage", "tags"):
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def fts_search(query, top_n=15):
    """FTS5 全文搜索

    对 CJK 文本，将中文拆成单字用 AND 连接以提高精确度，
    英文/数字词用引号做精确匹配。
    """
    db = _get_db()

    # 构建 FTS5 查询
    terms = []
    for t in query.split():
        t = t.strip()
        if not t:
            continue
        # 中文为主的词：拆成单字用 AND 连接
        if any("一" <= c <= "鿿" for c in t):
            chars = [c for c in t if "一" <= c <= "鿿"]
            if chars:
                terms.append(" AND ".join(chars))
            else:
                terms.append(t)
        else:
            # 英文/数字词：加引号精确匹配
            terms.append(f'"{t}"')

    if not terms:
        return []

    final_query = " OR ".join(terms)
    if len(final_query) > 200:
        final_query = final_query[:200]

    try:
        rows = db.execute(
            """SELECT c.*, rank as fts_score
               FROM chunks_fts f
               JOIN chunks c ON c.chunk_id = f.chunk_id
               WHERE chunks_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (final_query, top_n),
        ).fetchall()

        results = []
        for row in rows:
            d = _row_to_dict(row)
            d["fts_score"] = row["fts_score"]
            results.append(d)
        return results
    except sqlite3.OperationalError as e:
        print(f"[sqlite_store] FTS 搜索出错: {e}")
        return []


def filter_chunks(categories=None, stages=None, top_n=20):
    """metadata 过滤查询"""
    db = _get_db()
    conditions = []
    params = []

    if categories:
        placeholders = ",".join("?" for _ in categories)
        conditions.append(f"c.category IN ({placeholders})")
        params.extend(categories)

    if stages:
        stage_conds = []
        for s in stages:
            stage_conds.append("c.stage LIKE ?")
            params.append(f'%"{s}"%')
        conditions.append(f"({' OR '.join(stage_conds)})")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    try:
        rows = db.execute(
            f"""SELECT c.*
                FROM chunks c
                {where}
                ORDER BY c.priority ASC
                LIMIT ?""",
            (*params, top_n),
        ).fetchall()

        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        print(f"[sqlite_store] 过滤查询出错: {e}")
        return []


def get_chunk_by_id(chunk_id):
    """按 chunk_id 获取单条"""
    db = _get_db()
    try:
        row = db.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return _row_to_dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def clear_all():
    """清空所有数据"""
    db = _get_db()
    try:
        db.executescript("""
            DELETE FROM chunks_fts;
            DELETE FROM chunks;
            DELETE FROM documents;
        """)
        db.commit()
    except sqlite3.OperationalError:
        pass


def get_stats():
    """获取统计信息"""
    db = _get_db()
    try:
        doc_count = db.execute("SELECT COUNT(*) as count FROM documents").fetchone()["count"]
        chunk_count = db.execute("SELECT COUNT(*) as count FROM chunks").fetchone()["count"]
        return {"documents": doc_count, "chunks": chunk_count}
    except sqlite3.OperationalError:
        return {"documents": 0, "chunks": 0}


def close():
    """关闭当前线程的数据库连接"""
    conn = getattr(_thread_local, "connection", None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.OperationalError:
            pass
        _thread_local.connection = None


def close_all():
    """关闭所有线程的连接（仅用于清理）"""
    # 由于 thread-local 设计，各线程连接各自管理
    close()
