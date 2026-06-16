# 总编模块索引

> 用途：总编 Agent 按任务找到对应专业 Agent、skill、规则和 L0 项目上下文。
> 注意：本文件是索引，不承载具体规则细节。

---

## 专业 Agent

| Agent | 职责 | 定义文件 |
|:------|:-----|:---------|
| 上下文 Agent | 状态追踪、伏笔管理、上下文打包、信息中枢 | `.harness/agents/上下文Agent.md` |
| 规划 Agent | 剧情构思、设定扩展、反转/钩子设计 | `.harness/agents/规划Agent.md` |
| 写作 Agent | 基于大纲、约束和上下文包生成正文 | `.harness/agents/写作Agent.md` |
| 审稿 Agent | 调用各审查子模块，执行全面或专项审查 | `.harness/agents/审稿Agent.md` |

---

## 审查与创作模块

| 题材/用途 | 子模块 skill | 说明 |
|:----------|:-------------|:-----|
| 数据化降临/游戏异界/副本流 | `.harness/skills/game-datafied` | 战斗描写规范、数值体系、装备/经验/战力逻辑 |
| 通用·降低 AI 语感 | `.harness/skills/human-linguistics` | AI 式语病诊断、语感词典、句式节奏、轻量去 AI 味 |
| 通用·情节一致性 | `.harness/skills/plot-review` | 角色行为一致性、时间线、伏笔、信息边界、状态一致 |
| 通用·节奏/爽点 | `.harness/skills/rhythm-review` | 高潮间隔、钩子密度、爽点分布、阅读体验体感 |
| 通用·创作灵感 | `.harness/skills/plot-ideation` | 剧情构思、设定扩展、反转/钩子、多方向推演 |
| 全局·知识包 | `.harness/knowledge` | 随项目自带知识包、MCP 下载知识包、RAG 可检索资料 |

---

## 常用规则文件

| 需求 | 加载文件 |
|:-----|:---------|
| 去 AI 味 | `.harness/skills/human-linguistics/rules/去AI味最小修改指南.md` |
| 查语病 | `.harness/skills/human-linguistics/rules/语病诊断手册.md` |
| 句式节奏 | `.harness/skills/human-linguistics/rules/句式节奏档案.md` |
| 角色关系 | `.harness/skills/plot-review/rules/角色关系金字塔.md` |
| 角色知识边界 | `.harness/skills/plot-review/rules/角色知识边界.md` |
| 状态一致性 | `.harness/skills/plot-review/rules/状态一致性补充清单.md` |
| 大纲质量 | `.harness/skills/plot-review/rules/大纲质量评估清单.md` |
| 阅读体验 | `.harness/skills/rhythm-review/references/阅读体验与章节润色检查.md` |
| 写前准备 | `.harness/skills/plot-ideation/references/章节写前准备清单.md` |

---

## 知识包缺口协调

当规划、写作、审稿或上下文 Agent 提示缺少题材、平台风格、去 AI 化或写作方法参考时，总编 Agent 不要让下属 Agent 硬编规则。

处理流程：

```text
发现缺口
  -> 按 .harness/knowledge/pack-recommendation.md 给用户候选知识包
  -> 用户确认
  -> MCP 安装 / RAG 重建
  -> 按 .harness/rules/subagent-runtime.md 恢复原任务
```

候选话术：

```text
检测到当前任务缺少 {题材/风格/审稿} 参考包。
可选素材包：
1. {pack_id}：{name}（匹配原因）
2. {pack_id}：{name}（相近参考）
你要启用哪一个？未确认前我不会强制使用。
```

---

## L0 项目上下文索引

| 文件 | 用途 | 使用时机 |
|:-----|:-----|:---------|
| `.harness/current-project.md` | 当前项目指针 | 每次启动 Step -1 时读取 |
| `.harness/project-templates/模板-数据化降临.md` | 数据化降临题材创作约束 | 项目设置为该题材时加载 |
| `.harness/project-templates/模板-末世小黑屋.md` | 末世小黑屋题材创作约束 | 项目设置为该题材时加载 |
