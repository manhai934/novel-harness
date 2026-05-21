# 安装 novel-core

本文档用于让 AI 工具帮助用户安装 `novel-core`。用户不需要手动理解目录结构，只需要把对应提示词发给当前 AI 工具。

## 一句话安装

把下面这段话发给 Codex、Claude Code、Cursor 或 OpenCode：

```text
请帮我安装当前项目的 novel-core 入口。

安装目标：
1. 让我之后可以用 `/novel-core 帮我写小说` 触发 novel-harness。
2. 使用本仓库的 `skills/novel-core/SKILL.md` 作为 Skill 入口。
3. 真实核心规则在 `.harness/agents/总编Agent.md`。
4. 如果当前工具支持 Skill 目录，请把 `skills/novel-core/` 安装到该工具的 Skills 目录。
5. 如果当前工具不支持 Skill 安装，请把本项目作为工作目录打开，并按 `AGENTS.md` 或 `CLAUDE.md` 路由。
6. 安装后请验证：能找到 `skills/novel-core/SKILL.md`，能找到 `.harness/agents/总编Agent.md`。
```

## Codex 安装方式

如果 AI 工具是 Codex，可以让它执行：

```text
请在当前仓库执行 `scripts/install-skill.ps1`，把 `skills/novel-core/` 安装到 Codex 的 skills 目录。
安装后确认 `~/.codex/skills/novel-core/SKILL.md` 存在。
```

安装完成后使用：

```text
/novel-core 帮我写小说
```

## Claude Code / Cursor / OpenCode 使用方式

这些工具不一定有统一的 Skill 安装目录。更稳的方式是把 `novel-harness` 作为项目目录打开，然后让 AI 读取项目入口：

```text
请按当前项目的 `AGENTS.md` 或 `CLAUDE.md` 工作。
当我输入 `/novel-core`、写小说、审稿、规划剧情、去AI味时，
请先加载 `.harness/agents/总编Agent.md`，
再按任务读取 `.harness/agents/规划Agent.md`、`写作Agent.md`、`审稿Agent.md`、`上下文Agent.md`。
```

## 手动备用方式

如果 AI 工具无法代为安装，可以手动执行：

```powershell
git clone https://github.com/manhai934/novel-harness.git
cd novel-harness
powershell -ExecutionPolicy Bypass -File scripts/install-skill.ps1
```

## 验证

安装或打开项目后，让 AI 检查：

```text
请验证 novel-core 是否可用：
1. `skills/novel-core/SKILL.md` 是否存在
2. `.harness/agents/总编Agent.md` 是否存在
3. `/novel-core 帮我写小说` 是否会进入开书规划，而不是直接生成正文
```
