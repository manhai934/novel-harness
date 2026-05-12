/**
 * sqlite-store.js — SQLite + FTS5 存储层
 *
 * 基于 Node.js 内置 node:sqlite (DatabaseSync)，无需任何原生编译。
 * 提供 metadata 持久化 + FTS5 全文索引。
 *
 * 数据库文件位置：rag/data/metadata.db
 */

import { existsSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../../..');
const DB_PATH = join(PROJECT_ROOT, 'rag/data/metadata.db');

let db = null;

/**
 * 获取数据库连接（延迟初始化）
 */
function getDb() {
  if (db) return db;

  // 确保目录存在
  const dbDir = dirname(DB_PATH);
  if (!existsSync(dbDir)) {
    mkdirSync(dbDir, { recursive: true });
  }

  // 使用 Node.js 内置 SQLite (v22+)
  const { DatabaseSync } = require('node:sqlite');
  db = new DatabaseSync(DB_PATH);
  db.exec('PRAGMA journal_mode = WAL');
  db.exec('PRAGMA foreign_keys = ON');

  return db;
}

/**
 * require for CJS modules in ESM
 */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

/**
 * 初始化数据库表
 */
export function initialize() {
  const db = getDb();

  db.exec(`
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
    )
  `);

  db.exec(`
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
    )
  `);

  // FTS5 全文索引 (注意: node:sqlite 使用 fts5(content) 而非 fts5(content TEXT))
  try {
    db.exec(`
      CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
        chunk_id UNINDEXED,
        title,
        text,
        tags,
        content='chunks',
        content_rowid='rowid'
      )
    `);

    // 重建 FTS 内容以确保同步
    db.exec(`INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')`);
  } catch (err) {
    console.warn('[sqlite-store] FTS5 初始化:', err.message);
  }

  // 索引
  try {
    db.exec('CREATE INDEX IF NOT EXISTS idx_chunks_category ON chunks(category)');
    db.exec('CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(priority)');
    db.exec('CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)');
  } catch {}

  console.log('[sqlite-store] 数据库初始化完成');
}

/**
 * 插入或更新文档
 */
export function upsertDocument(doc) {
  const db = getDb();
  db.prepare(`
    INSERT OR REPLACE INTO documents (doc_id, title, source_path, source_type, category, stage, scope, tags, priority, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    doc.doc_id,
    doc.title,
    doc.source_path,
    doc.source_type,
    doc.category,
    JSON.stringify(doc.stage || []),
    doc.scope || 'common',
    JSON.stringify(doc.tags || []),
    doc.priority || 3,
    doc.status || 'active'
  );
}

/**
 * 批量插入 chunks（事务）
 * @param {Array} chunks
 */
export function insertChunks(chunks) {
  const db = getDb();

  const insertChunk = db.prepare(`
    INSERT OR REPLACE INTO chunks (chunk_id, doc_id, title, chunk_type, text, category, stage, scope, tags, priority, source_type, source_path, heading_level)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertFts = db.prepare(`
    INSERT INTO chunks_fts (chunk_id, title, text, tags)
    VALUES (?, ?, ?, ?)
  `);

  // 使用事务批量处理
  for (const chunk of chunks) {
    insertChunk.run(
      chunk.chunk_id, chunk.doc_id, chunk.title, chunk.chunk_type,
      chunk.text, chunk.category, JSON.stringify(chunk.stage || []),
      chunk.scope || 'common', JSON.stringify(chunk.tags || []),
      chunk.priority || 3, chunk.source_type, chunk.source_path,
      chunk.heading_level || 1
    );
    insertFts.run(
      chunk.chunk_id,
      chunk.title,
      chunk.text,
      (chunk.tags || []).join(' ')
    );
  }
}

/**
 * FTS5 全文搜索
 * @param {string} query - 搜索文本
 * @param {number} topN - 返回数量
 * @returns {Array}
 */
export function ftsSearch(query, topN = 15) {
  const db = getDb();

  // 构建 FTS5 查询
  // 注意：unicode61 tokenizer 对 CJK 按单字切分，
  // 所以中文词不用引号括起来（让 FTS5 自动匹配单字），
  // 英文/数字词用引号括起来做精确匹配
  const terms = query
    .replace(/[^\w一-鿿]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(t => t.length >= 1)
    .map(t => {
      // 中文为主的词：不加引号，匹配单字
      if (/[一-鿿]/.test(t)) {
        // 对中文，拆成单字用 AND 连接以提高精确度
        const chars = t.replace(/[^一-鿿]/g, '').split('');
        if (chars.length > 0) {
          return chars.join(' AND ');
        }
        return t;
      }
      // 英文/数字词：加引号精确匹配
      return `"${t}"`;
    })
    .filter(t => t.length > 0)
    .join(' OR ');
  // 如果中文单字太多，限制长度避免查询过大
  const finalQuery = terms.length > 200 ? terms.substring(0, 200) : terms;

  if (!terms) return [];

  try {
    const rows = db.prepare(`
      SELECT c.*, rank as fts_score
      FROM chunks_fts f
      JOIN chunks c ON c.chunk_id = f.chunk_id
      WHERE chunks_fts MATCH ?
      ORDER BY rank
      LIMIT ?
    `).all(finalQuery, topN);

    return rows.map(r => ({
      ...r,
      stage: JSON.parse(r.stage || '[]'),
      tags: JSON.parse(r.tags || '[]'),
    }));
  } catch (err) {
    console.warn('[sqlite-store] FTS 搜索出错:', err.message);
    return [];
  }
}

/**
 * metadata 过滤查询
 */
export function filterChunks({ categories, stages, topN = 20 } = {}) {
  const db = getDb();
  const conditions = [];
  const params = [];

  if (categories && categories.length > 0) {
    const placeholders = categories.map(() => '?').join(',');
    conditions.push(`c.category IN (${placeholders})`);
    params.push(...categories);
  }

  if (stages && stages.length > 0) {
    const stageConds = stages.map(() => `c.stage LIKE ?`);
    conditions.push(`(${stageConds.join(' OR ')})`);
    params.push(...stages.map(s => `%"${s}"%`));
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

  try {
    const rows = db.prepare(`
      SELECT c.*
      FROM chunks c
      ${where}
      ORDER BY c.priority ASC
      LIMIT ?
    `).all(...params, topN);

    return rows.map(r => ({
      ...r,
      stage: JSON.parse(r.stage || '[]'),
      tags: JSON.parse(r.tags || '[]'),
    }));
  } catch (err) {
    console.warn('[sqlite-store] 过滤查询出错:', err.message);
    return [];
  }
}

/**
 * 按 chunk_id 获取单条
 */
export function getChunkById(chunkId) {
  const db = getDb();
  try {
    const row = db.prepare('SELECT * FROM chunks WHERE chunk_id = ?').get(chunkId);
    if (row) {
      return {
        ...row,
        stage: JSON.parse(row.stage || '[]'),
        tags: JSON.parse(row.tags || '[]')
      };
    }
  } catch {}
  return null;
}

/**
 * 清空所有数据
 */
export function clearAll() {
  const db = getDb();
  try { db.exec('DELETE FROM chunks_fts'); } catch {}
  try { db.exec('DELETE FROM chunks'); } catch {}
  try { db.exec('DELETE FROM documents'); } catch {}
}

/**
 * 获取统计信息
 */
export function getStats() {
  const db = getDb();
  try {
    const docCount = db.prepare('SELECT COUNT(*) as count FROM documents').get();
    const chunkCount = db.prepare('SELECT COUNT(*) as count FROM chunks').get();
    return {
      documents: docCount.count,
      chunks: chunkCount.count
    };
  } catch {
    return { documents: 0, chunks: 0 };
  }
}

/**
 * 关闭数据库
 */
export function close() {
  if (db) {
    try { db.close(); } catch {}
    db = null;
  }
}

export default {
  initialize, upsertDocument, insertChunks,
  ftsSearch, filterChunks, getChunkById,
  clearAll, getStats, close
};
