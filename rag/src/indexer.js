/**
 * indexer.js — 索引编排器
 *
 * 职责：
 * - 完整编排：扫描 → 标准化 → 切块 → 嵌入 → 存储
 * - 支持全量重建和增量更新
 */

import * as scanner from './scanner.js';
import { normalizeDocument } from './normalizer.js';
import { chunkMarkdown } from './chunker.js';
import { embedBatch, buildVocabulary } from './embedder.js';
import * as sqliteStore from './storage/sqlite-store.js';
import * as vectorStore from './storage/vector-store.js';

/**
 * 全量构建索引
 * @returns {Promise<{documents: number, chunks: number, vectors: number}>}
 */
export async function buildFullIndex() {
  console.log('[indexer] === 开始全量构建索引 ===');

  // 1. 清空所有旧数据
  sqliteStore.clearAll();
  vectorStore.clearVectors();
  console.log('[indexer] 已清空旧数据');

  // 2. 初始化数据库
  sqliteStore.initialize();

  // 3. 扫描知识文件
  const files = scanner.scanKnowledgeFiles();
  console.log(`[indexer] 扫描到 ${files.length} 个知识文件`);

  let docCount = 0;
  let chunkCount = 0;
  const allChunks = [];
  const allVectors = [];

  // 4. 处理每个文件
  for (const file of files) {
    try {
      // 标准化文档
      const doc = normalizeDocument(file.path, file.source_type);
      if (!doc) continue;

      docCount++;
      sqliteStore.upsertDocument(doc);

      // 切分 chunk
      const rawSections = chunkMarkdown(doc._raw_content);

      const chunks = rawSections.map((section, i) => ({
        chunk_id: `${doc.doc_id}#${section.section_ref}`,
        doc_id: doc.doc_id,
        title: section.title,
        chunk_type: section.chunk_type,
        text: section.text,
        category: doc.category,
        stage: doc.stage,
        scope: doc.scope,
        tags: doc.tags,
        priority: doc.priority,
        source_type: doc.source_type,
        source_path: doc.source_path,
        heading_level: section.heading_level
      }));

      // 批量插入到 SQLite
      sqliteStore.insertChunks(chunks);
      chunkCount += chunks.length;
      allChunks.push(...chunks);

      if (chunks.length > 0) {
        console.log(`  [${doc.source_type}] ${doc.title} → ${chunks.length} chunks`);
      }
    } catch (err) {
      console.warn(`[indexer] 处理文件失败: ${file.path}`, err.message);
    }
  }

  console.log(`[indexer] 文档: ${docCount}, Chunks: ${chunkCount}`);

  // 4.5 构建嵌入词表
  if (allChunks.length > 0) {
    buildVocabulary(allChunks.map(c => c.title + ' ' + c.text));
  }

  // 5. 生成向量嵌入
  if (allChunks.length > 0) {
    console.log('[indexer] 开始生成 embeddings...');
    const batchSize = 10;

    for (let i = 0; i < allChunks.length; i += batchSize) {
      const batch = allChunks.slice(i, i + batchSize);
      const texts = batch.map(c => c.title + ' ' + c.text.substring(0, 500));

      try {
        const embeddings = await embedBatch(texts);
        for (let j = 0; j < batch.length; j++) {
          allVectors.push({
            chunk_id: batch[j].chunk_id,
            vector: embeddings[j]
          });
        }
      } catch (err) {
        console.warn(`[indexer] 批次 ${i} 嵌入失败:`, err.message);
      }

      if ((i + batchSize) % 50 === 0 || i + batchSize >= allChunks.length) {
        console.log(`[indexer] 嵌入进度: ${Math.min(i + batchSize, allChunks.length)}/${allChunks.length}`);
      }
    }

    // 存储向量
    vectorStore.insertVectors(allVectors);
    console.log(`[indexer] 向量存储完成: ${allVectors.length} 个`);
  }

  const stats = sqliteStore.getStats();
  console.log(`[indexer] === 索引构建完成 ===`);
  console.log(`[indexer] 文档: ${stats.documents}, Chunks: ${stats.chunks}, 向量: ${allVectors.length}`);

  return {
    documents: stats.documents,
    chunks: stats.chunks,
    vectors: allVectors.length
  };
}

/**
 * 获取索引统计
 */
export function getIndexStats() {
  const stats = sqliteStore.getStats();
  return {
    ...stats,
    vectors: vectorStore.getVectorCount()
  };
}

export default { buildFullIndex, getIndexStats };
