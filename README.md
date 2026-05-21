# Novel-Harness

`novel-harness` 是一个面向网络小说创作的 AI Agent 工程。

它的目标不是让 AI 临时写一段正文，而是让 AI 按“项目状态、题材规则、上下文记忆、审稿规则”持续协作写书。

一句话使用：

```text
/novel-core 帮我写小说
```

---

## 最快开始

### 1. 安装项目

```powershell
git clone https://github.com/manhai934/novel-harness.git
cd novel-harness
powershell -ExecutionPolicy Bypass -File scripts/install-skill.ps1
```

安装后，在 Codex 里可以直接使用：

```text
/novel-core 帮我写小说
```

如果你用的是 Claude Code、Cursor、OpenCode 等工具，也可以直接打开 `novel-harness` 目录，然后输入同样的指令。项目内的 `AGENTS.md`、`CLAUDE.md` 会告诉 AI 如何进入本工程流程。

### 2. 第一次开书

如果还没有小说项目，输入：

```text
/novel-core 帮我创建新小说项目
```

AI 会先问最少必要信息：

```text
1. 书名或项目名
2. 题材，例如：全民求生、游戏降临、末日经营、都市异能
3. 主角是谁
4. 一句话世界观或开局设定
```

确认后，再继续：

```text
/novel-core 帮我规划黄金三章
/novel-core 写第一章
/novel-core 审一下这一章
```

---

## 常用指令

### 写小说

```text
/novel-core 帮我写小说
/novel-core 帮我写第一章
/novel-core 续写下一章
/novel-core 按当前大纲写一段正文
```

只说“帮我写小说”时，系统不会直接乱写正文，而是先进入开书规划，确认题材、主角、世界观和开局方向。

### 规划剧情

```text
/novel-core 帮我规划一本全民求生文
/novel-core 设计黄金三章
/novel-core 后面怎么写
/novel-core 给我 3 个反转方向
```

适合用来做开书、黄金三章、阶段大纲、爽点链条、反转设计。

### 审稿修文

```text
/novel-core 帮我审稿
/novel-core 查一下逻辑问题
/novel-core 查一下节奏和爽点
/novel-core 这章哪里不像真人作者写的
```

适合检查语病、设定冲突、角色行为不合理、节奏拖沓、解释感过重等问题。

### 去 AI 味

```text
/novel-core 去AI味
/novel-core 帮我提高人工特征
/novel-core 这段太像AI了，帮我改自然
```

系统会优先加载 `human-linguistics` 模块，重点处理：

- 过度解释、过度因果
- 自问自答、判定式短句
- 段尾总结、口号式升华
- 句式过齐、节奏过工整
- 角色反应太标准、缺少真实作者的松弛感

---

## 去 AI 化效果示例

`human-linguistics` 模块用于把偏工整、解释感重的 AI 文风，调整成更接近真人网文作者的叙述口气。

| 优化前 | 优化后 |
|:---:|:---:|
| ![去 AI 化优化前](docs/assets/deslop-before.png) | ![去 AI 化优化后](docs/assets/deslop-after.png) |

---

## 它实际怎么工作

`novel-harness` 把写小说拆成几个角色协作：

| 角色 | 负责什么 |
|:---|:---|
| 总编 Agent | 理解你的需求，决定该调用哪个专业 Agent |
| 规划 Agent | 做题材定位、大纲、黄金三章、反转、爽点设计 |
| 写作 Agent | 按当前项目状态和大纲写正文 |
| 审稿 Agent | 查逻辑、节奏、语病、AI 味、设定一致性 |
| 上下文 Agent | 管理当前项目、章节摘要、角色状态、伏笔和记忆 |

触发链路大致是：

```text
你输入 /novel-core
  -> AGENTS.md / CLAUDE.md / Codex Skill 入口
  -> .harness/agents/总编Agent.md
  -> .harness/agents/ 专业 Agent
  -> .harness/skills/ 题材规则、语感规则、审稿规则
```

你不需要每次手动指定这些文件。正常情况下，只要在项目目录里输入 `/novel-core ...`，AI 就会按入口规则加载。

---

## 目录说明

```text
novel-harness/
├── README.md                  # 项目说明
├── AGENTS.md                  # Codex / OpenCode 入口规则
├── CLAUDE.md                  # Claude Code / Cursor 可参考入口规则
├── skills/novel-core/         # 可安装的 Codex Skill 入口
├── scripts/install-skill.ps1  # Codex Skill 安装脚本
├── .harness/                  # 核心 Agent、规则、模板
│   ├── agents/                # 总编 / 规划 / 写作 / 审稿 / 上下文 Agent
│   ├── skills/                # 题材、语感、情节、节奏模块
│   ├── projects/              # 小说项目约束模板
│   └── memory/                # 章节、角色、伏笔、事件记忆模板
├── projects/                  # 本地小说正文项目，默认不提交 Git
├── rag/                       # 轻量 RAG 检索模块
└── docs/                      # 详细设计文档
```

---

## 关于 RAG

RAG 用来检索项目里的参考资料，例如：

- 求生、游戏、电竞等题材参考
- 去 AI 味规则
- 审稿规则
- 已整理的案例文档

第一次写小说不需要先启动 RAG。等参考文档变多、需要“自动从资料库里找最合适规则”时再启用。

启用方式：

```powershell
pip install -r rag/requirements.txt
python rag/scripts/build_index.py
```

详细说明见：[RAG 操作手册](rag/OPERATIONS.md)

---

## 详细文档

- [系统架构](docs/architecture.md)
- [Agent 体系](docs/agents.md)
- [创作管线](docs/pipeline.md)
- [项目自定义与 Git 工作流](docs/usage.md)
- [RAG 操作手册](rag/OPERATIONS.md)

---

## 致谢

[![LINUXDO](https://img.shields.io/badge/%E7%A4%BE%E5%8C%BA-LINUXDO-0086c9?style=for-the-badge&labelColor=555555)](https://linux.do)

感谢 **linux.do** 社区的讨论、分享与支持。这个项目在方法论整理、实践思路和持续迭代上，都受益于社区氛围与成员交流。

感谢 [oh-story-claudecode](https://github.com/worldwonderer/oh-story-claudecode) 和 [webnovel-writer](https://github.com/lingfengQAQ/webnovel-writer) 给本项目带来的启发。
