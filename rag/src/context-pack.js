/**
 * context-pack.js — Context Pack 构建器
 *
 * 职责：
 * - 将检索结果组装成 Agent 可直接消费的 ContextPack
 * - 按任务类型组织知识结构
 * - 优化呈现顺序：规则优先、高优先级优先
 */

/**
 * 构建 Context Pack
 * @param {string} query - 原始查询
 * @param {string} taskType - 路由后的任务类型
 * @param {object} filterInfo - 使用的过滤条件
 * @param {Array} results - 检索结果
 * @param {object} meta - 检索元信息
 * @returns {object} ContextPack
 */
export function buildContextPack(query, taskType, filterInfo, results, meta) {
  // 按 source_type 分组排序: rule > reference > project
  const sorted = [...results].sort((a, b) => {
    const typeOrder = { rule: 0, reference: 1, project: 2 };
    const ta = typeOrder[a.source_type] || 3;
    const tb = typeOrder[b.source_type] || 3;
    if (ta !== tb) return ta - tb;
    return b.score - a.score;
  });

  // 格式化每个结果
  const formattedResults = sorted.map(r => ({
    chunk_id: r.chunk_id,
    title: r.title,
    score: r.score,
    reason: r.reason,
    snippet: r.snippet,
    source_path: r.source_path,
    source_type: r.source_type,
    category: r.category,
    tags: r.tags || []
  }));

  // 按 source_type 总结知识分布
  const sourceBreakdown = {};
  for (const r of formattedResults) {
    const st = r.source_type;
    if (!sourceBreakdown[st]) sourceBreakdown[st] = 0;
    sourceBreakdown[st]++;
  }

  // 生成简短的知识概要
  const knowledgeSummary = generateSummary(query, taskType, formattedResults);

  return {
    task_type: taskType,
    query: query,
    filters: filterInfo || {},
    results: formattedResults,
    knowledge_summary: knowledgeSummary,
    source_breakdown: sourceBreakdown,
    meta: meta || {}
  };
}

/**
 * 生成简短的知识概要摘要
 */
function generateSummary(query, taskType, results) {
  if (results.length === 0) {
    return '未检索到相关知识。';
  }

  const topSources = results.slice(0, 3).map(r => `"${r.title}"`);

  const stageMap = {
    humanization: '语言自然化和去AI味',
    outline_review: '大纲评估和结构检查',
    chapter_prewrite: '写前准备和章节规划',
    ideation: '构思和灵感激发',
    consistency_check: '一致性和逻辑检查',
    rhythm_review: '阅读体验和节奏优化',
    genre_routing: '题材选型和路线确定'
  };

  const stageHint = stageMap[taskType] || taskType;

  return `查询「${query}」匹配到 ${results.length} 条知识，类型为「${stageHint}」。
其中知识来源：${topSources.join('、')}。`;
}

/**
 * 生成纯文本版的 context pack（供 Agent prompt 直接注入）
 */
export function contextPackToText(contextPack) {
  const lines = [];
  lines.push(`## 知识上下文包`);
  lines.push(`任务类型：${contextPack.task_type}`);
  lines.push(`查询：${contextPack.query}`);
  lines.push(`知识来源分布：${JSON.stringify(contextPack.source_breakdown)}`);
  lines.push(``);

  if (contextPack.results.length === 0) {
    lines.push(`> ⚠️ 未检索到相关知识。`);
    lines.push(``);
    return lines.join('\n');
  }

  lines.push(`### 相关知识`);

  for (let i = 0; i < contextPack.results.length; i++) {
    const r = contextPack.results[i];
    lines.push(``);
    lines.push(`**${i + 1}. ${r.title}**  (相关度: ${r.score})`);
    lines.push(`- 来源: \`${r.source_path}\``);
    lines.push(`- 类型: ${r.source_type}`);
    if (r.tags && r.tags.length > 0) {
      lines.push(`- 标签: ${r.tags.join(', ')}`);
    }
    lines.push(`- 检索依据: ${r.reason}`);
    lines.push(``);
    lines.push(`> ${r.snippet}`);
    lines.push(``);
    lines.push(`---`);
  }

  return lines.join('\n');
}

export default { buildContextPack, contextPackToText };
