/**
 * normalizer.js — 文档标准化器
 *
 * 职责：
 * - 读取 Markdown 文件原始内容
 * - 从路径和内容中提取 metadata
 * - 输出统一的 document 结构
 */

import { readFileSync } from 'fs';
import { join, resolve, dirname, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../../');

/**
 * source_type 到 category 的映射规则
 */
const SOURCE_TO_CATEGORY = {
  'human-linguistics': {
    rules: 'common.humanization',
    references: 'common.language'
  },
  'plot-review': {
    rules: 'common.outline_review',
    references: 'common.consistency'
  },
  'plot-ideation': {
    rules: 'common.ideation',
    references: 'common.ideation'
  },
  // 特殊文件名映射
  FILE_CATEGORY_OVERRIDES: {
    '章节写前准备清单': 'common.prewrite',
    '大纲质量评估清单': 'common.outline_review',
    '状态一致性补充清单': 'common.consistency',
    '去AI味最小修改指南': 'common.humanization',
    '句式节奏档案': 'common.rhythm',
    '阅读体验与章节润色检查': 'common.rhythm',
  },
  'rhythm-review': {
    rules: 'common.rhythm',
    references: 'common.rhythm'
  },
  'game-datafied': {
    rules: 'common.outline',
    references: 'common.outline'
  },
  'projects': {
    project: 'common.project'
  }
};

/**
 * 从相对路径中提取技能目录名
 */
function extractSkillName(relPath) {
  const parts = relPath.replace(/\\/g, '/').split('/');
  // .harness/skills/{skill_name}/...
  const skillsIdx = parts.indexOf('skills');
  if (skillsIdx >= 0 && skillsIdx + 1 < parts.length) {
    return parts[skillsIdx + 1];
  }
  return null;
}

/**
 * 确定 stage（适用阶段）
 */
function inferStage(relPath, content) {
  const stages = [];
  const lower = content.toLowerCase();
  const pathLower = relPath.toLowerCase();

  // 从路径推断
  if (pathLower.includes('ideation') || pathLower.includes('灵感') || pathLower.includes('构思')) {
    stages.push('ideation');
  }
  if (pathLower.includes('outline') || pathLower.includes('大纲') || pathLower.includes('结构')) {
    stages.push('outline');
  }
  if (pathLower.includes('prewrite') || pathLower.includes('写前') || pathLower.includes('准备')) {
    stages.push('prewrite');
  }
  if (pathLower.includes('rhythm') || pathLower.includes('节奏') || pathLower.includes('润色') || pathLower.includes('阅读体验')) {
    stages.push('drafting', 'revision');
  }
  if (pathLower.includes('human') || pathLower.includes('去ai') || pathLower.includes('修改') || pathLower.includes('自然')) {
    stages.push('revision');
  }
  if (pathLower.includes('review') || pathLower.includes('审查') || pathLower.includes('评估') || pathLower.includes('审稿')) {
    stages.push('review');
  }

  // 从内容推断
  if (lower.includes('大纲') || lower.includes('骨架') || lower.includes('结构评估')) {
    if (!stages.includes('outline')) stages.push('outline');
    if (!stages.includes('review')) stages.push('review');
  }
  if (lower.includes('写前') || lower.includes('准备') || lower.includes('开始写')) {
    if (!stages.includes('prewrite')) stages.push('prewrite');
  }
  if (lower.includes('修改') || lower.includes('润色') || lower.includes('去ai') || lower.includes('总结腔')) {
    if (!stages.includes('revision')) stages.push('revision');
  }

  // 默认
  if (stages.length === 0) {
    stages.push('drafting', 'review');
  }

  return [...new Set(stages)];
}

/**
 * 从路径推断 doc_id
 */
function inferDocId(relPath) {
  const parts = relPath.replace(/\\/g, '/').split('/');
  const fileName = basename(parts[parts.length - 1], '.md');

  const skillName = extractSkillName(relPath);
  if (skillName) {
    return `${skillName}.${fileName}`;
  }

  // projects
  if (relPath.startsWith('.harness/projects/')) {
    return `project.${fileName}`;
  }

  return fileName;
}

/**
 * 从路径推断 category
 */
function inferCategory(relPath) {
  const path = relPath.replace(/\\/g, '/');
  const fileName = basename(relPath, '.md');

  // 文件名覆盖（处理特殊文档映射）
  const overrides = SOURCE_TO_CATEGORY.FILE_CATEGORY_OVERRIDES || {};
  if (overrides[fileName]) {
    return overrides[fileName];
  }

  // projects
  if (path.startsWith('.harness/projects/')) {
    return 'common.project';
  }

  const skillName = extractSkillName(relPath);
  if (!skillName) return 'common';

  const isRule = path.includes('/rules/');
  const isRef = path.includes('/references/');

  const mapping = SOURCE_TO_CATEGORY[skillName];
  if (mapping) {
    if (isRule && mapping.rules) return mapping.rules;
    if (isRef && mapping.references) return mapping.references;
  }

  return 'common';
}

/**
 * 推断 scope
 */
function inferScope(relPath, priority = 3) {
  if (relPath.startsWith('.harness/projects/')) {
    return 'project';
  }
  return 'common';
}

/**
 * 提取标签
 */
function inferTags(relPath, content) {
  const tags = [];
  const path = relPath.replace(/\\/g, '/');
  const fileName = basename(relPath, '.md');

  // 从文件名提取标签
  tags.push(fileName);

  // 从路径提取
  const skillName = extractSkillName(relPath);
  if (skillName) tags.push(skillName);

  // 从内容标题提取
  const titleMatch = content.match(/^#\s+(.+)/m);
  if (titleMatch) {
    const title = titleMatch[1].trim();
    tags.push(title);
  }

  return tags;
}

/**
 * 推断优先级 (1=最高, 5=最低)
 */
function inferPriority(relPath) {
  const path = relPath.replace(/\\/g, '/');
  // rule > reference > project
  if (path.includes('/rules/')) return 1;
  if (path.includes('/references/')) return 2;
  if (path.startsWith('.harness/projects/')) return 3;
  return 4;
}

/**
 * 标准化单个文件为 document 对象
 * @param {string} relPath - 相对路径
 * @param {string} sourceType - 源类型 (rule/reference/project)
 * @returns {object} document 对象
 */
export function normalizeDocument(relPath, sourceType) {
  const absPath = join(PROJECT_ROOT, relPath);

  let content = '';
  try {
    content = readFileSync(absPath, 'utf-8');
  } catch (e) {
    console.warn(`[normalizer] 无法读取文件: ${relPath}`, e.message);
    return null;
  }

  // 提取标题
  const titleMatch = content.match(/^#\s+(.+)/m);
  const title = titleMatch ? titleMatch[1].trim() : basename(relPath, '.md');

  const docId = inferDocId(relPath);
  const category = inferCategory(relPath);
  const priority = inferPriority(relPath);
  const tags = inferTags(relPath, content);
  const stage = inferStage(relPath, content);

  return {
    doc_id: docId,
    title,
    source_path: relPath.replace(/\\/g, '/'),
    source_type: sourceType,
    category,
    stage,
    scope: inferScope(relPath, priority),
    tags,
    priority,
    status: 'active',
    _raw_content: content  // 内部传递，不持久化
  };
}

export default { normalizeDocument };
