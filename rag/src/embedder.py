"""
embedder.py — 向量嵌入生成器

策略：
1. 优先使用 sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
   — 支持中文的多语言模型，输出 384 维向量
2. 回退到 TF-IDF (scikit-learn) — 完全本地运行，无需网络

架构设计：
- 统一接口 embed_text / embed_batch
- 向量存储层不感知嵌入实现细节
- 模型加载为延迟加载（首次调用时初始化）
"""

import re
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ====== 全局状态 ======
_transformer_model = None
_model_attempted = False

# TF-IDF 后备
_tfidf_vectorizer = None
_tfidf_built = False


# ====== 中文工具函数 ======

_STOP_WORDS = {
    "的", "了", "是", "在", "有", "和", "就", "不", "都", "而",
    "且", "但", "也", "之", "与", "这", "那", "到", "去", "能", "会", "可",
    "以", "让", "把", "被", "从", "对", "为", "上", "下", "中", "里", "着", "过",
    "没", "很", "太", "更", "最", "又", "再", "才", "还", "已", "将", "要",
    "所", "如", "于", "其", "各", "因", "或", "及", "等",
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "can", "could",
    "this", "that", "these", "those", "i", "me", "my", "you", "your", "it",
}


def tokenize(text):
    """智能中文分词（兼顾词汇和语义覆盖）

    - 汉字提取为单字词和相邻双字词
    - 英文/数字保留原词
    - 过滤停用词
    """
    text = str(text).lower()
    tokens = []
    i = 0

    while i < len(text):
        ch = text[i]

        # 汉字
        if "一" <= ch <= "鿿":
            if ch not in _STOP_WORDS:
                tokens.append(ch)
                # 相邻双字词
                if i + 1 < len(text) and "一" <= text[i + 1] <= "鿿":
                    bigram = text[i : i + 2]
                    if bigram not in _STOP_WORDS:
                        tokens.append(bigram)
            i += 1
        # 英文/数字
        elif ch.isalnum():
            word = ""
            while i < len(text) and text[i].isalnum():
                word += text[i]
                i += 1
            if word and word not in _STOP_WORDS:
                tokens.append(word)
        else:
            i += 1

    return tokens


# ====== sentence-transformers 嵌入器 ======


def _try_load_transformer():
    """尝试加载 sentence-transformers 模型（延迟加载）"""
    global _transformer_model, _model_attempted
    if _model_attempted:
        return
    _model_attempted = True

    try:
        from sentence_transformers import SentenceTransformer

        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        print(f"[embedder] 加载模型: {model_name} ...")
        _transformer_model = SentenceTransformer(model_name)
        dim = getattr(_transformer_model, 'get_sentence_embedding_dimension',
                      _transformer_model.get_embedding_dimension)()
        print(f"[embedder] 模型加载成功，输出维度: {dim}")
    except Exception as e:
        print(f"[embedder] sentence-transformers 加载失败: {e}")
        print("[embedder] 将使用 TF-IDF 统计嵌入回退方案")


def _transformer_embed(texts):
    """使用 transformer 模型生成 embedding"""
    if _transformer_model is None:
        raise RuntimeError("Transformer model not loaded")

    if isinstance(texts, str):
        texts = [texts]

    embeddings = _transformer_model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


# ====== TF-IDF 统计嵌入器（后备方案）======


def build_vocabulary(corpus, max_vocab=20000):
    """从语料构建 TF-IDF 向量器

    参数：
        corpus: 字符串列表
        max_vocab: 最大词表大小
    """
    global _tfidf_vectorizer, _tfidf_built

    from sklearn.feature_extraction.text import TfidfVectorizer

    # 自定义分词器
    def custom_tokenizer(text):
        return tokenize(text)

    _tfidf_vectorizer = TfidfVectorizer(
        tokenizer=custom_tokenizer,
        lowercase=True,
        max_features=max_vocab,
        norm="l2",
        token_pattern=None,
    )

    _tfidf_vectorizer.fit(corpus)
    _tfidf_built = True

    vocab_size = len(_tfidf_vectorizer.get_feature_names_out())
    print(f"[embedder] TF-IDF 词表构建完成: {vocab_size} 个词, {len(corpus)} 篇文档")


def _tfidf_embed(texts):
    """TF-IDF 向量化"""
    if _tfidf_vectorizer is None:
        raise RuntimeError("TF-IDF 向量器尚未构建，请先调用 build_vocabulary()。")

    if isinstance(texts, str):
        texts = [texts]

    vectors = _tfidf_vectorizer.transform(texts)
    return vectors.toarray().tolist()


# ====== 公共接口 ======


def embed_text(text):
    """为单段文本生成 embedding

    优先使用 sentence-transformers，失败则回退到 TF-IDF。

    参数：
        text: 待嵌入文本

    返回：
        384 维向量
    """
    if not _model_attempted:
        _try_load_transformer()

    if _transformer_model is not None:
        try:
            return _transformer_embed(text)[0]
        except Exception as e:
            print(f"[embedder] Transformer 嵌入失败: {e}，回退到 TF-IDF")

    if _tfidf_built and _tfidf_vectorizer is not None:
        return _tfidf_embed(text)[0]

    return _fallback_embed(text)


def embed_batch(texts):
    """批量生成嵌入向量"""
    if not isinstance(texts, (list, tuple)):
        texts = [texts]

    if not _model_attempted:
        _try_load_transformer()

    if _transformer_model is not None:
        try:
            return _transformer_embed(texts)
        except Exception as e:
            print(f"[embedder] Transformer 批量嵌入失败: {e}，回退到 TF-IDF")

    if _tfidf_built and _tfidf_vectorizer is not None:
        return _tfidf_embed(texts)

    return [_fallback_embed(t) for t in texts]


def _fallback_embed(text):
    """简单哈希嵌入（最后防线）"""
    dim = 384
    vector = np.zeros(dim)
    text = str(text)
    length = len(text) or 1

    for i, ch in enumerate(text):
        idx = abs(ord(ch)) % dim
        vector[idx] += 1.0 / length

    norm = np.linalg.norm(vector)
    if norm > 1e-10:
        vector = vector / norm

    return vector.tolist()
