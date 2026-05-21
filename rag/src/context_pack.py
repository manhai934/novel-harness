"""
context_pack.py - 根据检索结果构建可注入提示词的上下文包。
"""


def build_context_pack(query, retrieval_result, task_type=None, project_hint=None):
    """构建标准化 context pack。"""
    results = retrieval_result.get("results", [])
    meta = retrieval_result.get("meta", {})

    type_order = {"rule": 0, "knowledge": 1, "reference": 2, "project": 3}
    sorted_results = sorted(results, key=lambda r: type_order.get(r.get("source_type", ""), 9))

    top_sources = [r.get("title", "") for r in sorted_results[:5]]
    knowledge_summary = f"检索到 {len(sorted_results)} 条相关知识点"
    if top_sources:
        knowledge_summary += "，涉及: " + "、".join(top_sources)

    source_breakdown = {"rule": 0, "knowledge": 0, "reference": 0, "project": 0}
    for result in sorted_results:
        source_type = result.get("source_type", "")
        if source_type in source_breakdown:
            source_breakdown[source_type] += 1

    return {
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


def context_pack_to_text(context_pack):
    """把 context pack 格式化成纯文本，供 Agent prompt 注入。"""
    lines = []
    lines.append("---")
    lines.append("[知识上下文]")
    lines.append(f"任务类型: {context_pack.get('task_type', 'general')}")
    lines.append(f"查询: {context_pack.get('query', '')}")

    source_breakdown = context_pack.get("source_breakdown", {})
    names = {
        "rule": "规则",
        "knowledge": "知识包",
        "reference": "参考",
        "project": "项目",
    }
    parts = []
    for source_type in ("rule", "knowledge", "reference", "project"):
        count = source_breakdown.get(source_type, 0)
        if count > 0:
            parts.append(f"{names.get(source_type, source_type)} x {count}")
    lines.append(f"来源: {', '.join(parts) if parts else '无'}")

    if context_pack.get("knowledge_summary"):
        lines.append(f"摘要: {context_pack['knowledge_summary']}")

    lines.append("")

    for index, result in enumerate(context_pack.get("results", []), 1):
        source_type = result.get("source_type", "")
        source_type_label = names.get(source_type, source_type)
        lines.append(
            f"{index}. [{source_type_label}] {result.get('title', '')} "
            f"(相关性: {result.get('score', 0)})"
        )
        lines.append(f"   {result.get('reason', '')}")
        lines.append(f"   {result.get('snippet', '')}")
        lines.append("")

    lines.append("---")
    return "\n".join(lines)
