/**
 * vector-store.js — 向量存储抽象层
 *
 * 职责：
 * - 为 chunk 提供向量存储与相似度检索
 * - V1 实现：内存存储 + 余弦相似度（适用于小规模知识库）
 * - 接口设计为可替换，后续可对接 Qdrant/Chroma
 *
 * 设计原则：
 * - 上层代码通过相同接口调用，不依赖具体实现
 * - 后续只需替换此文件（或切换配置）即可升级到 Qdrant
 */

import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../../..');
const VECTORS_DIR = join(PROJECT_ROOT, 'rag/data/vectors');

let vectors = [];  // [{chunk_id, vector}]
let loaded = false;

/**
 * 加载持久化的向量
 */
function loadVectors() {
  if (loaded) return;
  const filePath = join(VECTORS_DIR, 'vectors.json');
  try {
    if (existsSync(filePath)) {
      const data = readFileSync(filePath, 'utf-8');
      vectors = JSON.parse(data);
      console.log(`[vector-store] 已加载 ${vectors.length} 个向量`);
    }
  } catch (err) {
    console.warn('[vector-store] 加载向量文件失败:', err.message);
  }
  loaded = true;
}

/**
 * 持久化向量到磁盘
 */
function saveVectors() {
  if (!existsSync(VECTORS_DIR)) {
    mkdirSync(VECTORS_DIR, { recursive: true });
  }
  const filePath = join(VECTORS_DIR, 'vectors.json');
  writeFileSync(filePath, JSON.stringify(vectors), 'utf-8');
}

/**
 * 余弦相似度计算
 */
function cosineSimilarity(a, b) {
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

/**
 * 向量维度
 */
export const VECTOR_DIM = 384;

/**
 * 批量插入向量
 * @param {Array<{chunk_id: string, vector: number[]}>} items
 */
export function insertVectors(items) {
  loadVectors();

  // 去重
  const existing = new Set(vectors.map(v => v.chunk_id));
  for (const item of items) {
    if (existing.has(item.chunk_id)) {
      const idx = vectors.findIndex(v => v.chunk_id === item.chunk_id);
      vectors[idx] = item;
    } else {
      vectors.push(item);
      existing.add(item.chunk_id);
    }
  }

  saveVectors();
}

/**
 * 清空所有向量
 */
export function clearVectors() {
  vectors = [];
  saveVectors();
}

/**
 * 向量相似度检索
 * @param {number[]} queryVector - 查询向量
 * @param {number} topN - 返回数量
 * @returns {Array<{chunk_id: string, score: number}>}
 */
export function vectorSearch(queryVector, topN = 15) {
  loadVectors();

  if (vectors.length === 0) return [];

  // 计算所有相似度
  const scores = vectors.map(v => ({
    chunk_id: v.chunk_id,
    score: cosineSimilarity(queryVector, v.vector)
  }));

  // 排序取 top
  scores.sort((a, b) => b.score - a.score);

  return scores.slice(0, topN).map(r => ({
    chunk_id: r.chunk_id,
    score: Number(r.score.toFixed(4))
  }));
}

/**
 * 获取向量总数
 */
export function getVectorCount() {
  loadVectors();
  return vectors.length;
}

/**
 * 获取 chunk_id 对应的向量
 */
export function getVector(chunk_id) {
  loadVectors();
  const found = vectors.find(v => v.chunk_id === chunk_id);
  return found ? found.vector : null;
}

export default {
  VECTOR_DIM, insertVectors, clearVectors,
  vectorSearch, getVectorCount, getVector
};
