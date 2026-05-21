# 系统架构

> 本文档详细说明 novel-harness 的四层架构设计、入口边界和目录结构。

---

## 四层架构（L0-L3）

```
L0（项目上下文）
   ├── 当前写哪本小说
   ├── 创作约束（成长曲线/防膨胀/阶段天花板）
   └── 文件：.harness/

L1（总编层）
   ├── 理解需求 → 分派任务 → 协调流程
   ├── 不执行具体工作，只做调度和质量管理
   └── 文件：.harness/agents/总编Agent.md

L2（专业 Agent 层）
   ├── 上下文 Agent — 状态管理 + 信息打包
   ├── 规划 Agent — 剧情构思 + 大纲生成
   ├── 写作 Agent — 正文生成
   ├── 审稿 Agent — 质量审查
   └── 文件：agents/*.md

L3（数据层）
   ├── 项目文件：projects/{项目名}/正文/ 状态/ 记忆/
   ├── 审查规则：game-datafied/ human-linguistics/ plot-review/ rhythm-review/
   ├── 案例库：cases/
   └── RAG 知识检索层：rag/ (混合检索 + Context Pack)
```

### L0 — 项目上下文

最底层，定义"当前在写什么"。

- `.harness/current-project.md`：指向当前激活的小说项目
- `.harness/projects/`：各题材的创作约束模板（成长曲线、防膨胀策略等）
- 所有上层 Agent 在做出决策前都会读取 L0 的约束

### L1 — 总编层

系统入口。唯一直接面对用户的层。

- 定义在 `.harness/agents/总编Agent.md` 中
- 接收用户的自然语言需求，理解意图，分派给对应的 L2 Agent
- 不做具体执行，只做调度和质量管理

### L2 — 专业 Agent 层

四个专业 Agent，各司其职：

| Agent | 职责 | 交付物 |
|-------|------|--------|
| 上下文 Agent | 主角状态追踪、伏笔管理、事件索引 | 上下文包 |
| 规划 Agent | 剧情构思、大纲生成、设定扩展 | 3-5 个剧情方向 |
| 写作 Agent | 按大纲和上下文包生成正文 | 2000-3000 字正文 |
| 审稿 Agent | 质量审查（语感/设定/情节/节奏） | 审查报告 |

### L3 — 数据层

所有的数据和知识存储：

- **项目文件**：正文、大纲、设定、状态、记忆
- **审查规则**：各 skill 模块的规则和参考文档
- **RAG 知识检索**：为 Agent 提供即时知识查询的混合检索层

---

## 入口与目录边界

系统不再把多个独立 skill 直接暴露给用户选择，而是收束为一个总编入口：

- `README.md`：用户入口，说明项目怎么用、目录怎么理解。
- `skills/novel-core/SKILL.md`：Codex Skill 安装入口，负责触发 `/novel-core` 并路由到总编 Agent。
- `.harness/agents/总编Agent.md`：Agent 核心入口，由总编 Agent 识别需求、分派上下文/规划/写作/审稿任务。
- `.harness/skills/`：Harness 内部能力模块，只由 Agent 或工作流按需调用。
- `legacy-skills/`：旧版导入 skill 资产，不作为当前主入口。其中有价值的资料后续逐步迁移到 Harness 模块或 RAG 参考库。

这种收束是一次架构升级：用户不需要在大量 skill 中猜该调用哪一个，只需要描述目标，由总编 Agent 负责判断该走哪条流程、加载哪些模块和参考资料。

---

## 文件结构

```
novel-harness/
│
├── README.md                          ← 用户入口
├── AGENTS.md                          ← Codex / OpenCode 项目入口规则
├── CLAUDE.md                          ← Claude Code / Cursor 可参考入口规则
├── skills/novel-core/                 ← Codex Skill 安装入口
├── scripts/install-skill.ps1          ← Skill 安装脚本
│
├── projects/                         ← 小说项目（你的创作内容）
│   ├── .gitkeep                      ← 仅用于保留目录
│   └── {项目名}/                     ← 本地创作内容，默认不上传
│       ├── 正文/                     ← 已完成的章节
│       ├── 大纲/                     ← 创作蓝图
│       ├── 设定/                     ← 世界观/数值/角色设定
│       ├── 状态/                     ← ★ 上下文 Agent 维护
│       │   ├── 主角.md               ← 主角当前状态
│       │   ├── 角色/                 ← 配角状态
│       │   └── 伏笔登记表.md         ← 伏笔生命周期
│       └── 记忆/                     ← ★ 上下文 Agent 维护
│           ├── 事件索引.md           ← 重大事件按章索引
│           ├── 章节摘要/             ← 每章 200 字摘要
│           └── 风格参考.md           ← 最近 N 章风格特征
│
├── .harness/                         ← Harness 核心工程系统
│   ├── current-project.md            ← 当前项目指针
│   ├── projects/                     ← 项目约束模板
│   ├── agents/
│   │   ├── 总编Agent.md              ← L1 协调层
│   │   ├── 上下文Agent.md            ← 记忆中枢
│   │   ├── 规划Agent.md              ← 剧情构思
│   │   ├── 写作Agent.md              ← 正文生成
│   │   └── 审稿Agent.md              ← 质量审查
│   ├── skills/
│   │   ├── game-datafied/            ← 题材审查
│   │   ├── human-linguistics/        ← 语感审查
│   │   ├── plot-review/              ← 情节审查
│   │   ├── rhythm-review/            ← 节奏审查
│   │   └── plot-ideation/            ← 创作灵感
│   ├── rules/                        ← 辅助规则
│   ├── memory/                       ← 记忆系统模板
│   └── cases/                        ← 案例/反馈
│
├── rag/                              ← L3 知识检索层
│   ├── src/                          ← 索引、检索、路由、服务
│   ├── scripts/                      ← 构建/查询 CLI
│   ├── config/                       ← 知识源/路由配置
│   ├── test/                         ← 验收测试
│   └── OPERATIONS.md                 ← 操作手册
│
├── docs/                             ← 详细文档
│   ├── architecture.md               ← 本文
│   ├── agents.md                     ← Agent 体系
│   ├── pipeline.md                   ← 创作管线
│   └── usage.md                      ← 使用指南
│
└── legacy-skills/                    ← 旧版导入 skill 资产（保留待迁移）
```

### 重要注释

- `.workspace/` 旧入口已废弃；当前项目指针统一使用 `.harness/current-project.md`
- `projects/` 会随仓库保留为空目录，但其中具体小说正文、设定、状态和记忆文件默认被 `.gitignore` 忽略，不上传到远程
- `legacy-skills/` 不是当前主入口。当前主入口是根目录 `README.md`、`AGENTS.md`、`CLAUDE.md`、`skills/novel-core/` 和 `.harness/agents/总编Agent.md`
- `.harness/skills/` 是内部模块目录，当前仍被 Agent 文档引用
