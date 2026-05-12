"""
vector_store.py — 向量存储层

基于 JSON 文件的向量存储，内存中管理，支持余弦相似度检索。
VECTOR_DIM = 384，与 sentence-transformers multilingual 模型对齐。
可替换为 Qdrant/Milvus 等专业向量数据库。
"""

import json
import math
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VECTORS_DIR = PROJECT_ROOT / "rag" / "data" / "vectors"
VECTORS_PATH = VECTORS_DIR / "vectors.json"

VECTOR_DIM = 384

# 内存存储: {chunk_id: {"vector": [...], "text": str, ...}}
_vectors = {}
_loaded = False


def _ensure_loaded():
    """确保向量数据已加载到内存"""
    global _loaded, _vectors
    if _loaded:
        return
    if VECTORS_PATH.exists():
        try:
            with open(VECTORS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                _vectors = data.get("vectors", {})
        except (json.JSONDecodeError, OSError) as e:
            print(f"[vector_store] 读取向量文件失败: {e}")
            _vectors = {}
    _loaded = True


def _save():
    """持久化到 JSON 文件"""
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)
    with open(VECTORS_PATH, "w", encoding="utf-8") as f:
        json.dump({"vectors": _vectors, "dim": VECTOR_DIM}, f, ensure_ascii=False)


def cosine_similarity(vec_a, vec_b):
    """计算余弦相似度"""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(len(vec_a)):
        va = vec_a[i]
        vb = vec_b[i] if i < len(vec_b) else 0
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb
    denom = math.sqrt(norm_a) * math.sqrt(norm_b)
    if denom < 1e-10:
        return 0.0
    return dot / denom


def insert_vectors(chunk_vectors):
    """批量插入向量

    Args:
        chunk_vectors: list of {"chunk_id": str, "vector": list[float], "text": str}
    """
    _ensure_loaded()
    for item in chunk_vectors:
        _vectors[item["chunk_id"]] = {
            "vector": item["vector"],
            "text": item.get("text", ""),
        }
    _save()


def vector_search(query_vector, top_n=15):
    """余弦相似度搜索

    Args:
        query_vector: list[float]
        top_n: 返回数量

    Returns:
        list of {"chunk_id": str, "score": float}
    """
    _ensure_loaded()
    if not _vectors:
        return []

    scored = []
    for chunk_id, data in _vectors.items():
        score = cosine_similarity(query_vector, data["vector"])
        scored.append({"chunk_id": chunk_id, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def get_vector_count():
    """获取向量数量"""
    _ensure_loaded()
    return len(_vectors)


def clear():
    """清空所有向量"""
    global _vectors, _loaded
    _vectors = {}
    _loaded = True
    if VECTORS_PATH.exists():
        try:
            VECTORS_PATH.unlink()
        except OSError:
            pass
