/**
 * server.js — RAG 本地 HTTP 服务
 *
 * 提供接口：
 * - POST /retrieve          混合检索
 * - POST /reindex           重建索引
 * - GET  /health            健康检查
 * - POST /explain-retrieval 检索解释（可选）
 * - GET  /stats             索引统计
 * - GET  /routes            路由信息
 */

import express from 'express';
import { buildFullIndex, getIndexStats } from './indexer.js';
import { hybridRetrieve } from './retriever.js';
import { routeQuery, getTaskTypes, getRoute } from './router.js';
import { buildContextPack, contextPackToText } from './context-pack.js';
import * as sqliteStore from './storage/sqlite-store.js';
import * as vectorStore from './storage/vector-store.js';
import { embedText } from './embedder.js';
import { existsSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');

const app = express();
const PORT = process.env.PORT || 3456;

app.use(express.json());

// 确保数据目录存在
const dataDir = join(PROJECT_ROOT, 'rag/data');
if (!existsSync(dataDir)) {
  mkdirSync(dataDir, { recursive: true });
}

// 启动时初始化 SQLite
sqliteStore.initialize();

// ========== 接口 ==========

/**
 * POST /retrieve — 混合检索
 */
app.post('/retrieve', async (req, res) => {
  try {
    const { query, task_type, project_hint, top_k = 5 } = req.body;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return res.status(400).json({ error: 'query 是必填字段' });
    }

    // 混合检索
    const { results, meta } = await hybridRetrieve(query, {
      taskType: task_type,
      topK: top_k
    });

    // 获取路由信息
    const routeInfo = task_type
      ? { task_type, ...getRoute(task_type) }
      : routeQuery(query);

    // 构建 context pack
    const contextPack = buildContextPack(
      query,
      routeInfo.task_type,
      routeInfo.filters,
      results,
      meta
    );

    // 生成纯文本版
    const contextText = contextPackToText(contextPack);

    res.json({
      task_type: routeInfo.task_type,
      query,
      filters: routeInfo.filters || {},
      results,
      context_pack: contextPack,
      context_text: contextText,
      meta
    });
  } catch (err) {
    console.error('[server] /retrieve 错误:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * POST /reindex — 重建索引
 */
app.post('/reindex', async (req, res) => {
  try {
    // 在后台执行，先返回接受
    const result = await buildFullIndex();

    res.json({
      status: 'ok',
      message: '索引重建完成',
      ...result
    });
  } catch (err) {
    console.error('[server] /reindex 错误:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /health — 健康检查
 */
app.get('/health', (req, res) => {
  const stats = sqliteStore.getStats();
  const vecCount = vectorStore.getVectorCount();

  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    sqlite: stats.documents > 0 ? 'connected' : 'empty',
    vectors: vecCount,
    documents: stats.documents,
    chunks: stats.chunks
  });
});

/**
 * POST /explain-retrieval — 检索解释（调试用）
 */
app.post('/explain-retrieval', async (req, res) => {
  try {
    const { query, task_type, top_k = 5 } = req.body;

    if (!query) {
      return res.status(400).json({ error: 'query 是必填字段' });
    }

    // 路由分析
    const routeResult = task_type
      ? { task_type, ...getRoute(task_type) }
      : routeQuery(query);

    // 路由打分详情
    const routeDetail = task_type ? null : {
      task_type: routeResult.task_type,
      confidence: routeResult.confidence,
      all_scores: routeResult._all_scores
    };

    // 检索
    const { results, meta } = await hybridRetrieve(query, {
      taskType: task_type,
      topK: top_k
    });

    // 嵌入向量预览（前10维）
    let vectorPreview = null;
    try {
      const vec = await embedText(query);
      vectorPreview = {
        dim: vec.length,
        first_10: vec.slice(0, 10)
      };
    } catch {}

    // 添加详细解释
    const detailedResults = results.map(r => ({
      ...r,
      _explanation: {
        why_matched: r.reason,
        score_breakdown: {
          semantic_weight: 0.45,
          fts_weight: 0.20,
          task_match_weight: 0.20,
          priority_weight: 0.10,
          source_type_weight: 0.05
        }
      }
    }));

    res.json({
      query,
      route_analysis: routeDetail,
      applied_filters: routeResult.filters,
      retrieval_meta: {
        total_candidates: meta.total_candidates,
        fts_count: meta.fts_count,
        vector_count: meta.vector_count,
        elapsed_ms: meta.elapsed_ms
      },
      query_vector: vectorPreview,
      results: detailedResults
    });
  } catch (err) {
    console.error('[server] /explain-retrieval 错误:', err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * GET /stats — 索引统计
 */
app.get('/stats', (req, res) => {
  const stats = getIndexStats();
  res.json(stats);
});

/**
 * GET /routes — 路由信息
 */
app.get('/routes', (req, res) => {
  const types = getTaskTypes();
  const routes = {};
  for (const t of types) {
    routes[t] = getRoute(t);
  }
  res.json({ task_types: types, routes });
});

// ========== 启动 ==========

export function startServer(port = PORT) {
  app.listen(port, () => {
    console.log(`[rag-service] 知识检索服务已启动`);
    console.log(`[rag-service] 端口: ${port}`);
    console.log(`[rag-service] 接口:`);
    console.log(`  POST /retrieve           混合检索`);
    console.log(`  POST /reindex            重建索引`);
    console.log(`  GET  /health             健康检查`);
    console.log(`  POST /explain-retrieval  检索解释`);
    console.log(`  GET  /stats              索引统计`);
    console.log(`  GET  /routes             路由信息`);
  });
  return app;
}

// 直接运行时启动
if (process.argv[1] && (process.argv[1].endsWith('server.js') || process.argv[1].endsWith('rag\\src\\server.js'))) {
  // 启动前先检查是否有索引数据
  const stats = sqliteStore.getStats();
  if (stats.documents === 0) {
    console.log('[rag-service] 检测到空索引，自动重建中...');
    buildFullIndex().then(result => {
      console.log(`[rag-service] 索引重建完成: ${result.documents} 文档, ${result.chunks} chunks, ${result.vectors} 向量`);
      startServer();
    }).catch(err => {
      console.error('[rag-service] 索引重建失败:', err);
      startServer();
    });
  } else {
    startServer();
  }
}
