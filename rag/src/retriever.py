"""
retriever.py - 混合检索器。

组合 SQLite FTS、可选向量检索、轻量重排和 source_type 权重，
输出最终 top-k chunks。
"""

from . import router as router_mod
from .embedder import embed_text
from .storage import sqlite_store
from .storage import vector_store

SOURCE_WEIGHTS = {"rule": 1.0, "knowledge": 0.9, "reference": 0.8, "project": 0.6}


def hybrid_retrieve(query, task_type=None, top_k=5, fts_n=15, vec_n=15):
    """执行混合检索，并返回重排后的 top-k chunks。"""
    import time

    start_time = time.time()
    query_lower = query.lower()

    if task_type:
        route_result = {"task_type": task_type, **router_mod.get_route(task_type)}
    else:
        route_result = router_mod.route_query(query)
    task_route = route_result

    fts_results = []
    categories = task_route.get("categories", [])
    stages = task_route.get("stages", [])

    if categories:
        filtered = sqlite_store.filter_chunks(categories=categories, stages=stages, top_n=fts_n)
        for row in filtered:
            text = (row.get("title", "") + " " + row.get("text", "")).lower()
            terms = [term for term in query_lower.split() if term]
            score = 0
            for term in terms:
                if term in text:
                    score -= 1

            title_text = row.get("title", "").lower()
            if any(term in title_text for term in terms):
                score -= 3

            row["fts_score"] = score if score < 0 else -0.1
            fts_results.append(row)

        fts_results = [r for r in fts_results if r.get("fts_score", 0) < 0]

    if not fts_results:
        fts_results = sqlite_store.fts_search(query, fts_n)

    fts_map = {row["chunk_id"]: row for row in fts_results}

    vec_results = []
    try:
        query_vector = embed_text(query)
        vec_results = vector_store.vector_search(query_vector, vec_n)
    except Exception as exc:
        print(f"[retriever] 向量检索失败: {exc}")

    vec_map = {row["chunk_id"]: row["score"] for row in vec_results}

    candidates = {}
    for chunk_id, info in fts_map.items():
        candidates[chunk_id] = {
            "chunk_id": chunk_id,
            "row": info,
            "fts_score": info.get("fts_score"),
            "vec_score": vec_map.get(chunk_id),
        }

    for row in vec_results:
        if row["chunk_id"] in candidates:
            continue

        chunk_data = sqlite_store.get_chunk_by_id(row["chunk_id"])
        if chunk_data:
            candidates[row["chunk_id"]] = {
                "chunk_id": row["chunk_id"],
                "row": chunk_data,
                "fts_score": None,
                "vec_score": row["score"],
            }

    reranked = []
    for chunk_id, candidate in candidates.items():
        row = candidate["row"]
        score = _rerank(row, query_lower, task_route, candidate["fts_score"], candidate["vec_score"])
        reason = _build_reason(row, candidate["fts_score"], candidate["vec_score"], task_route)
        text = row.get("text", "")
        reranked.append({
            "chunk_id": chunk_id,
            "title": row.get("title", ""),
            "score": score,
            "reason": reason,
            "snippet": text[:200] + ("..." if len(text) > 200 else ""),
            "source_path": row.get("source_path", ""),
            "source_type": row.get("source_type", ""),
            "category": row.get("category", ""),
            "tags": row.get("tags", []),
            "priority": row.get("priority", 3),
        })

    reranked.sort(key=lambda x: x["score"], reverse=True)
    elapsed = time.time() - start_time

    return {
        "results": reranked[:top_k],
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
    if isinstance(fts_score, (int, float)) and fts_score < 0:
        fts_norm = min(1.0, max(0.0, -fts_score / 15))
    else:
        fts_norm = 0.0

    if isinstance(vector_score, (int, float)):
        vec_norm = min(1.0, max(0.0, vector_score))
    else:
        vec_norm = 0.2

    task_match = 0.0
    if task_route:
        categories = task_route.get("categories", [])
        if categories and row.get("category") in categories:
            task_match += 0.5

        stages = task_route.get("stages", [])
        if row.get("stage") and any(stage in str(row["stage"]) for stage in stages):
            task_match += 0.3

        description = (task_route.get("description", "") or "").lower()
        query_terms = [term for term in query_lower.split() if len(term) > 1]
        import re

        desc_terms = re.split(r"[：:、，。\s]", description)
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
    if row.get("source_type") == "knowledge":
        parts.append("知识包")
    if not parts:
        parts.append("综合匹配")
    return " + ".join(parts)
