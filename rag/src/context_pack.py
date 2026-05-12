"""
context_pack.py — 上下文包构建器

职责：
- 将检索结果组织为标准化的 context pack
- 生成 knowledge_summary 和 source_breakdown
- 提供 text 格式输出用于 Agent prompt 注入
"""


def build_context_pack(query, retrieval_result, task_type=None, project_hint=None):
    """构建标准化的 context pack

    Args:
        query: 原始查询文本
        retrieval_result: hybrid_retrieve() 返回的结果
        task_type: 任务类型
        project_hint: 项目提示（保留字段）

    Returns:
        dict — 符合 context-pack.schema.json
    """
    results = retrieval_result.get("results", [])
    meta = retrieval_result.get("meta", {})

    # 按 source_type 排序：rule > reference > project
    type_order = {"rule": 0, "reference": 1, "project": 2}
    sorted_results = sorted(results, key=lambda r: type_order.get(r.get("source_type", ""), 3))

    # knowledge_summary
    top_sources = [r.get("title", "") for r in sorted_results[:5]]
    knowledge_summary = f"检索到 {len(sorted_results)} 条相关知识点"
    if top_sources:
        knowledge_summary += "，涉及: " + "、".join(top_sources)

    # source_breakdown
    source_breakdown = {"rule": 0, "reference": 0, "project": 0}
    for r in sorted_results:
        st = r.get("source_type", "")
        if st in source_breakdown:
            source_breakdown[st] += 1

    context_pack = {
        "task_type": task_type or meta.get("task_type", "general"),
        "query": query,
        "project_hint": project_hint or "",
        "filters": {
            "categories": [],
            "stages": [],
        },
        "results": [
            {
                "chunk_id": r["chunk_id"],
                "title": r["title"],
                "score": r["score"],
                "reason": r["reason"],
                "snippet": r["snippet"],
                "source_path": r["source_path"],
                "source_type": r["source_type"],
                "category": r.get("category", ""),
                "tags": r.get("tags", []),
            }
            for r in sorted_results
        ],
        "knowledge_summary": knowledge_summary,
        "source_breakdown": source_breakdown,
        "meta": {
            "total_candidates": meta.get("total_candidates", 0),
            "elapsed_ms": meta.get("elapsed_ms", 0),
            "task_type": meta.get("task_type", ""),
            "confidence": meta.get("confidence", 0),
        },
    }

    return context_pack


def context_pack_to_text(context_pack):
    """将 context pack 格式化为纯文本，用于 Agent prompt 注入

    输出格式：
    ---
    [知识上下文]
    任务类型: {task_type}
    查询: {query}
    来源: 规则 x N, 参考 x N, 项目 x N

    1. [{source_type}] {title} (相关性: {score})
       {reason}
       {snippet}
    ...
    ---
    """
    lines = []
    lines.append("---")
    lines.append("[知识上下文]")
    lines.append(f"任务类型: {context_pack.get('task_type', 'general')}")
    lines.append(f"查询: {context_pack.get('query', '')}")

    sb = context_pack.get("source_breakdown", {})
    parts = []
    for st in ("rule", "reference", "project"):
        names = {"rule": "规则", "reference": "参考", "project": "项目"}
        count = sb.get(st, 0)
        if count > 0:
            parts.append(f"{names.get(st, st)} x {count}")
    lines.append(f"来源: {', '.join(parts) if parts else '无'}")

    if context_pack.get("knowledge_summary"):
        lines.append(f"摘要: {context_pack['knowledge_summary']}")

    lines.append("")

    for i, r in enumerate(context_pack.get("results", []), 1):
        source_type_label = {"rule": "规则", "reference": "参考", "project": "项目"}.get(
            r.get("source_type", ""), r.get("source_type", "")
        )
        lines.append(f"{i}. [{source_type_label}] {r.get('title', '')} (相关性: {r.get('score', 0)})")
        lines.append(f"   {r.get('reason', '')}")
        lines.append(f"   {r.get('snippet', '')}")
        lines.append("")

    lines.append("---")

    return "\n".join(lines)
