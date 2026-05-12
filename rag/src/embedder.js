/**
 * embedder.js — 向量嵌入生成器
 *
 * 策略：
 * 1. 优先使用 Transformers.js (multilingual-e5-small) — 需网络下载模型
 * 2. 回退到统计嵌入 (TF-IDF + 中文 bigrams) — 完全本地运行
 *
 * 架构设计：
 * - 统一接口 embedText / embedBatch
 * - VectorStore 不感知 embedding 实现细节
 */

// ====== 中文分词引擎 ======

/**
 * 智能中文分词（兼顾词汇和语义覆盖）
 * - 汉字提取为 unigram + bigram
 * - 英文/数字保留原词
 * - 过滤停用词
 */
function tokenize(text) {
  const str = String(text).toLowerCase();
  const tokens = [];
  const stopWords = new Set(['的', '了', '是', '在', '有', '和', '就', '不', '都', '而',
    '而', '且', '但', '也', '之', '与', '这', '那', '到', '去', '能', '会', '可',
    '以', '让', '把', '被', '从', '对', '为', '上', '下', '中', '里', '着', '过',
    '没', '很', '太', '更', '最', '又', '再', '才', '还', '已', '将', '要', '该',
    '所', '如', '于', '其', '各', '但', '因', '所', '或', '及', '与', '等', '第',
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'can', 'could',
    'this', 'that', 'these', 'those', 'i', 'me', 'my', 'you', 'your', 'it']);

  let i = 0;

  while (i < str.length) {
    const ch = str[i];

    // 汉字
    if (/[一-鿿]/.test(ch)) {
      // unigram
      if (!stopWords.has(ch)) {
        tokens.push(ch);

        // bigram
        if (i + 1 < str.length && /[一-鿿]/.test(str[i + 1])) {
          const bigram = str.substring(i, i + 2);
          if (!stopWords.has(bigram)) {
            tokens.push(bigram);
          }
        }
      }
      i++;
    }
    // 英文/数字
    else if (/[a-zA-Z0-9]/.test(ch)) {
      let word = '';
      while (i < str.length && /[a-zA-Z0-9]/.test(str[i])) {
        word += str[i];
        i++;
      }
      if (word.length > 0 && !stopWords.has(word)) {
        tokens.push(word);
      }
    } else {
      i++;
    }
  }

  return tokens;
}

// ====== TF-IDF 统计嵌入引擎 ======

let vocabulary = new Map();   // word -> index
let corpusDf = new Map();    // word -> document frequency
let totalDocs = 0;
let built = false;

/**
 * 从语料构建词表
 * @param {string[]} corpus
 */
export function buildVocabulary(corpus) {
  vocabulary = new Map();
  corpusDf = new Map();
  totalDocs = corpus.length;

  // 收集所有文档的词频
  for (const doc of corpus) {
    const tokens = tokenize(doc);
    const seen = new Set();

    for (const token of tokens) {
      if (!vocabulary.has(token)) {
        vocabulary.set(token, vocabulary.size);
      }
      if (!seen.has(token)) {
        corpusDf.set(token, (corpusDf.get(token) || 0) + 1);
        seen.add(token);
      }
    }
  }

  // 限制词表大小（取 top N）
  const MAX_VOCAB = 20000;
  if (vocabulary.size > MAX_VOCAB) {
    // 按 IDF 排序保留最重要的词
    const sorted = [...corpusDf.entries()]
      .sort((a, b) => {
        const idfA = Math.log((totalDocs + 1) / (a[1] + 1)) + 1;
        const idfB = Math.log((totalDocs + 1) / (b[1] + 1)) + 1;
        return idfB - idfA;
      })
      .slice(0, MAX_VOCAB);

    vocabulary = new Map();
    for (const [word] of sorted) {
      vocabulary.set(word, vocabulary.size);
    }
  }

  built = true;
  console.log(`[embedder] 词表构建完成: ${vocabulary.size} 个词, ${totalDocs} 篇文档`);
}

/**
 * TF-IDF 向量化
 */
function tfidfEmbed(text) {
  const dim = Math.max(vocabulary.size, 384);
  const vector = new Array(dim).fill(0);
  const tokens = tokenize(text);

  if (tokens.length === 0) {
    vector[0] = 1;  // 零向量占位
    return vector;
  }

  // TF
  const tf = new Map();
  for (const token of tokens) {
    tf.set(token, (tf.get(token) || 0) + 1);
  }

  // TF-IDF 加权
  const len = tokens.length;
  for (const [token, count] of tf) {
    const idx = vocabulary.get(token);
    if (idx !== undefined && idx < dim) {
      const df = corpusDf.get(token) || 1;
      const idf = Math.log((totalDocs + 1) / (df + 1)) + 1;
      vector[idx] = (count / len) * idf;
    }
  }

  // L2 归一化
  const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
  if (norm > 1e-10) {
    for (let i = 0; i < dim; i++) vector[i] /= norm;
  }

  return vector;
}

// ====== Transformers.js ======

let transformersPipeline = null;
let modelAttempted = false;

async function tryLoadTransformers() {
  if (modelAttempted) return;
  modelAttempted = true;

  try {
    const { pipeline } = await import('@xenova/transformers');
    transformersPipeline = await pipeline('feature-extraction', 'Xenova/multilingual-e5-small');
    console.log('[embedder] Transformers.js 模型加载成功');
  } catch (err) {
    // 静默降级到 TF-IDF
  }
}

// ====== 公共接口 ======

/**
 * 为单段文本生成 embedding
 */
export async function embedText(text) {
  if (!modelAttempted) await tryLoadTransformers();

  if (transformersPipeline) {
    try {
      const result = await transformersPipeline(text, { pooling: 'mean', normalize: true });
      return Array.from(result.data);
    } catch {}
  }

  if (built && vocabulary.size > 0) {
    return tfidfEmbed(String(text));
  }

  return fallbackEmbed(String(text));
}

/**
 * 批量生成 embeddings
 */
export async function embedBatch(texts) {
  if (!modelAttempted) await tryLoadTransformers();

  if (transformersPipeline) {
    const results = [];
    for (const text of texts) {
      try {
        const result = await transformersPipeline(text, { pooling: 'mean', normalize: true });
        results.push(Array.from(result.data));
      } catch {
        results.push(built && vocabulary.size > 0 ? tfidfEmbed(String(text)) : fallbackEmbed(String(text)));
      }
    }
    return results;
  }

  if (built && vocabulary.size > 0) {
    return texts.map(t => tfidfEmbed(String(t)));
  }

  return texts.map(t => fallbackEmbed(String(t)));
}

/**
 * Fallback: 简单哈希嵌入
 */
function fallbackEmbed(text) {
  const dim = 384;
  const vector = new Array(dim).fill(0);
  const str = String(text);
  const len = str.length || 1;

  for (let i = 0; i < len; i++) {
    const code = str.charCodeAt(i);
    const idx = Math.abs(code) % dim;
    vector[idx] += 1 / len;
  }

  const norm = Math.sqrt(vector.reduce((sum, v) => sum + v * v, 0));
  if (norm > 0) {
    for (let i = 0; i < dim; i++) vector[i] /= norm;
  }
  return vector;
}

export default { embedText, embedBatch, buildVocabulary, tokenize };
