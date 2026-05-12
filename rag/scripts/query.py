"""
query.py — RAG 查询脚本

用法：
    python rag/scripts/query.py "你的查询"
    python rag/scripts/query.py "你的查询" --task-type humanization --top-k 3
    python rag/scripts/query.py "你的查询" --json
    python rag/scripts/query.py "你的查询" --route-only
"""

import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.src.retriever import hybrid_retrieve
from rag.src.router import route_query
from rag.src.context_pack import build_context_pack, context_pack_to_text


def main():
    parser = argparse.ArgumentParser(description="RAG 知识检索")
    parser.add_argument("query", nargs="?", help="检索查询文本")
    parser.add_argument("--task-type", help="任务类型（可选）")
    parser.add_argument("--top-k", type=int, default=5, help="返回结果数量")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--route-only", action="store_true", help="仅显示路由分析")
    parser.add_argument("--server", action="store_true", help="启动 HTTP 服务")

    args = parser.parse_args()

    if args.server:
        # 启动 HTTP 服务
        from rag.src.server import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=3456)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    query = args.query

    if args.route_only:
        route = route_query(query)
        print(json.dumps(route, ensure_ascii=False, indent=2))
        return

    # 执行检索
    result = hybrid_retrieve(
        query=query,
        task_type=args.task_type,
        top_k=args.top_k,
    )

    context_pack = build_context_pack(
        query=query,
        retrieval_result=result,
        task_type=args.task_type,
    )

    if args.json:
        print(json.dumps(context_pack, ensure_ascii=False, indent=2))
    else:
        print(context_pack_to_text(context_pack))
        print(f"\n[元信息] 耗时: {result['meta']['elapsed_ms']}ms, "
              f"候选: {result['meta']['total_candidates']}, "
              f"任务类型: {result['meta']['task_type']}")


if __name__ == "__main__":
    main()
