# RAG 知识检索层 — 操作手册

> **L3 数据层组件** — 为 novel-harness Agent 体系提供知识检索服务。
> 本文档面向系统维护者和 Agent 开发者，说明如何安装、运行、维护和调试 RAG 系统。

---

## 目录

- [系统概述](#系统概述)
- [安装与依赖](#安装与依赖)
- [索引管理](#索引管理)
- [HTTP 服务](#http-服务)
- [CLI 查询](#cli-查询)
- [API 接口详解](#api-接口详解)
- [任务路由机制](#任务路由机制)
- [嵌入策略](#嵌入策略)
- [验收测试](#验收测试)
- [故障排查](#故障排查)
- [Agent 集成指南](#agent-集成指南)
- [文件清单](#文件清单)

---

## 系统概述

### 定位

RAG（Retrieval-Augmented Generation）层为写作 Agent 提供知识上下文。它不是通用搜索引擎，而是面向小说创作的知识检索服务。

### 架构

```
Agent 请求
    │
    ▼
┌──────────────┐
│  任务路由器    │  ← 分析查询意图 → 确定 task_type / categories / stages
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  混合检索器    │
│              │
│  ┌────────┐  │  ┌──────────────────┐
│  │ 硬过滤   │──│→ metadata (category/stage)
│  └────────┘  │  └──────────────────┘
│  ┌────────┐  │  ┌──────────────────┐
│  │ FTS 召回 │──│→ SQLite FTS5 (关键词)
│  └────────┘  │  └──────────────────┘
│  ┌────────┐  │  ┌──────────────────┐
│  │ 向量召回  │──│→ sentence-transformers (语义)
│  └────────┘  │  └──────────────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  轻量重排器    │  ← vec*0.35 + fts*0.15 + taskMatch*0.30 + priority*0.12 + sourceType*0.08
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Context Pack │  → 结构化结果返回给 Agent
└──────────────┘
```

### 数据流

1. Agent 发送查询请求（可附带 task_type）
2. 任务路由器自动识别查询意图，确定过滤条件
3. 按 metadata 硬过滤 → FTS5 全文检索 → 向量语义检索
4. 合并候选集，用加权公式重排
5. 构建 Context Pack（结构化 JSON + 纯文本）
6. 返回给 Agent 做 prompt 注入

---

## 安装与依赖

### 环境要求

- Python ≥ 3.12
- pip
- 网络连接（首次运行需要下载 sentence-transformers 模型，约 100MB）

### 安装步骤

```bash
# 1. 安装 Python 依赖
pip install -r rag/requirements.txt

# 2. 构建索引（首次必须）
python rag/scripts/build_index.py

# 3. 验证安装
python rag/test/verify.py
```

### 依赖清单

| 包 | 用途 | 版本要求 |
|------|------|---------|
| `sentence-transformers` | 语义嵌入向量生成 | ≥ 2.2.0 |
| `fastapi` | HTTP 服务框架 | ≥ 0.104.0 |
| `uvicorn` | HTTP 服务运行 | ≥ 0.24.0 |
| `numpy` | 向量数值计算 | ≥ 1.24.0 |
| `scikit-learn` | TF-IDF 统计嵌入后备 | ≥ 1.3.0 |
| `pydantic` | API 请求/响应校验 | ≥ 2.5.0 |

### 模型说明

默认使用 `paraphrase-multilingual-MiniLM-L12-v2`（384 维输出，多语言支持）。缓存路径：
- Windows: `C:\Users\<用户名>\.cache\huggingface\hub\`
- Linux: `~/.cache/huggingface/hub/`

如无法联网，可手动下载模型文件放入缓存目录，或系统会自动回退到 TF-IDF 统计嵌入。

---

## 索引管理

### 构建索引

```bash
# 完整构建（清空旧数据后重新索引全部知识源）
python rag/scripts/build_index.py
```

输出示例：
```
==================================================
  RAG 索引构建开始
==================================================

[1/7] 清空旧数据...
   OK 旧数据已清空
[2/7] 初始化数据库...
   OK 数据库已初始化
[3/7] 扫描知识文件...
   OK 扫描到 23 个文件
[4/7] 标准化文档...
   OK 23 篇文档已入库
[5/7] 文档分块...
   OK 233 个 chunks 已入库
[6/7] 构建统计嵌入词表...
   OK 词表构建完成
[7/7] 生成向量嵌入...
   OK 233 个向量已存储

==================================================
  索引构建完成! (44.65s)
  文档: 23
  Chunks: 233
  向量: 233
==================================================
```

### 何时需要重建索引

| 场景 | 操作 |
|------|------|
| 首次部署 | `python rag/scripts/build_index.py` |
| 新增/修改了 `.harness/skills/` 中的规则或参考文档 | 调用 `POST /reindex` 或运行 build_index |
| 新增项目模板（`.harness/projects/*.md`） | 同上 |
| 索引损坏/数据异常 | 同上 |
| 日常启动服务前 | 不需要重建，已有索引自动可用 |

### 查看索引状态

```bash
# 通过 API
curl http://localhost:3456/stats
# → {"sqlite": {"documents": 23, "chunks": 233}, "vectors": 233}

# 通过 HTTP 健康检查
curl http://localhost:3456/health
# → {"status": "ok", "sqlite": true, "vectors": true}
```

---

## HTTP 服务

### 启动服务

```bash
# 方式一：通过 query.py
python rag/scripts/query.py --server

# 方式二：直接 uvicorn
uvicorn rag.src.server:app --host 0.0.0.0 --port 3456

# 方式三：带热重载的开发模式
uvicorn rag.src.server:app --reload --host 0.0.0.0 --port 3456
```

默认监听 `0.0.0.0:3456`。

### 健康检查

```bash
curl http://localhost:3456/health
```

成功响应：
```json
{
  "status": "ok",
  "timestamp": "2026-05-12T18:00:05.248077",
  "sqlite": true,
  "vectors": true
}
```

### 服务配置

当前无独立配置文件。如需修改端口或主机，在 uvicorn 命令行参数中指定：

```bash
uvicorn rag.src.server:app --host 127.0.0.1 --port 8080
```

---

## CLI 查询

### 基础查询

```bash
python rag/scripts/query.py "你的查询文本"
```

输出格式（纯文本 Context Pack）：
```
---
[知识上下文]
任务类型: humanization
查询: 这段太像 AI 写的
来源: 规则 x 1, 参考 x 2
摘要: 检索到 3 条相关知识点，涉及: 去AI味最小修改指南、4.2 断句与留白、2.13 动词同质化（"进行病"）

1. [规则] 去AI味最小修改指南 (相关性: 0.595)
   关键词匹配 + 语义接近 + 任务类型命中 + 规则文档
   ...
---
```

### 指定任务类型

```bash
python rag/scripts/query.py "这个大纲能展开吗" --task-type outline_review
```

### 控制返回数量

```bash
python rag/scripts/query.py "主角设定" --top-k 3
```

### JSON 格式输出

```bash
python rag/scripts/query.py "节奏太平" --json
```

### 仅路由分析

```bash
python rag/scripts/query.py "全民求生该先定哪条路线" --route-only
# → {"task_type": "genre_routing", "confidence": 0.48, ...}
```

### 启动服务

```bash
python rag/scripts/query.py --server
```

---

## API 接口详解

### `POST /retrieve`

核心检索接口。

**请求：**
```json
{
  "query": "这段太像 AI 写的",
  "task_type": "humanization",
  "project_hint": null,
  "top_k": 5
}
```

**参数说明：**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `query` | string | 是 | — | 检索查询文本 |
| `task_type` | string | 否 | 自动路由 | 见下方任务类型表 |
| `project_hint` | string | 否 | null | 项目提示（保留字段） |
| `top_k` | integer | 否 | 5 | 返回结果数量，1~20 |

**响应结构：**
```json
{
  "context_pack": {
    "task_type": "humanization",
    "query": "这段太像 AI 写的",
    "results": [
      {
        "chunk_id": "human-linguistics.去AI味最小修改指南.sec1",
        "title": "去AI味最小修改指南",
        "score": 0.595,
        "reason": "关键词匹配 + 语义接近 + 任务类型命中 + 规则文档",
        "snippet": "...",
        "source_path": ".harness/skills/human-linguistics/rules/去AI味最小修改指南.md",
        "source_type": "rule",
        "category": "common.humanization",
        "tags": ["去AI味最小修改指南", "human-linguistics", "去AI味最小修改指南"]
      }
    ],
    "knowledge_summary": "检索到 5 条相关知识点",
    "source_breakdown": {"rule": 2, "reference": 2, "project": 1},
    "meta": {
      "total_candidates": 30,
      "elapsed_ms": 58,
      "task_type": "humanization",
      "confidence": 0.54
    }
  },
  "context_text": "---\n[知识上下文]\n..."
}
```

`context_text` 是纯文本格式，可直接注入 Agent 的 system prompt。

### `POST /reindex`

重建全部索引。返回新的索引统计。

```bash
curl -X POST http://localhost:3456/reindex
```

响应：
```json
{
  "status": "ok",
  "documents": 23,
  "chunks": 233,
  "vectors": 233,
  "elapsed_seconds": 44.65
}
```

### `GET /health`

健康检查。

```bash
curl http://localhost:3456/health
```

### `GET /stats`

索引统计信息。

```bash
curl http://localhost:3456/stats
```

### `GET /routes`

查看所有任务路由定义。

```bash
curl http://localhost:3456/routes
```

### `POST /explain-retrieval`

调试接口，返回路由分析 + 详细检索结果。

```bash
curl -X POST http://localhost:3456/explain-retrieval \
  -H "Content-Type: application/json" \
  -d '{"query": "这段太像 AI 写的"}'
```

---

## 任务路由机制

### 7 种任务类型

| 任务类型 | 说明 | 典型查询 | 匹配分类 |
|----------|------|---------|---------|
| `ideation` | 构思发散 | "开脑洞想个题材" | common.ideation, common.outline |
| `outline_review` | 大纲审查 | "这个大纲能展开吗" | common.outline_review, common.consistency |
| `chapter_prewrite` | 写前准备 | "写之前该准备什么" | common.prewrite, common.outline |
| `humanization` | 去AI味 | "这段太AI了" | common.humanization, common.language, common.rhythm |
| `consistency_check` | 一致性检查 | "角色前后矛盾" | common.consistency, common.outline_review |
| `rhythm_review` | 节奏审查 | "节奏太慢了" | common.rhythm, common.outline_review, common.humanization |
| `genre_routing` | 题材选型 | "全民求生选路线" | common.project, common.outline, common.ideation |

### 路由算法

1. 将查询文本与每个任务类型的关键词列表做重叠度评分
2. 完整关键词命中：`score += len(keyword) * 2`
3. 部分字符匹配（>60% 重叠）：`score += len(keyword) * 0.5`
4. 乘以 weight_boost 系数
5. 取最高分作为匹配结果
6. 通过 `categories` 过滤 metadata，确保检索只返回相关分类的 chunks

### 配置路由

编辑 `rag/config/task-routes.json`：

```json
{
  "routes": {
    "humanization": {
      "description": "去AI味：语言自然化、改掉总结腔/解释腔",
      "categories": ["common.humanization", "common.language", "common.rhythm"],
      "stages": ["drafting", "revision", "review"],
      "keywords": ["AI", "去AI", "AI味", "总结腔", "解释腔", "自然", "修改", "润色"],
      "weight_boost": 1.2
    }
  }
}
```

修改后需要重建索引（`POST /reindex`）使新配置生效。

---

## 嵌入策略

三层嵌入策略，按优先级自动降级：

### 1. sentence-transformers（首选）

- **模型**: `paraphrase-multilingual-MiniLM-L12-v2`
- **输出维度**: 384
- **语言支持**: 多语言（含中文）
- **需要网络**: 首次运行需要下载模型（后续缓存到本地）
- **速度**: 单条嵌入 ~50ms（CPU）

### 2. TF-IDF + sklearn（回退）

- **触发条件**: sentence-transformers 加载失败或不可用
- **输出维度**: 词表大小（通常 7000+）
- **特点**: 纯本地，无需网络
- **构建**: 在索引构建时从语料训练，自动限制最多 20000 词

### 3. 哈希嵌入（最后防线）

- **触发条件**: 前两者均不可用
- **输出维度**: 384
- **特点**: 简单字符哈希，保证极端情况下系统不崩溃

---

## 验收测试

运行完整测试套件：

```bash
python rag/test/verify.py
```

测试覆盖 6 个类别：

| 类别 | 检查内容 | 典型项数 |
|------|---------|---------|
| 架构完整性 | 所有文件/配置/模式存在 | 23 |
| 知识源扫描 | 文件数、排除路径正确 | 9 |
| 任务路由 | 7 种查询路由准确 | 7 |
| 索引构建 | 文档数≥20、chunks≥200、向量一致 | 9 |
| 混合检索 | 4 个 TA 查询 top-3 命中、结果完备 | 17 |
| 结果稳定性 | 重复查询一致性 | 2 |

预期输出：
```
RAG 验收测试
==================================================
...
==================================================
  结果: 68 passed, 0 failed, 0 warnings
==================================================
```

---

## 故障排查

### 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `sqlite3.ProgrammingError: SQLite objects created in a thread` | 多线程访问单连接 | 已使用 thread-local 连接池，如出现请检查是否误用了全局 connection |
| `sentence-transformers` 模型下载失败 | 无网络连接 | 手动下载模型放入 `~/.cache/huggingface/hub/`，或系统自动回退到 TF-IDF |
| FTS5 搜索返回 0 结果 | query 为空或全部是停用词 | 确保查询包含非停用词的中文或英文 |
| 重建索引后结果没变化 | 向量缓存未更新 | 确认 `rag/data/` 下的 `.db` 文件和 `vectors.json` 已更新 |
| 服务启动报端口占用 | 端口 3456 已被占用 | 改用其他端口：`uvicorn rag.src.server:app --port 3457` |
| `gbk` 编码错误 | Windows 控制台编码问题 | 设置环境变量 `PYTHONIOENCODING=utf-8` |
| 向量检索返回空 | 向量文件不存在或为空 | 运行 `python rag/scripts/build_index.py` 重建索引 |

### 日志位置

- 索引构建日志：标准输出（stdout）
- 服务日志：uvicorn 标准输出
- 数据库文件：`rag/data/metadata.db`
- 向量文件：`rag/data/vectors/vectors.json`

### 重置到出厂状态

```bash
# 删除所有索引数据（索引会在下次 build 时重建）
rm -rf rag/data/

# 确认 .gitignore 中 rag/data/ 已被忽略
```

---

## Agent 集成指南

### 调用方式

Agent 可通过两种方式调用 RAG：

#### 方式一：HTTP API（推荐）

```python
import requests

response = requests.post("http://localhost:3456/retrieve", json={
    "query": "主角当前等级和属性",
    "task_type": "chapter_prewrite",
    "top_k": 5
})

data = response.json()
context_text = data["context_text"]  # 可直接注入 prompt
```

#### 方式二：直接 Python 调用

```python
import sys
sys.path.insert(0, ".")
from rag.src.retriever import hybrid_retrieve
from rag.src.context_pack import build_context_pack, context_pack_to_text

result = hybrid_retrieve(query="主角设定", task_type="chapter_prewrite")
pack = build_context_pack(query="主角设定", retrieval_result=result)
text = context_pack_to_text(pack)
```

### Context Pack 注入示例

```
你是一位网文写作助手。以下是相关知识上下文：

---
[知识上下文]
任务类型: humanization
查询: 这段太像 AI 写的
来源: 规则 x 1, 参考 x 2
摘要: 检索到 3 条相关知识点，涉及: 去AI味最小修改指南...

1. [规则] 去AI味最小修改指南 (相关性: 0.595)
   关键词匹配 + 语义接近 + 任务类型命中 + 规则文档
   ...

2. [参考] 4.2 断句与留白 (相关性: 0.487)
   语义接近 + 任务类型命中
   ...
---
```

### 任务类型选择建议

| Agent 角色 | 常用 task_type | 查询示例 |
|-----------|---------------|---------|
| 审稿 Agent | `humanization`, `consistency_check`, `rhythm_review` | "语病检查"、"角色矛盾" |
| 规划 Agent | `ideation`, `outline_review`, `genre_routing` | "开脑洞"、"大纲评估" |
| 写作 Agent | `chapter_prewrite` | "写前准备"、"角色设定" |
| 总编 Agent | 自动路由或根据子任务指定 | 根据委派的子任务决定 |

---

## 文件清单

### 源文件

| 路径 | 职责 |
|------|------|
| `rag/src/scanner.py` | 扫描 `.harness/skills/**/rules/, references/` 和 `.harness/projects/` |
| `rag/src/normalizer.py` | 读取 Markdown，提取 metadata（doc_id, category, stage, tags, priority） |
| `rag/src/chunker.py` | 按 heading 分割文档为语义块（300-900 字），检测 chunk_type |
| `rag/src/embedder.py` | 三层嵌入引擎：sentence-transformers → TF-IDF → hash |
| `rag/src/router.py` | 关键词重叠度评分 → 确定最佳 task_type |
| `rag/src/retriever.py` | 混合检索（FTS + 向量）+ 加权重排 |
| `rag/src/context_pack.py` | 构建标准化的 Context Pack（JSON + 纯文本） |
| `rag/src/indexer.py` | 编排完整索引构建流程（7 步） |
| `rag/src/server.py` | FastAPI 服务（6 个端点） |
| `rag/src/storage/sqlite_store.py` | SQLite + FTS5 持久化层（thread-local 连接） |
| `rag/src/storage/vector_store.py` | JSON 文件向量存储，余弦相似度检索 |

### 配置文件

| 路径 | 说明 |
|------|------|
| `rag/config/sources.json` | 知识源扫描范围（include/exclude） |
| `rag/config/task-routes.json` | 7 个任务类型的路由定义 |
| `rag/config/categories.json` | 分类定义 |

### Schema 定义

| 路径 | 说明 |
|------|------|
| `rag/schemas/document.schema.json` | 文档标准结构 |
| `rag/schemas/chunk.schema.json` | 分块标准结构 |
| `rag/schemas/context-pack.schema.json` | Context Pack 输出格式 |

### CLI 脚本

| 路径 | 命令 |
|------|------|
| `rag/scripts/build_index.py` | `python rag/scripts/build_index.py` |
| `rag/scripts/query.py` | `python rag/scripts/query.py "查询" [--options]` |
| `rag/scripts/ingest.py` | `python rag/scripts/ingest.py`（扫描预览） |

### 测试

| 路径 | 命令 |
|------|------|
| `rag/test/verify.py` | `python rag/test/verify.py` |
