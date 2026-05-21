"""
sqlite_store.py - SQLite + FTS5 存储层。
"""

import json
import sqlite3
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / "rag" / "data" / "metadata.db"

_thread_local = threading.local()


def _get_db():
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
    db = _get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_path TEXT NOT NULL,
            source_type TEXT NOT NULL CHECK(source_type IN ('knowledge', 'rule', 'reference', 'project')),
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
    except sqlite3.OperationalError as exc:
        print(f"[sqlite_store] FTS5 初始化警告: {exc}")

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
    if row is None:
        return None

    result = dict(row)
    for field in ("stage", "tags"):
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return result


def fts_search(query, top_n=15):
    db = _get_db()

    terms = []
    for term in query.split():
        term = term.strip()
        if not term:
            continue

        if any("\u4e00" <= char <= "\u9fff" for char in term):
            chars = [char for char in term if "\u4e00" <= char <= "\u9fff"]
            if chars:
                terms.append(" AND ".join(chars))
            else:
                terms.append(term)
        else:
            terms.append(f'"{term}"')

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
            item = _row_to_dict(row)
            item["fts_score"] = row["fts_score"]
            results.append(item)
        return results
    except sqlite3.OperationalError as exc:
        print(f"[sqlite_store] FTS 搜索失败: {exc}")
        return []


def filter_chunks(categories=None, stages=None, top_n=20):
    db = _get_db()
    conditions = []
    params = []

    if categories:
        placeholders = ",".join("?" for _ in categories)
        conditions.append(f"c.category IN ({placeholders})")
        params.extend(categories)

    if stages:
        stage_conditions = []
        for stage in stages:
            stage_conditions.append("c.stage LIKE ?")
            params.append(f'%"{stage}"%')
        conditions.append(f"({' OR '.join(stage_conditions)})")

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

        return [_row_to_dict(row) for row in rows]
    except sqlite3.OperationalError as exc:
        print(f"[sqlite_store] 过滤查询失败: {exc}")
        return []


def get_chunk_by_id(chunk_id):
    db = _get_db()
    try:
        row = db.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return _row_to_dict(row) if row else None
    except sqlite3.OperationalError:
        return None


def clear_all():
    db = _get_db()
    try:
        db.executescript("""
            DROP TABLE IF EXISTS chunks_fts;
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS documents;
        """)
        db.commit()
    except sqlite3.OperationalError:
        pass


def get_stats():
    db = _get_db()
    try:
        doc_count = db.execute("SELECT COUNT(*) as count FROM documents").fetchone()["count"]
        chunk_count = db.execute("SELECT COUNT(*) as count FROM chunks").fetchone()["count"]
        return {"documents": doc_count, "chunks": chunk_count}
    except sqlite3.OperationalError:
        return {"documents": 0, "chunks": 0}


def close():
    conn = getattr(_thread_local, "connection", None)
    if conn is not None:
        try:
            conn.close()
        except sqlite3.OperationalError:
            pass
        _thread_local.connection = None


def close_all():
    close()
