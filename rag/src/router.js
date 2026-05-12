/**
 * router.js — 任务路由器
 *
 * 职责：
 * - 接收用户查询文本
 * - 判断最适合的任务类型
 * - 返回 task_type + 对应的 metadata 过滤条件
 *
 * 当前实现：关键词匹配 + 规则路由
 * 后续可替换为：轻量分类模型 / few-shot 分类
 */

import { readFileSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '../..');

let routeConfig = null;

/**
 * 加载路由配置
 */
function getRouteConfig() {
  if (routeConfig) return routeConfig;
  const configPath = join(PROJECT_ROOT, 'rag/config/task-routes.json');
  routeConfig = JSON.parse(readFileSync(configPath, 'utf-8'));
  return routeConfig;
}

/**
 * 计算查询与任务类型的匹配分数
 */
function scoreTaskType(query, route) {
  let score = 0;
  const q = query.toLowerCase();

  for (const keyword of route.keywords) {
    if (q.includes(keyword.toLowerCase())) {
      score += 1;
    }
  }

  // 归一化
  return route.keywords.length > 0 ? score / route.keywords.length : 0;
}

/**
 * 路由查询到任务类型
 * @param {string} query - 用户查询
 * @returns {{
 *   task_type: string,
 *   confidence: number,
 *   categories: string[],
 *   stages: string[],
 *   filters: object
 * }}
 */
export function routeQuery(query) {
  const config = getRouteConfig();
  const routes = config.routes;

  let bestMatch = 'humanization';  // 默认回退
  let bestScore = 0;
  const scores = {};

  for (const [taskType, route] of Object.entries(routes)) {
    const score = scoreTaskType(query, route);
    scores[taskType] = score;
    if (score > bestScore) {
      bestScore = score;
      bestMatch = taskType;
    }
  }

  const matchedRoute = routes[bestMatch];

  return {
    task_type: bestMatch,
    confidence: bestScore,
    categories: matchedRoute.categories,
    stages: matchedRoute.stages,
    filters: {
      categories: matchedRoute.categories,
      stages: matchedRoute.stages
    },
    _all_scores: scores  // 调试用
  };
}

/**
 * 获取所有任务类型列表
 */
export function getTaskTypes() {
  const config = getRouteConfig();
  return Object.keys(config.routes);
}

/**
 * 获取特定任务类型的路由信息
 */
export function getRoute(taskType) {
  const config = getRouteConfig();
  return config.routes[taskType] || null;
}

export default { routeQuery, getTaskTypes, getRoute };
