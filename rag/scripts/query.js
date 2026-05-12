/**
 * query.js — 检索查询 CLI
 *
 * 用法：
 *   node scripts/query.js "这段太像 AI 写的"
 *   node scripts/query.js "这段太像 AI 写的" --task-type humanization
 *   node scripts/query.js "这个大纲后面能不能展开" --task-type outline_review
 *   node scripts/query.js "查询文本" --top-k 3
 *   node scripts/query.js "查询文本" --json
 *   node scripts/query.js --server
 */

import { hybridRetrieve } from '../src/retriever.js';
import { routeQuery } from '../src/router.js';
import { buildContextPack, contextPackToText } from '../src/context-pack.js';

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`用法:
  node scripts/query.js <查询文本> [选项]

选项:
  --task-type <type>  指定任务类型
  --top-k <n>         返回结果数量 (默认 5)
  --json              JSON 格式输出
  --route-only        只显示路由结果

示例:
  node scripts/query.js "这段太像 AI 写的"
  node scripts/query.js "这个大纲后面能不能展开" --task-type outline_review
  node scripts/query.js "写前准备" --top-k 3 --json
`);
    return;
  }

  if (args[0] === '--server') {
    const { startServer } = await import('../src/server.js');
    startServer();
    return;
  }

  // 正确解析参数（提取 --flag 及后一个值，其余为查询文本）
  const flags = {};
  const queryParts = [];
  let i = 0;
  while (i < args.length) {
    if (args[i].startsWith('--')) {
      const flagName = args[i].replace(/^--/, '');
      if (i + 1 < args.length && !args[i + 1].startsWith('--')) {
        flags[flagName] = args[i + 1];
        i += 2;
      } else {
        flags[flagName] = true;
        i += 1;
      }
    } else {
      queryParts.push(args[i]);
      i += 1;
    }
  }

  const query = queryParts.join(' ');
  const taskType = flags['task-type'] || null;
  const topK = parseInt(flags['top-k'] || '5', 10);
  const asJson = flags.hasOwnProperty('json');
  const routeOnly = flags.hasOwnProperty('route-only');

  if (routeOnly) {
    const route = routeQuery(query);
    console.log('\n=== 任务路由 ===');
    console.log(`查询:         "${query}"`);
    console.log(`路由结果:     ${route.task_type}`);
    console.log(`置信度:       ${route.confidence.toFixed(3)}`);
    console.log(`Category:     ${route.categories.join(', ')}`);
    console.log(`Stages:       ${route.stages.join(', ')}`);
    if (asJson) {
      console.log(JSON.stringify(route, null, 2));
    }
    return;
  }

  console.log(`\n查询: "${query}"`);
  if (taskType) console.log(`任务类型: ${taskType}`);
  console.log('');

  const { results, meta } = await hybridRetrieve(query, { taskType, topK });

  const route = taskType ? { task_type: taskType, filters: {} } : routeQuery(query);
  const contextPack = buildContextPack(query, route.task_type, route.filters, results, meta);

  if (asJson) {
    console.log(JSON.stringify(contextPack, null, 2));
    return;
  }

  const text = contextPackToText(contextPack);
  console.log(text);

  console.log(`\n--- 检索元信息 ---`);
  console.log(`候选总数: ${meta.total_candidates}`);
  console.log(`FTS 召回: ${meta.fts_count}`);
  console.log(`向量召回: ${meta.vector_count}`);
  console.log(`耗时: ${meta.elapsed_ms}ms`);
  console.log(`任务类型: ${meta.task_type}`);
}

main().catch(err => {
  console.error('查询失败:', err);
  process.exit(1);
});
