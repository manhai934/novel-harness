"""
indexer.py — 索引构建器

职责：
- 编排完整索引构建流程
- scan → normalize → chunk → buildVocabulary → embed → store
"""

import time
from . import scanner
from . import normalizer
from . import chunker
from . import embedder
from .storage import sqlite_store
from .storage import vector_store


def build_full_index():
    """构建完整索引

    流程：
    1. 清空旧数据（SQLite + 向量）
    2. 初始化数据库
    3. 扫描知识文件
    4. 标准化为 document
    5. 分块为 chunks，写入 SQLite
    6. 构建 TF-IDF 词表（用于回退嵌入）
    7. 为所有 chunk 生成向量，写入向量存储

    Returns:
        dict with documents, chunks, vectors
    """
    start_time = time.time()
    print("=" * 50)
    print("  RAG 索引构建开始")
    print("=" * 50)

    # 1. 清空旧数据
    print("\n[1/7] 清空旧数据...")
    sqlite_store.clear_all()
    vector_store.clear()
    print("   OK 旧数据已清空")

    # 2. 初始化数据库
    print("\n[2/7] 初始化数据库...")
    sqlite_store.initialize()
    print("   OK 数据库已初始化")

    # 3. 扫描
    print("\n[3/7] 扫描知识文件...")
    files = scanner.scan_knowledge_files()
    print(f"   OK 扫描到 {len(files)} 个文件")

    # 4. 标准化
    print("\n[4/7] 标准化文档...")
    documents = []
    for f in files:
        doc = normalizer.normalize_document(f["rel_path"], f["source_type"])
        if doc:
            documents.append(doc)
            sqlite_store.upsert_document(doc)
    print(f"   OK {len(documents)} 篇文档已入库")

    # 5. 分块
    print("\n[5/7] 文档分块...")
    all_chunks = []
    for doc in documents:
        chunks = chunker.chunk_markdown(doc)
        all_chunks.extend(chunks)
    sqlite_store.insert_chunks(all_chunks)
    print(f"   OK {len(all_chunks)} 个 chunks 已入库")

    # 6. 构建 TF-IDF 词表（用于回退嵌入）
    print("\n[6/7] 构建统计嵌入词表...")
    corpus = [c["text"] for c in all_chunks]
    embedder.build_vocabulary(corpus)
    print("   OK 词表构建完成")

    # 7. 生成向量
    print("\n[7/7] 生成向量嵌入...")
    chunk_texts = [c["text"] for c in all_chunks]
    vectors = embedder.embed_batch(chunk_texts)

    vector_items = []
    for i, chunk in enumerate(all_chunks):
        vector_items.append({
            "chunk_id": chunk["chunk_id"],
            "vector": vectors[i],
            "text": chunk["text"],
        })

    vector_store.insert_vectors(vector_items)
    print(f"   OK {len(vector_items)} 个向量已存储")

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"  索引构建完成! ({elapsed:.2f}s)")
    print(f"  文档: {len(documents)}")
    print(f"  Chunks: {len(all_chunks)}")
    print(f"  向量: {len(vector_items)}")
    print("=" * 50)

    return {
        "documents": len(documents),
        "chunks": len(all_chunks),
        "vectors": len(vector_items),
    }
