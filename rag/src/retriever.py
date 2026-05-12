"""
retriever.py — 混合检索器

职责：
- 混合 FTS + 向量检索
- 轻量重排器
- 输出最终 top-k chunks

重排公式：
   最终分 = 语义分 * 0.35 + FTS分 * 0.15 + 任务匹配分 * 0.30 + priority权重 * 0.12 + source_type权重 * 0.08
"""

import math
from .storage import sqlite_store
from .storage import vector_store
from . import router as router_mod
from .embedder import embed_text

SOURCE_WEIGHTS = {"rule": 1.0, "reference": 0.8, "project": 0.6}


def hybrid_retrieve(query, task_type=None, top_k=5, fts_n=15, vec_n=15):
    """混合检索

    Args:
        query: 查询文本
        task_type: 任务类型（可选，不提供则自动路由）
        top_k: 最终返回数量
        fts_n: FTS 召回数量
        vec_n: 向量召回数量

    Returns:
        dict with results, meta
    """
    import time
    start_time = time.time()
    query_lower = query.lower()

    # 1. 任务路由
    if task_type:
        route_result = {"task_type": task_type, **router_mod.get_route(task_type)}
    else:
        route_result = router_mod.route_query(query)
    task_route = route_result

    # 2. 按任务路由的分类做硬过滤 + FTS 召回
    fts_results = []

    categories = task_route.get("categories", [])
    stages = task_route.get("stages", [])

    if categories:
        filtered = sqlite_store.filter_chunks(categories=categories, stages=stages, top_n=fts_n)
        # 对过滤结果做关键词评分
        for row in filtered:
            text = (row.get("title", "") + " " + row.get("text", "")).lower()
            score = 0
            terms = [t for t in query_lower.split() if len(t) > 0]
            for term in terms:
                if term in text:
                    score -= 1  # FTS rank is negative = better match
            # sub-title match
            title_text = row.get("title", "").lower()
            if any(t in title_text for t in terms):
                score -= 3

            row["fts_score"] = score if score < 0 else -0.1
            fts_results.append(row)

        # 过滤掉得分不够的
        fts_results = [r for r in fts_results if r.get("fts_score", 0) < 0]

    # 如果分类过滤没结果，退回到全库 FTS
    if not fts_results:
        fts_results = sqlite_store.fts_search(query, fts_n)

    fts_map = {}
    for r in fts_results:
        fts_map[r["chunk_id"]] = r

    # 3. 向量召回
    vec_results = []
    try:
        query_vector = embed_text(query)
        vec_results = vector_store.vector_search(query_vector, vec_n)
    except Exception as e:
        print(f"[retriever] 向量检索失败: {e}")

    vec_map = {}
    for r in vec_results:
        vec_map[r["chunk_id"]] = r["score"]

    # 4. 合并候选集
    candidates = {}

    for chunk_id, info in fts_map.items():
        candidates[chunk_id] = {
            "chunk_id": chunk_id,
            "row": info,
            "fts_score": info.get("fts_score"),
            "vec_score": vec_map.get(chunk_id),
        }

    for r in vec_results:
        if r["chunk_id"] not in candidates:
            chunk_data = sqlite_store.get_chunk_by_id(r["chunk_id"])
            if chunk_data:
                candidates[r["chunk_id"]] = {
                    "chunk_id": r["chunk_id"],
                    "row": chunk_data,
                    "fts_score": None,
                    "vec_score": r["score"],
                }

    # 5. 重排
    reranked = []
    for chunk_id, c in candidates.items():
        score = _rerank(c["row"], query_lower, task_route, c["fts_score"], c["vec_score"])
        reason = _build_reason(c["row"], c["fts_score"], c["vec_score"], task_route)
        reranked.append({
            "chunk_id": chunk_id,
            "title": c["row"].get("title", ""),
            "score": score,
            "reason": reason,
            "snippet": c["row"].get("text", "")[:200] + ("..." if len(c["row"].get("text", "")) > 200 else ""),
            "source_path": c["row"].get("source_path", ""),
            "source_type": c["row"].get("source_type", ""),
            "category": c["row"].get("category", ""),
            "tags": c["row"].get("tags", []),
            "priority": c["row"].get("priority", 3),
        })

    reranked.sort(key=lambda x: x["score"], reverse=True)
    top_results = reranked[:top_k]

    elapsed = time.time() - start_time

    return {
        "results": top_results,
        "meta": {
            "total_candidates": len(candidates),
            "fts_count": len(fts_results),
            "vector_count": len(vec_results),
            "elapsed_ms": round(elapsed * 1000),
            "task_type": route_result.get("task_type"),
            "confidence": route_result.get("confidence", 0),
        },
    }


def _rerank(row, query_lower, task_route, fts_score, vector_score):
    """重排"""
    # 归一化 FTS 分数
    if isinstance(fts_score, (int, float)) and fts_score < 0:
        fts_norm = min(1.0, max(0.0, -fts_score / 15))
    else:
        fts_norm = 0.0

    # 归一化向量分数
    if isinstance(vector_score, (int, float)):
        vec_norm = min(1.0, max(0.0, vector_score))
    else:
        vec_norm = 0.2

    # 任务匹配分
    task_match = 0.0
    if task_route:
        cats = task_route.get("categories", [])
        if cats and row.get("category") in cats:
            task_match += 0.5
        stages = task_route.get("stages", [])
        if row.get("stage") and any(s in str(row["stage"]) for s in stages):
            task_match += 0.3

        desc = (task_route.get("description", "") or "").lower()
        query_terms = [t for t in query_lower.split() if len(t) > 1]
        import re
        desc_terms = re.split(r"[：:、，。\s]", desc)
        overlap = sum(1 for qt in query_terms if any(qt in rt for rt in desc_terms))
        task_match += min(overlap * 0.05, 0.2)

    task_match = min(1.0, task_match)

    priority_weight = (6 - (row.get("priority", 3) or 3)) / 5
    source_weight = SOURCE_WEIGHTS.get(row.get("source_type"), 0.5)

    return round(
        vec_norm * 0.35
        + fts_norm * 0.15
        + task_match * 0.30
        + priority_weight * 0.12
        + source_weight * 0.08,
        4,
    )


def _build_reason(row, fts_score, vector_score, task_route):
    """构建 reason 字符串"""
    parts = []
    if isinstance(fts_score, (int, float)) and fts_score < 0:
        parts.append("关键词匹配")
    if isinstance(vector_score, (int, float)) and vector_score > 0.3:
        parts.append("语义接近")
    if task_route and row.get("category") in task_route.get("categories", []):
        parts.append("任务类型命中")
    if row.get("priority", 3) <= 2:
        parts.append("高优先级")
    if row.get("source_type") == "rule":
        parts.append("规则文档")
    if not parts:
        parts.append("综合匹配")
    return " + ".join(parts)
