---
name: novel-core
description: 当用户使用 /novel-core，或请求写长篇网文、开书、规划剧情、写章节、审稿、去AI味、人性化润色、分析题材参考时使用。该 skill 是 novel-harness 工程的启动入口，会加载 .harness/agents/总编Agent.md，并按 .harness/agents/ 路由到规划、写作、审稿、上下文 Agent。
---

# novel-core

这是 `novel-harness` 小说创作工程的 thin skill 入口。

## 触发方式

用户出现以下任一请求时使用本 skill：

- `/novel-core 帮我写小说`
- `/novel-core 帮我规划一本小说`
- `/novel-core 帮我写一章`
- `/novel-core 去AI味`
- `/novel-core 审稿`
- 写小说、开书、规划剧情、续写章节、查语病、查节奏、查逻辑、人性化润色、题材拆解

## 启动流程

1. 定位 `novel-harness` 工程根目录。
   - 优先使用当前工作目录。
   - 如果当前目录不是 novel-harness，询问用户提供仓库路径。
   - 判断依据：根目录存在 `.harness/agents/总编Agent.md`、`.harness/agents/`、`.harness/skills/`。
2. 读取 `.harness/agents/总编Agent.md`，作为 L1 总编 Agent。
3. 读取 `.harness/current-project.md`，确认当前小说项目。
4. 如果当前项目仍是模板占位，先询问：
   - 书名或项目名
   - 题材
   - 目标平台（不确定时让用户选：番茄新手向 / 起点长线向 / 先不限定）
   - 主角
   - 一句话世界观或开局设定
5. 根据任务类型按需读取对应 Agent：
   - 规划/大纲/剧情方向：`.harness/agents/规划Agent.md`
   - 写正文/续写章节：`.harness/agents/写作Agent.md`
   - 审稿/去 AI 味/查问题：`.harness/agents/审稿Agent.md`
   - 长篇状态、伏笔、设定延续：`.harness/agents/上下文Agent.md`
6. 需要语感、人性化、去 AI 味时，按需读取：
   - `.harness/skills/human-linguistics/SKILL.md`
   - `.harness/skills/human-linguistics/rules/去AI味最小修改指南.md`
   - `.harness/skills/human-linguistics/rules/语病诊断手册.md`
   - `.harness/knowledge/` 中已安装的题材、写作、去 AI 化知识包。
   - `.harness/skills/human-linguistics/references/` 下的题材参考。
7. 如果缺少对应题材、平台风格或专项审稿知识包，提示用户可通过 MCP/知识包同步工具安装扩展知识包，并重建 RAG 索引后继续。

## 默认行为

用户只说“帮我写小说”时，不要直接生成正文。

先进入开书规划：

1. 判断是否已有当前项目。
2. 没有项目时，引导创建项目档案。
3. 如果用户不知道写什么、已有项目未记录目标平台，或没有明确目标平台，先做平台素材推荐：新手优先番茄热门方向，再补起点长线结构对照；不要默认只搜索起点。
4. 有项目但缺少大纲时，先输出 2-3 个开局方向。
5. 用户确认方向后，再写正文。
6. 正文生成后，默认做一次轻量审稿。

开书推荐必须保持流程进度：

- 推荐题材、平台或知识包时，只返回候选，不直接写大纲或正文。
- 候选只推荐一轮；用户选择后立刻锁定 `selected_topic / selected_platform / selected_pack`。
- 锁定后恢复开书流程，提示下一步，不要丢失 `next_action`。

## 约束

- 不要把 `legacy-skills/` 当作当前入口。
- 不要一次性加载 `.harness/agents/` 全部文件，只按任务读取。
- 不要在没有项目上下文时直接长篇输出正文。
- 修改正文前，先确认用户是要“直接修改文件”还是“先给方案”。
