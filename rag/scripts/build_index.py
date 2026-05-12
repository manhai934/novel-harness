"""
build_index.py — 索引构建脚本

用法：
    python rag/scripts/build_index.py
"""

import sys
import time
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.src.indexer import build_full_index


def main():
    start = time.time()
    stats = build_full_index()
    elapsed = time.time() - start

    print(f"\n耗时: {elapsed:.2f}s")
    print(f"文档: {stats['documents']}")
    print(f"Chunks: {stats['chunks']}")
    print(f"向量: {stats['vectors']}")


if __name__ == "__main__":
    main()
