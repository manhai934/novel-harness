/**
 * retriever.js — 混合检索器
 *
 * 职责：
 * - 混合 FTS + 向量检索
 * - 轻量重排器
 * - 输出最终 top-k chunks
 *
 * 重排公式：
 *   最终分 = 语义分 * 0.35 + FTS分 * 0.15 + 任务匹配分 * 0.30 + priority权重 * 0.12 + source_type权重 * 0.08
 */

import { readFileSync, existsSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import * as sqliteStore from './storage/sqlite-store.js';
import * as vectorStore from './storage/vector-store.js';
import * as router from './router.js';
import { embedText } from './embedder.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');
const require = createRequire(import.meta.url);

const SOURCE_WEIGHTS = { rule: 1.0, reference: 0.8, project: 0.6 };

/**
 * 混合检索
 */
export async function hybridRetrieve(query, {
  taskType,
  topK = 5,
  ftsN = 15,
  vecN = 15
} = {}) {
  const startTime = Date.now();
  const queryStr = String(query);
  const queryLower = queryStr.toLowerCase();

  // 1. 任务路由
  const routeResult = taskType
    ? { task_type: taskType, ...router.getRoute(taskType) }
    : router.routeQuery(queryStr);
  const taskRoute = routeResult;

  // 2. 按任务路由的分类做硬过滤 + FTS 召回
  let ftsResults = [];

  // 如果有明确的任务分类，优先按分类范围过滤
  const categories = taskRoute.categories || [];
  const stages = taskRoute.stages || [];

  if (categories.length > 0) {
    // 先尝试按分类过滤 + 关键词模糊匹配
    const filtered = sqliteStore.filterChunks({ categories, stages, topN: ftsN });
    // 对过滤结果做简单的关键词评分
    ftsResults = filtered.map(row => {
      const text = (row.title + ' ' + row.text).toLowerCase();
      let score = 0;
      const terms = queryLower.split(/\s+/).filter(t => t.length > 0);
      for (const term of terms) {
        if (text.includes(term)) {
          score -= 1;  // FTS rank is negative = better match
        }
      }
      // sub-title match
      const titleText = row.title.toLowerCase();
      if (terms.some(t => titleText.includes(t))) {
        score -= 3;
      }
      return { row, fts_score: score < 0 ? score : -0.1 };
    }).filter(r => r.fts_score < 0);
  }

  // 如果分类过滤没结果，退回到全库 FTS
  if (ftsResults.length === 0) {
    ftsResults = sqliteStore.ftsSearch(queryStr, ftsN).map(r => ({
      row: r,
      fts_score: r.fts_score
    }));
  }

  const ftsMap = new Map();
  for (const r of ftsResults) {
    ftsMap.set(r.row.chunk_id, r);
  }

  // 3. 向量召回
  let vecResults = [];
  try {
    const queryVector = await embedText(queryStr);
    vecResults = vectorStore.vectorSearch(queryVector, vecN);
  } catch (err) {
    console.warn('[retriever] 向量检索失败:', err.message);
  }
  const vecMap = new Map();
  for (const r of vecResults) {
    vecMap.set(r.chunk_id, r.score);
  }

  // 4. 合并候选集
  const candidates = new Map();

  for (const [chunkId, info] of ftsMap) {
    candidates.set(chunkId, {
      chunk_id: chunkId,
      row: info.row,
      fts_score: info.fts_score,
      vec_score: vecMap.get(chunkId) || null
    });
  }

  for (const r of vecResults) {
    if (!candidates.has(r.chunk_id)) {
      const chunkData = sqliteStore.getChunkById(r.chunk_id);
      if (chunkData) {
        candidates.set(r.chunk_id, {
          chunk_id: r.chunk_id,
          row: chunkData,
          fts_score: null,
          vec_score: r.score
        });
      }
    }
  }

  // 5. 重排
  const reranked = Array.from(candidates.values()).map(c => {
    const score = rerank(c.row, queryLower, taskRoute, c.fts_score, c.vec_score);
    const reason = buildReason(c.row, c.fts_score, c.vec_score, taskRoute);
    return {
      chunk_id: c.chunk_id,
      title: c.row.title,
      score,
      reason,
      snippet: c.row.text.substring(0, 200) + (c.row.text.length > 200 ? '...' : ''),
      source_path: c.row.source_path,
      source_type: c.row.source_type,
      category: c.row.category,
      tags: c.row.tags || [],
      priority: c.row.priority
    };
  });

  reranked.sort((a, b) => b.score - a.score);
  const topResults = reranked.slice(0, topK);

  return {
    results: topResults,
    meta: {
      total_candidates: candidates.size,
      fts_count: ftsResults.length,
      vector_count: vecResults.length,
      elapsed_ms: Date.now() - startTime,
      task_type: routeResult.task_type,
      confidence: routeResult.confidence
    }
  };
}

/**
 * 重排
 */
function rerank(row, queryLower, taskRoute, ftsScore, vectorScore) {
  const ftsNorm = (typeof ftsScore === 'number' && ftsScore < 0)
    ? Math.min(1, Math.max(0, -ftsScore / 15))
    : 0;
  const vecNorm = (typeof vectorScore === 'number')
    ? Math.min(1, Math.max(0, vectorScore))
    : 0.2;

  let taskMatch = 0;
  if (taskRoute) {
    const cats = taskRoute.categories || [];
    if (cats.length > 0 && cats.includes(row.category)) taskMatch += 0.5;
    const stages = taskRoute.stages || [];
    if (row.stage && stages.some(s => row.stage.includes(s))) taskMatch += 0.3;

    const desc = (taskRoute.description || '').toLowerCase();
    const queryTerms = queryLower.split(/\s+/).filter(t => t.length > 1);
    const descTerms = desc.split(/[\s：:、，。]/);
    const overlap = queryTerms.filter(qt => descTerms.some(rt => rt.includes(qt)));
    taskMatch += Math.min(overlap.length * 0.05, 0.2);
  }
  taskMatch = Math.min(1, taskMatch);

  const priorityWeight = (6 - (row.priority || 3)) / 5;
  const sourceWeight = SOURCE_WEIGHTS[row.source_type] || 0.5;

  return Number((
    vecNorm * 0.35 +
    ftsNorm * 0.15 +
    taskMatch * 0.30 +
    priorityWeight * 0.12 +
    sourceWeight * 0.08
  ).toFixed(4));
}

/**
 * 构建 reason
 */
function buildReason(row, ftsScore, vectorScore, taskRoute) {
  const parts = [];
  if (typeof ftsScore === 'number' && ftsScore < 0) parts.push('关键词匹配');
  if (typeof vectorScore === 'number' && vectorScore > 0.3) parts.push('语义接近');
  if (taskRoute && (taskRoute.categories || []).includes(row.category)) parts.push('任务类型命中');
  if (row.priority <= 2) parts.push('高优先级');
  if (row.source_type === 'rule') parts.push('规则文档');
  if (parts.length === 0) parts.push('综合匹配');
  return parts.join(' + ');
}
