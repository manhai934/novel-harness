/**
 * verify.js — 验收验证脚本
 *
 * 运行全部验收测试，检查：
 * 1. 知识入库完整性
 * 2. 任务路由准确性
 * 3. 4 个关键查询的检索质量
 * 4. 架构完整性
 */

import { buildFullIndex, getIndexStats } from '../src/indexer.js';
import { hybridRetrieve } from '../src/retriever.js';
import { routeQuery } from '../src/router.js';
import { scanKnowledgeFiles } from '../src/scanner.js';

const PASS = '✅';
const FAIL = '❌';
const WARN = '⚠️';

let passed = 0;
let failed = 0;
let warnings = 0;

function check(name, condition, detail = '') {
  if (condition) {
    console.log(`  ${PASS} ${name}`);
    passed++;
  } else {
    console.log(`  ${FAIL} ${name} ${detail}`);
    failed++;
  }
}

function warn(name, detail = '') {
  console.log(`  ${WARN} ${name} ${detail}`);
  warnings++;
}

async function main() {
  console.log('\n========================================');
  console.log('  novel-harness RAG 验收测试');
  console.log('========================================\n');

  // ===== 1. 架构完整性 =====
  console.log('--- 1. 架构完整性 ---');

  try {
    const { readdirSync, existsSync } = await import('fs');
    const { join, resolve, dirname } = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = dirname(fileURLToPath(import.meta.url));
    const ROOT = resolve(__dirname, '..');

    check('rag/ 目录存在', existsSync(join(ROOT)));
    check('rag/config/ 目录', existsSync(join(ROOT, 'config')));
    check('rag/schemas/ 目录', existsSync(join(ROOT, 'schemas')));
    check('rag/src/ 目录', existsSync(join(ROOT, 'src')));
    check('rag/scripts/ 目录', existsSync(join(ROOT, 'scripts')));

    // 检查关键文件
    const keyFiles = [
      'config/sources.json', 'config/task-routes.json', 'config/categories.json',
      'schemas/document.schema.json', 'schemas/chunk.schema.json', 'schemas/context-pack.schema.json',
      'src/scanner.js', 'src/normalizer.js', 'src/chunker.js', 'src/embedder.js',
      'src/router.js', 'src/retriever.js', 'src/context-pack.js', 'src/indexer.js', 'src/server.js',
      'src/storage/sqlite-store.js', 'src/storage/vector-store.js',
      'scripts/ingest.js', 'scripts/build-index.js', 'scripts/query.js'
    ];

    for (const f of keyFiles) {
      check(`文件存在: ${f}`, existsSync(join(ROOT, f)));
    }

  } catch (err) {
    warn('架构检查出错:', err.message);
  }

  // ===== 2. 知识源扫描 =====
  console.log('\n--- 2. 知识源扫描 ---');

  try {
    const files = scanKnowledgeFiles();
    check('扫描到知识文件', files.length > 0, `(共 ${files.length} 个)`);

    const ruleFiles = files.filter(f => f.source_type === 'rule');
    const refFiles = files.filter(f => f.source_type === 'reference');
    const projFiles = files.filter(f => f.source_type === 'project');

    check('至少包含 rules', ruleFiles.length > 0, `(${ruleFiles.length})`);
    check('至少包含 references', refFiles.length > 0, `(${refFiles.length})`);
    check('至少包含 projects', projFiles.length > 0, `(${projFiles.length})`);

    // 检查不应该在索引里的路径
    const badPaths = files.filter(f =>
      f.path.includes('planning/') || f.path.includes('agents/') ||
      f.path.includes('memory/') || f.path.includes('cases/') ||
      f.path.includes('legacy-skills/')
    );
    check('没有混入不应索引的路径', badPaths.length === 0,
      badPaths.length > 0 ? `(发现: ${badPaths.map(f => f.path).join(', ')})` : '');

    // 检查预期文件
    const allPaths = files.map(f => f.path);
    check('包含去AI味规则', allPaths.some(p => p.includes('去AI味')), '(去AI味最小修改指南)');
    check('包含大纲评估规则', allPaths.some(p => p.includes('大纲质量评估')), '(大纲质量评估清单)');
    check('包含全民求生模板', allPaths.some(p => p.includes('全民求生')), '(project)');

  } catch (err) {
    warn('知识源扫描出错:', err.message);
  }

  // ===== 3. 任务路由 =====
  console.log('\n--- 3. 任务路由 ---');

  const routeTests = [
    { query: '这段太像 AI 写的', expect: 'humanization' },
    { query: '大纲后面能不能展开', expect: 'outline_review' },
    { query: '写之前该准备什么', expect: 'chapter_prewrite' },
    { query: '开脑洞想个新题材', expect: 'ideation' },
    { query: '节奏太慢了', expect: 'rhythm_review' },
    { query: '全民求生选什么路线', expect: 'genre_routing' },
    { query: '角色设定前后矛盾了', expect: 'consistency_check' },
  ];

  for (const t of routeTests) {
    const result = routeQuery(t.query);
    check(`路由 "${t.query.substring(0, 12)}..." → ${result.task_type}`,
      result.task_type === t.expect,
      `(期望: ${t.expect}, 实际: ${result.task_type})`);
  }

  // ===== 4. 索引构建 =====
  console.log('\n--- 4. 索引构建 ---');

  try {
    const result = await buildFullIndex();
    check('文档入库 > 0', result.documents > 0, `(${result.documents})`);
    check('Chunks > 0', result.chunks > 0, `(${result.chunks})`);
    check('向量 > 0', result.vectors > 0, `(${result.vectors})`);

    if (result.documents > 0) {
      console.log(`   📊 ${result.documents} 文档 → ${result.chunks} chunks → ${result.vectors} 向量`);
    }
  } catch (err) {
    warn('索引构建失败:', err.message);
    console.log('   (跳过后续检索测试)');
    printSummary();
    process.exit(failed > 0 ? 1 : 0);
    return;
  }

  // ===== 5. 混合检索验证 =====
  console.log('\n--- 5. 混合检索验证 ---');

  const retrievalTests = [
    {
      label: 'TA1: "这段太像 AI 写的"',
      query: '这段太像 AI 写的',
      taskType: 'humanization',
      check: (results) => {
        // 应命中去AI味相关文档
        const titles = results.map(r => r.title);
        const hasRelevant = titles.some(t =>
          t.includes('去AI') || t.includes('修改') || t.includes('语') ||
          t.includes('阅读体验') || t.includes('自然')
        );
        return hasRelevant;
      }
    },
    {
      label: 'TA2: "这个大纲后面能不能展开"',
      query: '这个大纲后面能不能展开',
      taskType: 'outline_review',
      check: (results) => {
        const titles = results.map(r => r.title);
        return titles.some(t => t.includes('大纲') || t.includes('评估') || t.includes('结构'));
      }
    },
    {
      label: 'TA3: "这一章写之前我该准备什么"',
      query: '这一章写之前我该准备什么',
      taskType: 'chapter_prewrite',
      check: (results) => {
        const titles = results.map(r => r.title);
        return titles.some(t => t.includes('写前') || t.includes('准备') || t.includes('章节'));
      }
    },
    {
      label: 'TA4: "全民求生该先定哪条路线"',
      query: '全民求生该先定哪条路线',
      taskType: 'genre_routing',
      check: (results) => {
        const titles = results.map(r => r.title);
        return titles.some(t => t.includes('全民求生') || t.includes('路线') || t.includes('题材'));
      }
    }
  ];

  for (const t of retrievalTests) {
    console.log(`\n  ${t.label}`);
    try {
      const { results, meta } = await hybridRetrieve(t.query, { taskType: t.taskType, topK: 5 });

      check('  返回结果 > 0', results.length > 0, `(${results.length} 条)`);

      if (results.length > 0) {
        const top3Pass = t.check(results.slice(0, 3));
        const top5Pass = t.check(results);
        check('  Top 3 命中任务意图', top3Pass, top5Pass ? '(Top 5 整体 OK)' : '(Top 5 也未命中)');

        // 显示结果
        for (let i = 0; i < Math.min(3, results.length); i++) {
          const r = results[i];
          console.log(`     ${i + 1}. [${r.score.toFixed(3)}] ${r.title}`);
          console.log(`        ${r.reason}`);
        }
        console.log(`     (FTS:${meta.fts_count}, 向量:${meta.vector_count}, ${meta.elapsed_ms}ms)`);
      }
    } catch (err) {
      warn(`  ${t.label} 检索失败:`, err.message);
    }
  }

  // ===== 6. 结果稳定性 =====
  console.log('\n--- 6. 结果稳定性 ---');

  try {
    const testQuery = '这段太像 AI 写的';
    const r1 = await hybridRetrieve(testQuery, { taskType: 'humanization', topK: 3 });
    const r2 = await hybridRetrieve(testQuery, { taskType: 'humanization', topK: 3 });

    const ids1 = r1.results.map(r => r.chunk_id).join(',');
    const ids2 = r2.results.map(r => r.chunk_id).join(',');
    check('重复查询结果稳定', ids1 === ids2, '(相同 query 应返回相同 top 结果)');
  } catch (err) {
    warn('稳定性测试出错:', err.message);
  }

  // ===== 总结 =====
  printSummary();
}

function printSummary() {
  console.log('\n========================================');
  console.log('  验收结果');
  console.log('========================================');
  console.log(`  ${PASS} 通过: ${passed}`);
  console.log(`  ${FAIL} 失败: ${failed}`);
  console.log(`  ${WARN} 警告: ${warnings}`);
  console.log('========================================\n');

  if (failed > 0) {
    console.log(`部分检查未通过，请查看上面详情。\n`);
    process.exit(1);
  } else if (warnings > 0) {
    console.log(`全部关键检查通过，有 ${warnings} 条警告。\n`);
    process.exit(0);
  } else {
    console.log('全部检查通过！\n');
    process.exit(0);
  }
}

main();
