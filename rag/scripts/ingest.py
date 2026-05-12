"""
ingest.py — 知识文件扫描预览

用法：
    python rag/scripts/ingest.py
    python rag/scripts/ingest.py --dry-run
    python rag/scripts/ingest.py --verbose
"""

import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.src.scanner import scan_knowledge_files
from rag.src.normalizer import normalize_document
from rag.src.chunker import chunk_markdown


def main():
    parser = argparse.ArgumentParser(description="知识文件扫描预览")
    parser.add_argument("--dry-run", action="store_true", default=True, help="仅预览不写入")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    args = parser.parse_args()

    files = scan_knowledge_files()

    print(f"\n扫描到 {len(files)} 个知识文件:\n")

    by_type = {"rule": 0, "reference": 0, "project": 0}
    for f in files:
        by_type[f["source_type"]] = by_type.get(f["source_type"], 0) + 1

    for st, count in sorted(by_type.items()):
        print(f"  {st}: {count}")

    if args.verbose:
        print("\n文件列表:")
        for f in sorted(files, key=lambda x: x["rel_path"]):
            print(f"  [{f['source_type']}] {f['rel_path']}")

    # 预览分块统计
    print("\n分块预览 (前 5 个文档):")
    seen_docs = set()
    count = 0
    for f in files:
        doc = normalize_document(f["rel_path"], f["source_type"])
        if doc and doc["doc_id"] not in seen_docs:
            seen_docs.add(doc["doc_id"])
            chunks = chunk_markdown(doc)
            print(f"  {doc['doc_id']}: {len(chunks)} chunks")
            count += 1
            if count >= 5:
                break


if __name__ == "__main__":
    main()
