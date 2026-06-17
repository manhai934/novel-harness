# 知识包素材推荐规则

> 用途：在开书、故事背景设计、大纲规划、章节写作前，给用户推荐可选知识包和素材方向。
> 核心原则：只推荐选项，不在用户确认前强制启用任何题材包。
> 协作边界：推荐、安装和 RAG 查询必须遵循 `../rules/subagent-runtime.md` 的知识作用域隔离规则。

---

## 1. 触发场景

以下任务开始前，先进入素材/知识包推荐步骤：

- 开书、创建新小说项目。
- 设计故事背景、世界观、主角设定、金手指、题材卖点。
- 规划黄金三章、卷纲、章纲。
- 写第一章、续写章节、按大纲写正文。
- 用户要求参考某类题材、平台风格、去 AI 化规则或写法模板。

如果用户只是让你审稿、查语病、解释规则，可以不主动推荐题材包，但可按需推荐 `deslop-basic`、`webnovel-writing-basic` 等通用包。

---

## 2. 推荐流程

```text
用户请求
  -> 提取方向：题材 / 平台 / 写作阶段 / 审稿目标 / 去 AI 化目标
  -> 保存任务恢复点：原始请求 / 目标 Agent / 当前步骤 / 已有上下文 / 下一步动作
  -> 查询本地 included + remote installed + server available
  -> 找精确匹配
  -> 找不到精确匹配时，给相近选项
  -> 让用户选择
  -> 用户确认后才安装/启用
  -> 安装/启用并重建 RAG
  -> 注入已确认参考知识包
  -> 从任务恢复点继续原任务
```

必须遵守：

- 不可自己强制使用未确认的题材包。
- 不可把“相近知识包”当成“已经匹配”。
- 不可因为本地已有某包就默认启用到无关题材。
- 不可为了凑资料，把玄幻、游戏、求生等强题材包混入普通都市、现实、言情等任务。
- 不可在安装知识包后丢失原任务；必须恢复到推荐知识包前被挂起的步骤。
- 不可把 RAG 或 subagent 查询到的知识直接写入项目长期设定，除非用户确认。

---

## 3. 用户方向处理

### 3.1 用户方向明确

用户已经说出题材或方向时，直接找对应或相近知识包。

示例：

```text
用户：我想写规则怪谈。
总编：先给你找规则怪谈相关素材包，可选：
1. topic-rule-horror：规则怪谈题材参考包（更精准）
2. library-topic-horror-weird：恐怖灵异与规则怪谈资料包（范围更大）
是否安装/启用其中一个？
```

### 3.2 用户方向模糊

用户只说“帮我写小说”“没灵感”“帮我开书”时，先询问素材类型，不直接进入正文。

推荐询问：

```text
你想先找哪类素材？
1. 题材方向：玄幻、求生、规则怪谈、都市、女频、短篇等
2. 写法方法：黄金三章、大纲、人物关系、战斗场景、去 AI 味
3. 平台/市场：番茄、起点、知乎短篇、短剧感等
4. 暂不找素材，先用通用写作包开书
```

新手平台提示：

- 如果用户不知道写什么、没有明确平台，素材推荐不要只看起点。
- 番茄小说更适合新手找方向，优先用于观察大众题材、强钩子、快节奏、低门槛爽点。
- 起点适合参考长线结构、设定纵深、升级体系和老读者口味，但不要一开始就用起点标准压新手。
- 默认建议同时给“番茄方向参考”和“起点方向参考”，让用户选择平台口味。
- 如果只能先推荐一个市场方向，Lv.1 新手优先推荐番茄；Lv.2/Lv.3 再根据题材和目标判断是否转向起点。
- 任何平台都不能作为默认身份写死；必须根据用户确认的平台或本轮任务作用域启用。

### 3.3 没有精确匹配

如果没有精确匹配，最多给 2-4 个相近选项，并明确说明“相近，不是精准”。

示例：

```text
没有找到“克苏鲁调查员”精准包。相近素材可以选：
1. library-topic-horror-weird：恐怖灵异与规则怪谈资料包
2. library-topic-mystery-detective：悬疑刑侦推理题材资料包
3. library-design-rules-mechanics：规则机制设定设计包
你要用哪个方向做参考？
```

---

## 4. 推荐分类参考

### 4.1 通用写作

- `webnovel-writing-basic`：网文写作基础包，适合开书、黄金三章、章节结构。
- `webnovel-creative-planning`：创意与立项规划。
- `webnovel-setting-framework`：设定与大纲框架。
- `webnovel-drafting-polish`：正文创作与润色。
- `library-writing-outline-pacing`：大纲结构与节奏设计。
- `library-writing-character-relations`：人物角色与关系设计。
- `library-writing-action-scenes`：场景动作与战斗写作。

### 4.2 去 AI 化 / 润色

- `deslop-basic`：去 AI 味基础规则。
- `library-polish-emotion-sensory`：情绪心理与感官表达。
- `library-polish-language-style`：语言风格与修辞。

### 4.3 题材方向

- 求生 / 末世 / 庇护所：`survival-topic`、`library-topic-apocalypse-survival`
- 玄幻 / 仙侠：`topic-xuanhuan`、`library-topic-xuanhuan-xianxia`
- 规则怪谈 / 恐怖：`topic-rule-horror`、`library-topic-horror-weird`
- 悬疑 / 刑侦 / 推理：`library-topic-mystery-detective`
- 都市 / 现实：`library-topic-urban-realistic`、`topic-shiqing`
- 女频 / 情感 / 狗血：`library-topic-romance-female`、`topic-gouxue-nvwen`
- 知乎短篇 / 短篇反转：`topic-zhihu-short`
- 短剧 / 影视改编：`library-topic-short-drama-media`
- 游戏 / 电竞 / 体育：`library-topic-game-sports`
- 科幻 / 赛博：`library-topic-scifi-cyber`
- 历史 / 古代 / 权谋：`library-topic-history-power`
- 同人 IP：`library-topic-fanfic-ip`
- 西幻 / 奇幻：`library-topic-fantasy-western`
- 多子多福：`library-topic-duoziduofu`

### 4.4 设定设计

- `library-design-worldbuilding`：世界观设定设计。
- `library-design-system-cheat`：系统金手指设定。
- `library-design-rules-mechanics`：规则机制设定。
- `library-design-factions-resources`：组织势力与资源设定。

### 4.5 工作流与工具

- `library-workflow-agent-pipeline`：创作流程 Agent 工具。
- `library-workflow-writing-checklists`：写作工具与检查表。
- `webnovel-analysis-commercial-tools`：数据分析、商业化、拆书、素材工具。

### 4.6 平台/市场参考

- 番茄：适合新手找大众题材、快节奏、强情绪、强钩子、低门槛爽点。
- 起点：适合长篇结构、设定纵深、升级体系、老读者审美和长期追读。
- 知乎短篇：适合短篇反转、情绪拉扯、现实议题和故事感标题。
- 短剧感：适合高密度冲突、强人设反差、连续反转。

用户没有明确平台时，不要默认只搜索起点；至少同时给番茄和起点两个参考方向。

---

## 5. 推荐输出模板

### 5.1 精确匹配

```text
我先给你找到了更匹配的素材包：

1. {pack_id}：{name}
   用途：{为什么适合}
   状态：{已安装/可安装}

是否启用这个知识包？如果未安装，我会先建议通过 MCP 安装并重建 RAG。
```

### 5.2 相近匹配

```text
没有找到完全匹配“{用户方向}”的知识包。相近素材有：

1. {pack_id}：{name}
   更偏：{适用范围}
2. {pack_id}：{name}
   更偏：{适用范围}

这些只是相近参考，不会默认启用。你想选哪个，还是先不用素材包？
```

### 5.3 用户未给方向

```text
开始设计故事前，我先帮你选素材方向。你想找哪类？

1. 题材包：玄幻、求生、规则怪谈、都市、女频、短篇等
2. 写法包：黄金三章、大纲、人物、战斗、节奏
3. 润色包：去 AI 味、语言风格、感官表达
4. 暂不找素材，先用通用写作规则
```

---

## 6. 启用规则

用户确认后再做：

- 已安装：记录为本任务启用知识包，并让 RAG 优先检索，然后恢复原任务。
- 未安装：通过 MCP 安装，再重建 RAG，成功后恢复原任务。
- 用户拒绝：不启用对应知识包，只用通用规则继续。

启用记录建议写入上下文包或任务说明：

```text
本次任务已确认参考知识包：
- {pack_id}：{name}
- 作用域：本轮任务 / 当前章节 / 当前项目
- 匹配级别：精准匹配 / 相近参考
```

如果用户只选择了“看看有哪些”，不要直接启用。

---

## 7. 挂起与恢复协议

素材推荐不是独立任务，而是通用挂起恢复机制的一个使用场景。推荐前必须按 `../rules/subagent-runtime.md` 保存恢复点，用户确认并完成知识包准备后，继续原任务。

### 7.1 恢复点字段

```text
任务恢复点：
- resume_id：{本次挂起任务的临时编号}
- original_request：{用户原始请求}
- target_agent：{规划Agent / 写作Agent / 审稿Agent / 上下文Agent}
- suspended_step：{挂起前正在准备的步骤}
- collected_context：{已经确认的项目、题材、主角、章节目标、限制条件}
- pending_pack_options：{推荐给用户的 pack_id 列表}
- next_action：{知识包确认后要继续执行的动作}
```

### 7.2 成功恢复

```text
知识包已准备好：
- 已确认参考知识包：{pack_id 列表}
- RAG 状态：已重建 / 无需重建

现在恢复刚才的任务：{next_action}
```

恢复后，把“已确认参考知识包”传给目标 Agent，不要重新走素材推荐，也不要重新询问已经确认的信息。

传递给目标 Agent 时必须标注知识作用域和匹配级别。相近参考只允许作为结构、氛围、避坑点参考，不能直接套入题材设定。

### 7.3 失败恢复

如果 MCP 下载、安装或 RAG 重建失败，保留恢复点，不要丢弃原任务。

```text
知识包准备失败，刚才的任务已暂停在：{suspended_step}

1. 重试安装/重建索引
2. 不使用该知识包，恢复原任务并用通用规则继续
3. 暂停任务，稍后再继续
```

用户选择 2 时，也要回到原任务继续，只是“已确认参考知识包”为空。
