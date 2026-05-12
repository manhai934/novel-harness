/**
 * scanner.js — 知识源扫描器
 *
 * 职责：
 * - 按 sources.json 中的 include/exclude 模式扫描文件系统
 * - 返回匹配的知识文件列表
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, resolve, dirname, basename } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');

/**
 * 加载 sources.json 配置
 */
export function loadSourceConfig() {
  const configPath = join(PROJECT_ROOT, 'rag/config/sources.json');
  return JSON.parse(readFileSync(configPath, 'utf-8'));
}

/**
 * 将 glob 模式转为正则
 */
function globToRegex(pattern) {
  const normalized = pattern.replace(/\\/g, '/');
  let regexStr = normalized
    .replace(/\./g, '\\.')
    .replace(/\*\*/g, '___DBL___')
    .replace(/\*/g, '[^/]*')
    .replace(/___DBL___/g, '.*');
  return new RegExp(`^${regexStr}$`);
}

/**
 * 递归收集文件
 */
function collectFiles(dir, includePattern, excludePatterns) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return results;
  }

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    const relPath = fullPath.replace(/\\/g, '/');

    // 排除 .git, node_modules 等
    if (entry.name.startsWith('.') && entry.name !== '.harness') continue;
    if (entry.name === 'node_modules') continue;

    if (entry.isDirectory()) {
      results.push(...collectFiles(fullPath, includePattern, excludePatterns));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      // 检查是否匹配 include 模式
      if (!includePattern.test(relPath)) continue;

      // 检查是否在 exclude 中
      let excluded = false;
      for (const ex of excludePatterns) {
        if (ex.test(relPath)) { excluded = true; break; }
      }
      if (excluded) continue;

      results.push(relPath.replace(PROJECT_ROOT.replace(/\\/g, '/') + '/', ''));
    }
  }

  return results;
}

/**
 * 扫描知识文件
 * @returns {Array<{path: string, source_type: string}>}
 */
export function scanKnowledgeFiles() {
  const config = loadSourceConfig();

  const includePatterns = {};
  for (const [type, pattern] of Object.entries(config.source_types)) {
    includePatterns[type] = globToRegex(join(PROJECT_ROOT, pattern).replace(/\\/g, '/'));
  }

  const excludeRegexes = config.exclude_patterns.map(p =>
    globToRegex(p.startsWith('**') ? join(PROJECT_ROOT, p).replace(/\\/g, '/') : join(PROJECT_ROOT, p).replace(/\\/g, '/'))
  );

  const allFiles = [];
  const seen = new Set();

  for (const [sourceType, includeRegex] of Object.entries(includePatterns)) {
    const matches = collectFiles(PROJECT_ROOT, includeRegex, excludeRegexes);
    for (const relPath of matches) {
      if (seen.has(relPath)) continue;
      seen.add(relPath);

      allFiles.push({
        path: relPath,
        source_type: sourceType
      });
    }
  }

  return allFiles;
}
