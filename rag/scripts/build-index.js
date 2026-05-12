/**
 * build-index.js — 索引构建 CLI
 *
 * 用法：
 *   node scripts/build-index.js             # 全量构建索引
 *   node scripts/build-index.js --no-vector # 跳过向量（只建 FTS）
 */

import { buildFullIndex, getIndexStats } from '../src/indexer.js';

async function main() {
  console.log('=== 构建知识索引 ===\n');

  const startTime = Date.now();

  const result = await buildFullIndex();

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  console.log(`\n✅ 索引构建完成 (${elapsed}s)`);
  console.log(`  文档:   ${result.documents}`);
  console.log(`  Chunks:  ${result.chunks}`);
  console.log(`  向量:    ${result.vectors}`);

  if (result.chunks === 0) {
    console.log('\n⚠️  警告: 未构建任何 chunk。请先运行 node scripts/ingest.js');
  }
}

main().catch(err => {
  console.error('索引构建失败:', err);
  process.exit(1);
});
