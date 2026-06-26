# novel-harness Claude 入口规则

本仓库是 `novel-harness` 小说创作系统。用户提出小说创作、审稿、规划、去 AI 味、题材分析、章节续写等请求时，优先进入 novel-harness 流程。

## 入口说明

`.harness/agents/总编Agent.md` 是 novel-harness 的 L1 总编 Agent 定义，但普通对话模型不会自动把它当作运行入口。当前文件用于提醒 Claude/Cursor 类工具：遇到小说创作相关请求时，先读取 `.harness/agents/总编Agent.md`，再按 `.harness/agents/` 分派任务。

## 自动触发

以下请求必须先加载 `.harness/agents/总编Agent.md`：

- `/novel-core`
- 帮我写小说、写一章、写正文、续写、开书
- 帮我构思、没灵感、后面怎么写、设计反转、设计大纲
- 帮我审稿、查问题、查语病、查节奏、查逻辑
- 去 AI 味、润色、人性化、提高人工特征
- 分析题材、拆书、参考某本小说完善规则

## 默认流程

1. 读取 `.harness/agents/总编Agent.md`，作为总编 Agent 入口。
2. 读取 `.harness/current-project.md`，确认当前小说项目。
3. 如果当前项目仍是模板占位，先询问用户：
   - 书名或项目名
   - 题材
   - 目标平台（不确定时让用户选：番茄新手向 / 起点长线向 / 先不限定）
   - 主角
   - 一句话世界观或开局设定
4. 按任务类型读取对应 Agent：
   - 规划/大纲/剧情方向：`.harness/agents/规划Agent.md`
   - 写正文/续写章节：`.harness/agents/写作Agent.md`
   - 审稿/去 AI 味/查问题：`.harness/agents/审稿Agent.md`
   - 长篇状态、伏笔、设定延续：`.harness/agents/上下文Agent.md`
5. 需要语感、人性化、去 AI 味时，按需读取：
   - `.harness/skills/human-linguistics/SKILL.md`
   - `.harness/skills/human-linguistics/rules/去AI味最小修改指南.md`
   - `.harness/skills/human-linguistics/rules/语病诊断手册.md`
   - `.harness/knowledge/` 中已安装的题材、写作、去 AI 化知识包。
   - `.harness/skills/human-linguistics/references/` 下的题材参考。
6. 如果缺少对应题材或平台风格知识包，提示用户可通过 MCP 下载额外知识包，并重建 RAG 索引后继续。

## 写小说请求默认行为

用户只说“帮我写小说”或 `/novel-core 帮我写小说` 时，不要直接生成正文。

先做开书规划：

1. 判断是否已有当前项目。
2. 没有项目时，引导创建项目档案。
3. 如果用户不知道写什么、已有项目未记录目标平台，或没有明确目标平台，先做平台素材推荐：新手优先番茄热门方向，再补起点长线结构对照；不要默认只搜索起点。
4. 有项目但缺少大纲时，先输出 2-3 个开局方向。
5. 用户确认方向后，再写正文。
6. 正文生成后，默认做一次轻量审稿。

## 约束

- 不要把 `legacy-skills/` 当作当前入口，它是本地旧版资产。
- 不要一次性加载 `.harness/agents/` 全部文件，只按任务读取。
- 不要在没有项目上下文时直接长篇输出正文。
- 修改正文前，先确认用户是要“直接修改文件”还是“先给方案”。
