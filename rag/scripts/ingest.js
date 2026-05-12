/**
 * ingest.js — 知识入库 CLI
 *
 * 用法：
 *   node scripts/ingest.js                  # 扫描并入库所有知识
 *   node scripts/ingest.js --dry-run        # 仅扫描，不写入
 *   node scripts/ingest.js --verbose        # 显示详细信息
 */

import { scanKnowledgeFiles, loadSourceConfig } from '../src/scanner.js';
import { normalizeDocument } from '../src/normalizer.js';
import { chunkMarkdown } from '../src/chunker.js';

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const verbose = args.includes('--verbose');

async function main() {
  console.log('=== 知识入库 ===\n');

  // 扫描文件
  const files = scanKnowledgeFiles();
  console.log(`扫描到 ${files.length} 个知识文件\n`);

  if (dryRun) {
    for (const f of files) {
      console.log(`  [${f.source_type}] ${f.path}`);
    }
    console.log(`\n[DRY RUN] 共 ${files.length} 个文件，未写入`);
    return;
  }

  // 处理每个文件
  let docCount = 0;
  let chunkCount = 0;

  for (const file of files) {
    const doc = normalizeDocument(file.path, file.source_type);
    if (!doc) continue;

    docCount++;
    const chunks = chunkMarkdown(doc._raw_content);
    chunkCount += chunks.length;

    if (verbose) {
      console.log(`\n📄 ${doc.title} (${doc.source_type})`);
      console.log(`   路径: ${file.path}`);
      console.log(`   分类: ${doc.category}`);
      console.log(`   阶段: ${doc.stage.join(', ')}`);
      console.log(`   标签: ${doc.tags.slice(0, 5).join(', ')}`);
      console.log(`   Chunks: ${chunks.length}`);
      for (const c of chunks) {
        console.log(`     - [${c.chunk_type}] ${c.title} (${c.text.length}字)`);
      }
    } else {
      process.stdout.write('.');
      if (docCount % 20 === 0) console.log(` ${docCount}`);
    }
  }

  if (!verbose) console.log(` ${docCount}`);

  console.log(`\n入库完成!`);
  console.log(`  文档: ${docCount}`);
  console.log(`  Chunks: ${chunkCount}`);
  console.log(`\n运行 "node scripts/build-index.js" 来构建索引`);
}

main().catch(err => {
  console.error('入库失败:', err);
  process.exit(1);
});
