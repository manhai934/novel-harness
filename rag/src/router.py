"""
router.py — 任务路由器

职责：
- 根据查询文本匹配最合适的任务类型
- 输出路由结果（task_type, categories, stages, filters）
- 支持 7 种写作任务路由
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTES_PATH = PROJECT_ROOT / "rag" / "config" / "task-routes.json"


def _load_routes():
    """加载任务路由配置"""
    try:
        with open(ROUTES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("routes", {})
    except (OSError, json.JSONDecodeError) as e:
        print(f"[router] 加载路由配置失败: {e}")
        return {}


def route_query(query):
    """路由查询到最匹配的任务类型

    通过关键词重叠度评分，选择得分最高的任务类型。

    Args:
        query: 用户查询文本

    Returns:
        dict with task_type, categories, stages, filters, confidence, description
    """
    routes = _load_routes()
    if not routes:
        return {
            "task_type": "general",
            "categories": [],
            "stages": [],
            "filters": {},
            "confidence": 0,
            "description": "",
        }

    query_lower = query.lower()
    query_terms = set(query_lower.split())

    best_match = None
    best_score = -1

    for task_type, route in routes.items():
        keywords = route.get("keywords", [])
        if not keywords:
            continue

        # 计算关键词匹配度
        score = 0
        matched = []

        for kw in keywords:
            kw_lower = kw.lower()
            # 完整关键词匹配
            if kw_lower in query_lower:
                kw_score = len(kw_lower) / max(len(qt) for qt in query_terms) if query_terms else 1
                score += len(kw_lower) * 2
                matched.append(kw)
            # 部分匹配（关键词的每个字都在查询中）
            elif len(kw_lower) >= 3:
                chars = set(kw_lower)
                overlap = sum(1 for c in chars if c in query_lower)
                if overlap / len(chars) > 0.6:
                    score += len(kw_lower) * 0.5
                    matched.append(kw)

        # boost 权重
        boost = route.get("weight_boost", 1.0)
        score *= boost

        if score > best_score:
            best_score = score
            best_match = {
                "task_type": task_type,
                "categories": route.get("categories", []),
                "stages": route.get("stages", []),
                "filters": route.get("filters", {}),
                "confidence": min(1.0, best_score / 20),
                "description": route.get("description", ""),
            }

    if not best_match:
        best_match = {
            "task_type": "general",
            "categories": [],
            "stages": [],
            "filters": {},
            "confidence": 0,
            "description": "",
        }

    return best_match


def get_route(task_type):
    """直接获取指定任务类型的路由配置

    Args:
        task_type: 任务类型名称

    Returns:
        dict with categories, stages, filters, description
    """
    routes = _load_routes()
    route = routes.get(task_type)
    if route:
        return {
            "categories": route.get("categories", []),
            "stages": route.get("stages", []),
            "filters": route.get("filters", {}),
            "description": route.get("description", ""),
        }
    return {
        "categories": [],
        "stages": [],
        "filters": {},
        "description": "",
    }
