# Novel-Harness — 长篇网文 AI 创作系统

> 基于 Harness Engineering 方法论构建的长篇网络小说辅助创作系统。
> 目标：支持 100-200 万字量级的连载创作，解决 AI 写作中的遗忘和幻觉问题。
> 核心理念：**写小说不是一个 skill，是一个 Agent 系统。**

---

## 一句话介绍

novel-harness 是一个**四层 Agent 系统**，不是普通的写作工具。你告诉它"帮我写一章"，它自动完成：状态打包 → 正文生成 → 归档更新 → 质量审查 → 结果呈现。

## 详细文档

- [系统架构](docs/architecture.md) — L0-L3 分层、入口边界
- [Agent 体系](docs/agents.md) — 总编与 4 个 Agent 职责与协作
- [创作管线](docs/pipeline.md) — 单章流水线、200 万字周期、状态与记忆
- [项目自定义与 Git 工作流](docs/usage.md) — 约束模板、版本管理
- [RAG 操作手册](rag/OPERATIONS.md) — 安装部署、API 调用、故障排查

## 快速开始

### 安装

```bash
# 克隆
git clone https://github.com/manhai934/novel-harness.git
cd novel-harness

# 安装 RAG 知识检索依赖
pip install -r rag/requirements.txt
python rag/scripts/build_index.py
```

### 创建小说项目

在 Claude 中打开项目，告诉总编 Agent：

```
你：帮我创建新项目
Agent：好的，几个问题：
  1. 书名？
  2. 题材？（数据化降临 / 末世小黑屋 / 其他）
  3. 主角叫什么？
  4. 一句话世界观？

确认后生成：
  projects/{书名}/
  ├── 正文/
  ├── 状态/（由上下文 Agent 自动维护）
  └── 记忆/（由上下文 Agent 自动维护）
```

### 日常写作

```
你：帮我写第二章
→ 总编 Agent 协调全流程：上下文打包 → 写作 → 归档 → 审稿 → 呈现结果

你：帮我审稿
→ 委派审稿 Agent，检查语感/设定/情节/节奏

你：没灵感，后面怎么写
→ 委派规划 Agent，提供 3-5 个剧情方向及对比
```

---

## 架构一览

```
┌─────────────────────────────────────────────────────┐
│  L1  总编 Agent (SKILL.md)                          │
│      理解需求 → 分派任务 → 协调流程 → 质量裁定         │
├──────┬──────┬──────┬──────┬──────────────────────────┤
│ L2   │ 上下文 │ 规划  │ 写作  │ 审稿                    │
│      │ Agent  │ Agent │ Agent │ Agent                   │
├──────┴──────┴──────┴──────┴──────────────────────────┤
│ L3   projects/  .harness/skills/  rag/ (RAG 知识检索)  │
├──────────────────────────────────────────────────────┤
│ L0   .harness/ (项目约束、当前项目指针)                  │
└──────────────────────────────────────────────────────┘
```

---

## 文件结构

```
novel-harness/
├── SKILL.md                    ← 总编 Agent 定义（系统入口）
├── .harness/                   ← Harness 核心工程系统
│   ├── agents/                 ← 4 个专业 Agent 定义
│   ├── skills/                 ← 题材/语感/情节/节奏/灵感模块
│   ├── projects/               ← 项目约束模板
│   └── memory/                 ← 记忆系统模板
├── projects/                   ← 你的小说项目（正文/大纲/状态/记忆）
├── rag/                        ← ★ RAG 知识检索层
│   └── OPERATIONS.md           ← 操作手册
└── docs/                       ← 详细文档
```
---

## 致谢

[![LINUXDO](https://img.shields.io/badge/%E7%A4%BE%E5%8C%BA-LINUXDO-0086c9?style=for-the-badge&labelColor=555555)](https://linux.do)

感谢 **`linux.do`** 社区的讨论、分享与支持。这个项目在方法论整理、实践思路和持续迭代上，都受益于社区氛围与成员交流。

感谢 [oh-story-claudecode](https://github.com/worldwonderer/oh-story-claudecode) 和 [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) 给我的启发，前者是我入门老师，后者是我从 skill 进化到 harness 后的进一步完善方向，都给我提供了很多思路。
