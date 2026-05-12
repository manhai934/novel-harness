# Novel-Harness — 长篇网文 AI 创作系统

> 基于 Harness Engineering 方法论构建的长篇网络小说辅助创作系统。
> 目标：支持 100-200 万字量级的连载创作，解决 AI 写作中的遗忘和幻觉问题。
> 核心理念：**写小说不是一个 skill，是一个 Agent 系统。**

[![LINUXDO](https://img.shields.io/badge/%E7%A4%BE%E5%8C%BA-LINUXDO-0086c9?style=for-the-badge&labelColor=555555)](https://linux.do)

---

## 一句话

novel-harness 是一个**四层 Agent 系统**，不是普通的写作工具。你告诉它"帮我写一章"，它自动完成：状态打包 → 正文生成 → 归档更新 → 质量审查 → 结果呈现。

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/manhai934/novel-harness.git
cd novel-harness

# 2. 安装 RAG 知识检索依赖
pip install -r rag/requirements.txt
python rag/scripts/build_index.py

# 3. 在 Claude 中打开项目，开始写作
```

```
你："帮我写第二章"
系统：上下文打包 → 写作 Agent 写正文 → 归档更新 → 审稿 → 呈现结果
你："帮我审稿"
系统：委派审稿 Agent，检查语感/情节/节奏/题材
你："没灵感"
系统：委派规划 Agent，提供 3-5 个剧情方向
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
│   ├── src/                    ← 索引、检索、路由、HTTP 服务
│   └── OPERATIONS.md           ← RAG 操作手册
└── docs/                       ← 详细文档
```

---

## 文档导航

| 你想了解什么 | 去这里 |
|-------------|--------|
| 系统设计思路、L0-L3 分层详解 | `docs/architecture.md` |
| 5 个 Agent 各负责什么、怎么协作 | `docs/agents.md` |
| 写一章的完整流程、200 万字创作周期 | `docs/pipeline.md` |
| 状态/记忆/上下文包怎么工作 | `docs/pipeline.md` |
| 开始写作前的准备、项目自定义 | `docs/usage.md` |
| Git 工作流、与普通 Skill 的区别 | `docs/usage.md` |
| RAG 安装、API 调用、故障排查 | `rag/OPERATIONS.md` |

---

## 致谢

感谢 **`linux.do`** 社区的讨论、分享与支持。感谢 [oh-story-claudecode](https://github.com/worldwonderer/oh-story-claudecode) 和 [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) 给我的启发。
