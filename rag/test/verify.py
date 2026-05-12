"""
verify.py — RAG 系统验收测试

覆盖 50+ 项检查：
1. 架构完整性 — 文件/配置/模式是否存在
2. 知识源扫描 — 文件数量，排除路径是否正确
3. 任务路由 — 7 种任务类型路由准确率
4. 索引构建 — 文档数、chunks 数、向量数
5. 混合检索 — 4 个 TA 查询命中 top-3 正确性
6. 结果稳定性 — 重复查询结果一致性
"""

import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.src.scanner import scan_knowledge_files
from rag.src.normalizer import normalize_document
from rag.src.chunker import chunk_markdown
from rag.src.router import route_query
from rag.src.indexer import build_full_index
from rag.src.retriever import hybrid_retrieve
from rag.src.storage import sqlite_store
from rag.src.storage import vector_store


# ====== 测试框架 ======

class Tester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            status = "PASS"
        else:
            self.failed += 1
            status = "FAIL"
        self.results.append({"name": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    def warn(self, name, detail=""):
        self.warnings += 1
        self.results.append({"name": name, "status": "WARN", "detail": detail})
        print(f"  [WARN] {name}" + (f" — {detail}" if detail else ""))

    def summary(self):
        print(f"\n{'='*50}")
        print(f"  结果: {self.passed} passed, {self.failed} failed, {self.warnings} warnings")
        print(f"{'='*50}")
        return self.failed == 0


def run_verify():
    t = Tester()
    print("RAG 验收测试")
    print("=" * 50)

    # ====== 1. 架构完整性 ======
    print("\n[1/6] 架构完整性检查")
    print("-" * 30)

    # 文件存在性
    required_files = [
        "rag/src/__init__.py",
        "rag/src/storage/__init__.py",
        "rag/src/scanner.py",
        "rag/src/normalizer.py",
        "rag/src/chunker.py",
        "rag/src/embedder.py",
        "rag/src/router.py",
        "rag/src/retriever.py",
        "rag/src/context_pack.py",
        "rag/src/indexer.py",
        "rag/src/server.py",
        "rag/src/storage/sqlite_store.py",
        "rag/src/storage/vector_store.py",
        "rag/scripts/build_index.py",
        "rag/scripts/query.py",
        "rag/scripts/ingest.py",
        "rag/config/sources.json",
        "rag/config/task-routes.json",
        "rag/config/categories.json",
        "rag/schemas/document.schema.json",
        "rag/schemas/chunk.schema.json",
        "rag/schemas/context-pack.schema.json",
        "rag/test/verify.py",
    ]

    for f in required_files:
        path = PROJECT_ROOT / f
        t.check(f"文件存在: {f}", path.exists())

    # ====== 2. 知识源扫描 ======
    print("\n[2/6] 知识源扫描")
    print("-" * 30)

    files = scan_knowledge_files()
    t.check("扫描到文件", len(files) > 0, f"共 {len(files)} 个")

    # 检查没有扫描到禁入路径
    forbidden = ["planning", "legacy-skills", "agents", "memory", "cases", ".harness/rules"]
    for path_str in forbidden:
        count = sum(1 for f in files if path_str in f["rel_path"])
        t.check(f"未扫描禁入路径: {path_str}", count == 0, f"命中 {count} 个")

    # source_type 分布
    by_type = {}
    for f in files:
        by_type[f["source_type"]] = by_type.get(f["source_type"], 0) + 1
    t.check("有规则文件", by_type.get("rule", 0) > 0, f"规则: {by_type.get('rule', 0)}")
    t.check("有参考文件", by_type.get("reference", 0) > 0, f"参考: {by_type.get('reference', 0)}")

    # ====== 3. 任务路由 ======
    print("\n[3/6] 任务路由")
    print("-" * 30)

    route_tests = {
        # p0 查询 → 期望 task_type
        "这段太像 AI 写的": "humanization",
        "这个大纲后面能不能展开": "outline_review",
        "这一章写之前我该准备什么": "chapter_prewrite",
        "全民求生该先定哪条路线": "genre_routing",
        "这章节奏太平了，读起来很拖": "rhythm_review",
        "帮我看看角色状态有没有矛盾": "consistency_check",
        "给我一些新的灵感": "ideation",
    }

    for query, expected in route_tests.items():
        route = route_query(query)
        matched = route.get("task_type") == expected
        detail = f"预期={expected}, 实际={route.get('task_type')}, 置信度={route.get('confidence', 0):.2f}"
        t.check(f"路由: {query[:20]}... → {expected}", matched, detail)

    # ====== 4. 索引构建 ======
    print("\n[4/6] 索引构建")
    print("-" * 30)

    stats = build_full_index()

    t.check("文档数 > 0", stats["documents"] > 0, f"{stats['documents']} 篇")
    t.check("Chunks 数 > 0", stats["chunks"] > 0, f"{stats['chunks']} 个")
    t.check("向量数 > 0", stats["vectors"] > 0, f"{stats['vectors']} 个")
    t.check("文档数 ≥ 20", stats["documents"] >= 20, f"{stats['documents']} 篇")
    t.check("Chunks ≥ 200", stats["chunks"] >= 200, f"{stats['chunks']} 个")
    t.check("向量数 = chunks 数", stats["vectors"] == stats["chunks"],
            f"向量={stats['vectors']}, chunks={stats['chunks']}")

    # SQLite 验证
    sqlite_stats = sqlite_store.get_stats()
    t.check("SQLite 文档数一致", sqlite_stats["documents"] == stats["documents"],
            f"SQLite={sqlite_stats['documents']}, indexer={stats['documents']}")
    t.check("SQLite chunks 数一致", sqlite_stats["chunks"] == stats["chunks"],
            f"SQLite={sqlite_stats['chunks']}, indexer={stats['chunks']}")

    # 向量验证
    vec_count = vector_store.get_vector_count()
    t.check("向量存储数量一致", vec_count == stats["vectors"],
            f"vector_store={vec_count}, indexer={stats['vectors']}")

    # ====== 5. 混合检索 ======
    print("\n[5/6] 混合检索")
    print("-" * 30)

    ta_queries = [
        ("这段太像 AI 写的", "humanization", ["去AI味最小修改指南"]),
        ("这个大纲后面能不能展开", "outline_review", ["大纲质量评估清单"]),
        ("这一章写之前我该准备什么", "chapter_prewrite", ["章节写前准备清单"]),
        ("全民求生该先定哪条路线", "genre_routing", ["二、Index：子题材规则入口"]),
    ]

    all_top3_correct = True
    for query, task_type, expected_titles in ta_queries:
        result = hybrid_retrieve(query=query, task_type=task_type, top_k=3)
        top_titles = [r["title"] for r in result["results"]]

        # 检查 top-3 中是否有预期结果
        top3_ok = any(any(exp in t for exp in expected_titles) for t in top_titles)

        detail = f"top1={top_titles[0] if top_titles else 'N/A'}, top3={top_titles}"
        t.check(
            f"TA: {query[:20]}...",
            top3_ok,
            detail,
        )
        if not top3_ok:
            all_top3_correct = False

    t.check("所有 TA 查询 top-3 有效", all_top3_correct, "" if all_top3_correct else "有查询未命中")

    # 额外质量检查
    for query, task_type, _ in ta_queries:
        result = hybrid_retrieve(query=query, task_type=task_type, top_k=3)
        for r in result["results"]:
            t.check(f"  结果票签完备: {r['chunk_id'][:30]}",
                    all(k in r for k in ("chunk_id", "title", "score", "reason", "snippet")),
                    "")

    # 测试无任务类型时的自动路由检索
    auto_result = hybrid_retrieve(query="这段太像 AI 写的", top_k=3)
    t.check("自动路由检索正常", len(auto_result["results"]) > 0,
            f"共 {len(auto_result['results'])} 条结果, 路由类型={auto_result['meta']['task_type']}")

    # ====== 6. 结果稳定性 ======
    print("\n[6/6] 结果稳定性")
    print("-" * 30)

    test_query = "大纲"
    r1 = hybrid_retrieve(query=test_query, task_type="outline_review", top_k=5)
    r2 = hybrid_retrieve(query=test_query, task_type="outline_review", top_k=5)

    ids1 = [r["chunk_id"] for r in r1["results"]]
    ids2 = [r["chunk_id"] for r in r2["results"]]
    t.check("重复查询结果 top-1 一致",
            ids1[:1] == ids2[:1],
            f"r1={ids1[:1]}, r2={ids2[:1]}")
    t.check("重复查询结果 top-5 一致",
            ids1 == ids2,
            f"差异: {set(ids1) ^ set(ids2)}")

    # 打印性能
    print(f"\n  检索性能: {r1['meta']['elapsed_ms']}ms (FTS: {r1['meta']['fts_count']}, "
          f"向量: {r1['meta']['vector_count']}, 候选: {r1['meta']['total_candidates']})")

    return t.summary()


if __name__ == "__main__":
    success = run_verify()
    sys.exit(0 if success else 1)
