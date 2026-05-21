# novel-harness Codex 入口规则

本仓库是 `novel-harness` 小说创作系统。用户提出小说创作、审稿、规划、去 AI 味、题材分析、章节续写等请求时，必须优先进入 novel-harness 流程，而不是按普通问答处理。

## 自动触发范围

当用户请求包含以下意图时，先加载 `.harness/agents/总编Agent.md`：

- `/novel-core`
- 帮我写小说、写一章、写正文、续写、开书
- 帮我构思、没灵感、后面怎么写、设计反转、设计大纲
- 帮我审稿、查问题、查语病、查节奏、查逻辑
- 去 AI 味、润色、人性化、提高人工特征
- 分析题材、拆书、参考某本小说完善规则

## 默认启动流程

1. 读取 `.harness/agents/总编Agent.md`，把它当作 L1 总编 Agent 入口。
2. 读取 `.harness/current-project.md`，确认当前小说项目。
3. 如果当前项目仍是模板占位，先询问用户最少必要信息：
   - 书名或项目名
   - 题材
   - 主角
   - 一句话世界观或开局设定
4. 按任务类型加载对应 Agent：
   - 规划/大纲/剧情方向：`.harness/agents/规划Agent.md`
   - 写正文/续写章节：`.harness/agents/写作Agent.md`
   - 审稿/去 AI 味/查问题：`.harness/agents/审稿Agent.md`
   - 长篇状态、伏笔、设定延续：`.harness/agents/上下文Agent.md`
5. 需要语感、人性化、去 AI 味时，按需加载：
   - `.harness/skills/human-linguistics/SKILL.md`
   - `.harness/skills/human-linguistics/rules/去AI味最小修改指南.md`
   - `.harness/skills/human-linguistics/rules/语病诊断手册.md`
   - 题材相关参考文件，如求生、电竞等 references。

## 写小说请求的默认行为

用户只说“帮我写小说”或 `/novel-core 帮我写小说` 时，不要直接生成正文。先进入开书规划：

1. 判断是否已有当前项目。
2. 没有项目时，引导创建项目档案。
3. 有项目但缺少大纲时，先让规划 Agent 输出 2-3 个开局方向。
4. 用户确认方向后，再调用写作 Agent 写正文。
5. 正文生成后，默认用审稿 Agent 做一次轻量检查。

## 重要约束

- `.harness/agents/总编Agent.md` 是 novel-harness 的总编入口；本文件负责把用户请求路由过去。
- 不要把 `legacy-skills/` 当作当前系统入口。它是本地旧版资产，已从 Git 跟踪移除。
- 不要在没有项目上下文时直接长篇输出正文。
- 不要把 `.harness/agents/` 当作普通资料全部一次性加载，只按任务需要加载对应 Agent。
- 修改项目文件时，先保护用户已有正文和本地未提交内容。
