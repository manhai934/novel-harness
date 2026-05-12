# novel-harness RAG — 轻量混合知识检索层

> L3 知识检索层，服务于 novel-harness 总编/专业 Agent 体系。
> 定位：不是通用搜索引擎，是面向小说创作 Agent 的知识上下文服务。

---

## 架构概览

```
用户请求 → 任务路由器 → 检索请求构造器 → 混合召回
  ├─ SQLite FTS5 (关键词/标题/标签)
  └─ 向量检索 (sentence-transformers 语义相似度)
  → 轻量重排器 → Context Pack Builder → Agent
```

## 目录结构

```
rag/
├── config/
│   ├── sources.json         # 知识源配置
│   ├── task-routes.json     # 任务路由规则
│   └── categories.json      # 分类定义
├── schemas/
│   ├── document.schema.json
│   ├── chunk.schema.json
│   └── context-pack.schema.json
├── data/                    # 运行时数据（索引文件）
│   ├── metadata.db          # SQLite + FTS5
│   └── vectors/             # 向量存储
├── src/
│   ├── scanner.py           # 知识源扫描
│   ├── normalizer.py        # 文档标准化
│   ├── chunker.py           # 语义切块
│   ├── embedder.py          # 向量嵌入生成
│   ├── router.py            # 任务路由
│   ├── retriever.py         # 混合检索 + 重排
│   ├── context_pack.py      # Context Pack 构建
│   ├── indexer.py           # 索引编排
│   ├── server.py            # HTTP 服务 (FastAPI)
│   └── storage/
│       ├── sqlite_store.py  # SQLite + FTS5
│       └── vector_store.py  # 向量存储抽象
├── scripts/
│   ├── ingest.py            # 知识入库 CLI
│   ├── build_index.py       # 索引构建 CLI
│   └── query.py             # 查询 CLI
└── test/
    └── verify.py            # 验收测试
```

## 快速开始

### 0. 安装依赖

```bash
pip install -r rag/requirements.txt
```

首次运行会自动下载 sentence-transformers 多语言模型（~100MB）。

### 1. 构建索引

```bash
python rag/scripts/build_index.py
```

### 2. 查询测试

```bash
python rag/scripts/query.py "这段太像 AI 写的"
python rag/scripts/query.py "这个大纲后面能不能展开" --top-k 3
python rag/scripts/query.py "全民求生该先定哪条路线" --task-type genre_routing
```

### 3. 启动 HTTP 服务

```bash
python rag/scripts/query.py --server
# 或
uvicorn rag.src.server:app --host 0.0.0.0 --port 3456
```

默认端口 3456。

## API 接口

### `POST /retrieve`

```json
{
  "query": "这段太像 AI 写的",
  "task_type": "humanization",
  "top_k": 5
}
```

返回包含 `context_pack` 和 `context_text`（纯文本版，可直接注入 Agent prompt）。

### `POST /reindex`

重建所有索引。

### `GET /health`

健康检查。

### `POST /explain-retrieval`

检索解释（调试用）。

## 支持的任务类型

| 任务类型 | 说明 | 典型查询 |
|----------|------|---------|
| `ideation` | 构思发散 | "开脑洞想个题材" |
| `outline_review` | 大纲审查 | "这个大纲能展开吗" |
| `chapter_prewrite` | 写前准备 | "写之前该准备什么" |
| `humanization` | 去AI味 | "这段太AI了" |
| `consistency_check` | 一致性检查 | "角色前后矛盾" |
| `rhythm_review` | 节奏审查 | "节奏太慢了" |
| `genre_routing` | 题材选型 | "全民求生选路线" |

## 重排公式

```
最终分 = 语义分 × 0.35 + FTS分 × 0.15 + 任务匹配分 × 0.30 + priority权重 × 0.12 + source_type权重 × 0.08
```

## 知识源范围 (V1)

- `.harness/skills/**/references/*.md`
- `.harness/skills/**/rules/*.md`
- `.harness/projects/*.md`

## 验收

```bash
python rag/test/verify.py
```

## 嵌入策略

1. **sentence-transformers**（首选）：`paraphrase-multilingual-MiniLM-L12-v2`，384 维，多语言支持
2. **TF-IDF + sklearn**（回退）：纯本地统计嵌入，无需网络
3. **哈希嵌入**（最后防线）：简单字符哈希

## 后续扩展

- V2: 接入 `.harness/cases/**`、独立 reranker、query rewrite
- V3: 项目级状态知识、反馈日志分析
- V4: MCP 封装
