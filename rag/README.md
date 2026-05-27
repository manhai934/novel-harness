# novel-harness RAG — 轻量知识检索层

> 给 Agent 准备的写作知识搜索引擎。不是通用搜索引擎，是为小说创作 Agent 服务的知识上下文服务。

---

## RAG 是什么

RAG = Retrieval-Augmented Generation（检索增强生成）。说人话：**把写作规则书做成搜索引擎，让 Agent 写作时随时查到该参考什么，不用靠 AI 硬记。**

你的 Agent 需要很多参考知识——"去AI味的规则"、"大纲怎么评估"、"全民求生的题材边界"。这些知识散落在 `.harness/skills/` 的各个 Markdown 文件里。RAG 把这些文件提前建好索引，Agent 提问时秒级找到最相关的内容返回。

没有 RAG 时：Agent 记不住规则，每次都要重新讲，写长了就矛盾。
有 RAG 后：Agent 像查词典一样，随时查。

---

## 完整流程

```
Agent 问："这段太像 AI 写的"
       │
       ▼
① 路由器 分析意图 → 属于 humanization 任务
② 检索器 两路同时搜
   ├─ 关键词搜（FTS）：找包含"AI""总结腔"的段落
   └─ 语义搜（向量）：找意思接近的段落
③ 重排器 从 30 个候选中选出最好的 5 个
④ 组装成"上下文包"返回给 Agent
       │
       ▼
Agent 拿到"去AI味最小修改指南"的内容，参考后修改
```

---

## 核心概念

### 索引
像书的目录。提前把所有 `.md` 文件扫描、按章节切段、给每段生成向量指纹，存入数据库。建一次，查无数次。
目前：**23 个文件 → 233 段 → 233 个向量**。

### 两种搜索方式

| 方式 | 打个比方 | 优缺点 |
|------|---------|--------|
| **关键词搜索（FTS）** | 在网页上 Ctrl+F | 精确但死板，搜"AI味"找不到"总结腔" |
| **语义搜索（向量）** | 问朋友"那段讲什么的" | 灵活但模糊，意思对但字不一定对上 |

两路同时搜，综合打分排序——这就是"混合检索"。

### 向量
把一段文字转成一串数字（384 个）。意思越接近的文字，数字越像。比如"这段像 AI 写的"和"总结腔太明显"字面不同，但向量距离很近。

生成向量的 AI 模型是 `sentence-transformers`（多语言模型，本地运行，跟 ChatGPT 无关）。

### 任务路由
不同问题要找不同知识。路由器根据关键词判断"这是什么类型的问题"，只搜相关分类。

7 种任务类型：

| 任务 | 对应查询 | 搜什么知识 |
|------|---------|-----------|
| `humanization` | "这段太 AI 了" | 语感、人话、去AI味规则 |
| `outline_review` | "这个大纲能展开吗" | 大纲评估、结构完整性 |
| `chapter_prewrite` | "写之前该准备什么" | 写前清单、流程 |
| `genre_routing` | "全民求生选路线" | 题材模板、项目约束 |
| `consistency_check` | "角色前后矛盾" | 设定、逻辑、一致性 |
| `rhythm_review` | "节奏太慢了" | 阅读体验、爽点密度 |
| `ideation` | "开脑洞想个题材" | 灵感、题材方向 |

---

## 快速开始

```bash
# 1. 安装依赖（首次需要）
pip install -r rag/requirements.txt

# 2. 构建索引（首次 + 每次修改知识源后）
python rag/scripts/build_index.py

# 3. 查询测试
python rag/scripts/query.py "这段太像 AI 写的"

# 4. 启动 HTTP 服务（供 Agent 调用）
python rag/scripts/query.py --server
# → 监听 http://localhost:3456
```

---

## API 接口

### `POST /retrieve` — 检索
```json
{ "query": "这段太像 AI 写的", "task_type": "humanization", "top_k": 5 }
```
返回 `context_pack`（结构化数据）和 `context_text`（纯文本，可直接注入 Agent）。

### `POST /reindex` — 重建索引
### `GET /health` — 健康检查
### `GET /stats` — 索引统计
### `POST /explain-retrieval` — 调试：看路由和分数分解

---

## 关键数字

| 指标 | 值 |
|------|----|
| 索引文档 | 随本地知识包变化，以 `build_index.py` 输出为准 |
| Chunks | 随本地知识包变化，以 `build_index.py` 输出为准 |
| 向量维度 | 384 |
| 检索耗时 | ~50ms |
| API 端口 | 3456 |
| 验收测试 | 运行 `python rag/test/verify.py` |

---

## 知识源

- `.harness/knowledge/included/**/*.md` — 随项目自带的知识包
- `.harness/knowledge/remote/**/*.md` — MCP 下载的远程知识包
- `.harness/skills/**/references/*.md` — 参考文档
- `.harness/skills/**/rules/*.md` — 规则文档
- `.harness/project-templates/*.md` — 项目模板

修改这些文件后，需要重建索引：`python rag/scripts/build_index.py`

知识包管理：

```bash
python rag/scripts/sync_packs.py list
python rag/scripts/sync_packs.py installed
python rag/scripts/sync_packs.py --manifest <manifest路径或URL> install <pack_id> --rebuild-index
```

## 验收

```bash
python rag/test/verify.py
```
预期输出：`68 passed, 0 failed, 0 warnings`

---

## 目录结构

```
rag/
├── config/        ← 知识源和路由配置（JSON）
├── schemas/       ← 数据格式定义（JSON Schema）
├── data/          ← 运行时数据（SQLite + 向量，已 gitignore）
├── src/           ← 核心代码（Python）
│   ├── scanner → normalizer → chunker → embedder → indexer   ← 建索引
│   ├── router → retriever → context_pack                      ← 查索引
│   ├── server.py                                              ← HTTP 服务
│   └── storage/  ← SQLite 和向量存储
├── scripts/       ← 命令行工具（build/query/ingest）
└── test/          ← 验收测试
```

## 其中代码

| 文件 | 一句话职责 |
|------|-----------|
| `scanner.py` | 去 `.harness/skills/` 找出所有 `.md` 文件 |
| `normalizer.py` | 读每个 `.md`，提取标题、分类、优先级 |
| `chunker.py` | 按章节切段（300-900 字一段） |
| `embedder.py` | 把文字转成 384 个数字（向量指纹） |
| `indexer.py` | 指挥上面 4 个按顺序干活 |
| `router.py` | 分析问题类型，决定搜哪类知识 |
| `retriever.py` | 关键词 + 语义两路混合搜索 + 打分排序 |
| `context_pack.py` | 把结果组装成 Agent 能直接用的格式 |
| `server.py` | HTTP 服务，给 Agent 调用的 6 个接口 |
| `sqlite_store.py` | 存文件信息和关键词索引 |
| `vector_store.py` | 存向量指纹 |
