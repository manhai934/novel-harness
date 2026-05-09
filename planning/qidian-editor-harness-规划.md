# qidian-editor · Harness Engineering 进化规划

> 基于 Anthropic Harness Engineering 方法论 × 网文创作领域映射
> 核心参考：Effective Harnesses for Long-Running Agents / OpenAI Codex Harness Practice
> 核心理念：**写小说不是一个 skill，是一个 Agent 系统。**
> 历史说明：本文档记录早期从 `skills/qidian-editor` 演进到 Harness 的方案。当前实现已统一到 `harness/qidian-editor`，旧路径只作历史语境参考。

---

## 一、当前阶段诊断：从 Prompt → Context → Harness

文章说的三次范式跃迁，映射到我们当前的状态：

```
Prompt Engineering（2022-2024）    
  └─ 我们已超越此阶段
  └─ 不再靠"写好prompt"解决问题

Context Engineering（2025）
  └─ 我们在此阶段
  └─ qidian-editor（主模块）+ game-datafied + human-linguistics（子模块）
  └─ 分层加载，按需获取——这正是 Context Engineering 的做法
  └─ reference/ 知识库——让 Agent 能查询

Harness Engineering（2026） ← 我们要去的地方
  └─ 多会话、多Agent、多执行阶段的完整系统架构
  └─ Constraints + Feedback Loops + Workflow Orchestration + Continuous Improvement
```

**结论**：你已经建好了 Context Engineering 的基础（skill 分层 + 知识库），现在要升级到 Harness Engineering——把"静态规则"变成"动态系统"。

---

## 二、Harness 四支柱 × 网文创作映射

### 支柱一：上下文架构（Context Architecture）

**原文经验**：Agent 应当恰好获得当前任务所需的上下文——不多不少。

**网文映射**：


| 层级          | 加载时机       | 内容                   | 对应现有文件                            |
| ----------- | ---------- | -------------------- | --------------------------------- |
| **L1 常驻层**  | 始终加载       | 总编Agent定义、核心Rules    | qidian-editor/SKILL.md            |
| **L2 阶段触发** | 进入对应阶段时    | 对应 Skill（审稿/语感/设定检查） | game-datafied / human-linguistics |
| **L3 按需查询** | Agent 主动查阅 | 世界观、设定、角色档案          | 设定/*.md                           |


**关键约束**：L1 总量控制——Agent 定义文件不超过 400 行，遵循"Index & Map"原则而非百科全书。

---

### 支柱二：Agent 专业化（Agent Specialization）

**原文经验**：拥有受限工具集的专业 Agent，优于拥有全部权限的通用 Agent。

**网文映射——角色分工**：

```
                   总编 Agent "林远"
           （Application Owner · 流程编排中枢）
              ┌──────────────────────┐
              │ 职责：任务分派 · 质量   │
              │ 裁定 · 知识调度 · 流程   │
              │ 控制                    │
              └──────────────────────┘
                      │
        ┌─────────────┼──────────────┐
        │             │              │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │审稿Agent │  │语感Agent │  │设定Agent │
   │(当前已   │  │(当前已   │  │(待创建)  │
   │ 有雏形)  │  │ 有雏形)  │  │          │
   └─────────┘  └─────────┘  └─────────┘
                       │
                  ┌────▼────┐  ┌────▼────┐
                  │写作Agent │  │分析Agent │
                  │(未来)   │  │(未来)   │
                  └─────────┘  └─────────┘
```

**核心原则**：将做事的 Agent 和评判的 Agent 分开——审稿 Agent 和写作 Agent 永远不是同一个。

### 创作灵感 Agent——新增能力维度

当前体系只有"审"，缺少"创"。参考起点编辑给作者提剧情建议、番茄的灵感创作功能，需要增加一个**创作灵感 Agent**：

```
                     总编 Agent
           （流程编排中枢 · 任务分派）
                      │
        ┌─────────────┼──────────────┐
        │             │              │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │审稿Agent │  │创作Agent │  │分析Agent │
   │(批判)   │  │(发散)   │  │(洞察)   │
   │         │  │         │  │         │
   │ ·通用审稿│  │·剧情构思│  │·市场趋势│
   │ ·语感审查│  │·设定扩展│  │·读者偏好│
   │ ·设定检查│  │·角色发展│  │·题材分析│
   │ ·情节逻辑│  │·反转设计│  │          │
   └─────────┘  └─────────┘  └─────────┘
```

**创作 Agent 的三个能力模块：**

**模块一：剧情构思（Plot Ideation）**

- 基于当前故事状态，生成多条可能的剧情走向
- 提供"如果……会怎样"的假设推演
- 对比不同选择的故事张力、节奏影响

```
示例交互：
  用户：林北刚拿到双倍奖励，接下来怎么写？
  创作Agent：
    方向A：利用优势快速升级 → 爽点密集，但容易变无敌流
    方向B：低调发育，在关键副本一鸣惊人 → 蓄力爆发型爽点
    方向C：双倍奖励被发现，卷入阵营冲突 → 人际关系线展开
  
  每个方向附带：所需篇幅、冲突类型、风险提示
```

**模块二：设定扩展（World Expansion）**

- 基于现有世界观，建议可扩展的方向
- 设计新副本、新怪物、新装备
- 确保新设定与已有数值体系兼容

```
示例交互：
  用户：想加一个新副本，但又不想破坏数值平衡
  创作Agent：
    推荐：镜像副本（怪物复制玩家属性）
    原因：不依赖固定数值，任何等级都能打
    产出：怪物设计 + 掉落表 + 难度曲线
```

**模块三：反转/钩子设计（Twist & Hook Design）**

- 分析已埋下的伏笔，建议回收时机
- 设计章节结尾的悬念
- 制造让读者"意想不到但合理"的反转

---

### 支柱三：持久化记忆（Persistent Memory）

**原文经验**：进度持久化在文件系统上，而非上下文窗口中。

**网文映射**：

```
小说项目/
├── changes/                 ← 变更管理（每个章节的完整编辑记录）
│   ├── 第3章-v1-20260506/
│   │   ├── summary.md       ← 全流程追溯摘要
│   │   ├── review/          ← 审稿记录
│   │   └── revision/        ← 修改记录
│   └── 第4章-v1-20260507/
│
├── wiki/                    ← 知识库（当前设定/ 目录）
│   ├── 世界观.md
│   ├── 角色档案/
│   └── 数值体系.md
│
└── .harness/                ← Harness 系统文件
    ├── agents/              ← Agent 定义
    │   └── chief-editor.md  ← 总编 Agent 定义
    ├── rules/               ← 规则体系
    │   ├── 通用审稿规则.md
    │   └── 语言语感规范.md
    ├── skills/              ← 技能体系
    │   ├── general-review/  ← 通用审稿 skill
    │   ├── language-audit/  ← 语感审查 skill
    │   ├── setting-check/   ← 设定一致性 skill
    │   ├── plot-review/     ← 情节审查 skill（待建）
    │   └── plot-ideation/   ← 剧情构思 skill（新增）
    └── cases/               ← 错误案例库
        └── 语病案例/
```

---

### 支柱四：结构化执行（Structured Execution）

**原文经验**：永远不让 Agent 在未经审查和批准书面计划之前写代码。

**网文映射——创作管线**：

```
写一章的标准流程（10 Stage Pipeline）：

Stage 1: 大纲规划
  → 确定章节目标和核心冲突
  → 产出：chapter_outline.md

Stage 2: 大纲评审 ← 总编确认点
  → 审稿Agent评审大纲合理性和爽点分布
  → 产出：review/outline_review.md

Stage 3: 初稿写作
  → 写作Agent按大纲生成初稿
  → 加载：情节模板 + 战斗描写规范
  → 产出：draft_v1.md

Stage 4: 语言润色
  → 语感Agent排查AI式语病
  → 加载：human-linguistics 全量规则
  → 产出：polished_draft.md

Stage 5: 设定一致性检查
  → 设定Agent对比正文 vs 设定文件
  → 检查：怪物名/技能名/数值体系一致性
  → 产出：consistency_report.md

Stage 6: 情节评审 ← 总编确认点
  → 审稿Agent检查逻辑漏洞和角色行为合理性
  → 产出：review/plot_review.md

Stage 7: 修改循环
  → 根据评审意见修改
  → 最多2轮，超出升级到人工

Stage 8: 终审 ← 人工确认（必设Human-in-the-Loop）
  → 总编Agent汇总所有评审报告
  → 人工终审

Stage 9: 发布准备
  → 检查钩子、章尾悬念
  → 产出：publish_ready.md

Stage 10: 归档
  → 更新 changes/ 目录
  → 总结本学到的规则更新
```

### 创作灵感管线（Creative Pipeline）

与"审"管线并行，处理"创"的需求：

```
灵感请求流程：

Phase 1: 理解上下文
  → 创作Agent 读取当前故事状态（最新章节 + 角色状态 + 可用伏笔）
  → 加载：wiki/世界观 + 角色档案 + 已有章节摘要
  → 产出：context_summary.md

Phase 2: 发散构思
  → 基于上下文生成 3-5 个剧情方向
  → 每个方向含：核心冲突、爽点类型、预期篇幅
  → 产出：plot_branches.md

Phase 3: 深化推演
  → 用户选择方向后，创作Agent 深入推演
  → 细化情节节点、角色反应、设定兼容性
  → 产出：detailed_outline.md

Phase 4: 可行性评估 ← 审稿Agent 介入
  → 审稿Agent 检查设定一致性、逻辑合理性
  → 标记风险点（如"这个方向会破坏数值平衡"）
  → 产出：feasibility_report.md

Phase 5: 人工决策 ← Human-in-the-Loop
  → 用户结合创作方案 + 可行性评估做最终选择
```

**关键设计：创作 Agent 只管"出点子"，审稿 Agent 负责"挑毛病"。**
这正好实践文章说的"将做事的 Agent 和评判的 Agent 分开"。

---

## 三、四要素架构：从碎片到系统

### 当前状态 vs 目标状态


| 要素          | 当前（碎片化）          | 目标（系统化）                                    |
| ----------- | ---------------- | ------------------------------------------ |
| **Rules**   | 散落在 SKILL.md 各章节 | `.harness/rules/` 结构化文件                    |
| **Skills**  | 主模块 + 2个子模块      | `.harness/skills/` 每个 skill 独立目录含 SOP + 模板 |
| **Wiki**    | `设定/` 下的 md 文件   | `.harness/wiki/` 按题材/角色/世界观分类              |
| **Changes** | ❌ 无              | `.harness/changes/` 每章完整变更记录               |


### 1. Rules 体系（规则体系）

不随需求变化的稳定约束（Invariant Constraints）：

```
.harness/rules/
├── 工程结构.md          ← 目录规范、文件命名、版本管理
├── 语言语感规范.md       ← human-linguistics 核心规则（迁移至此）
├── 游戏题材规范.md       ← game-datafied 核心规则（迁移至此）
└── 通用审稿规范.md       ← 上架前审查清单等
```

每条规则遵循"先讲原则，再讲规则，最后给示例"的结构，且必须有**可程序化验证**的检查点（不能只说"要自然"，要说"连续5句没有语气词 → 违规"）。

### 2. Skills 体系（技能体系）

每个 Skill 是一份结构化的 SOP，告诉 Agent "应该怎么做"：

```
.harness/skills/
├── general-review/       ← 通用审稿 skill（已有）
│   ├── SKILL.md          ← SOP：怎么审稿
│   └── templates/        ← 评审报告模板
│       └── review_report_template.md
├── language-audit/       ← 语感审查 skill（已有 human-linguistics）
│   ├── SKILL.md
│   ├── rules/            ← 13类语病结构化规则
│   └── templates/
├── setting-check/        ← 设定一致性 skill（待创建）
│   ├── SKILL.md
│   └── rules/
├── plot-review/          ← 情节/逻辑审查 skill（待创建）
│   ├── SKILL.md
│   └── rules/
└── chapter-write/        ← 章节写作 skill（未来）
    ├── SKILL.md
    └── templates/
└── plot-ideation/          ← 剧情构思 skill（新增）
    ├── SKILL.md            ← SOP：怎么构思剧情
    ├── rules/
    │   ├── 爽点节奏参考.md
    │   └── 反转设计模式.md
    └── templates/
        ├── plot_branches_template.md
        └── twist_design_template.md
```

每个 Skill 的 SOP 结构：

1. **触发条件**：什么时候加载这个 Skill
2. **执行流程**：分步骤的标准化流程
3. **产出物模板**：必须生成的产物及其格式
4. **质量门禁**：什么算"通过"（可程序化验证）
5. **回退路径**：不通过怎么办

### 3. Wiki 知识库

Agent 理解业务上下文的素材（Domain Context）：

```
.harness/wiki/
├── 世界观/               ← 当前 设定/ 的内容
├── 角色档案/             ← 角色性格、背景、关系
├── 数值体系/             ← 等级、属性、伤害公式
├── 战斗规则/             ← game-datafied 战斗逻辑
└── 语言参考/             ← human-linguistics reference/
```

### 4. Changes 变更管理

每章完整的追溯链：

```
.harness/changes/
└── 第{章节}-v{版本}-{日期}/
    ├── summary.md                    ← 全流程追溯摘要（Single Source of Truth）
    ├── outline/
    │   ├── chapter_outline.md
    │   └── review/                   ← 大纲评审记录
    ├── draft/
    │   ├── v1.md
    │   └── review/                   ← 初稿评审记录
    ├── polish/
    │   ├── polished_v1.md
    │   └── language_report.md
    ├── consistency/
    │   └── consistency_report.md
    └── publish/
        └── publish_checklist.md
```

---

## 四、分阶段进化路线

### Phase 1：Agent 化包装（1-2 周）

**目标**：不改变现有内容，加一层 Agent 角色和任务分类

**具体任务**：

1. **定义总编 Agent**
  - 在 qidian-editor 主模块开头增加 Agent 角色定义模块
  - 角色：起点金牌编辑"林远"，10年经验
  - 核心职责：需求理解、任务拆解、质量把关、知识库维护
  - 七项职责（参考文章的七项核心职责设计）
2. **任务分类逻辑**
  - 用户请求 → Agent 自动判断任务类型
  - 类型一：全面审稿（调通用+题材+语感）
  - 类型二：专项语感检查（调 human-linguistics）
  - 类型三：设定一致性检查（调设定文件）
  - 类型四：写作辅助（未来）
3. **建立结构骨架**
  ```
   harness/qidian-editor/
   ├── agents/
   │   └── chief-editor.md      ← Agent 定义
   ├── rules/                    ← 从主模块抽离
   ├── skills/                   ← 已有
   ├── cases/                    ← 案例库（空）
   └── changes/                  ← 变更记录（空）
  ```
4. **更新主模块 SKILL.md**
  - 保留现有内容作为 Rules 素材
  - 增加 Agent 角色定义和调度逻辑

**关键约束**：Agent 定义文件控制在 400 行以内，作为 Index & Map，不做百科全书。

---

### Phase 2：Knowledge Base 结构化（2-3 周）

**目标**：把"长文档"变成"可查询的知识库"

1. **human-linguistics 结构化拆解**
  - 13 类语病 → 13 个独立规则文件
  - 8 张对照表 → 8 个可查询的对照词典
  - 10 则案例 → 格式化的案例条目
2. **创建 rules/ 目录**
  - 从主模块抽离稳定规则
  - 每条规则附可验证的检查条件
3. **创建 skill 独立目录**
  - 当前子模块升级为独立 skill 目录
  - 每个 skill 有完整的 SOP + 模板 + 质量门禁
4. **创建 cases/ 目录**
  - 从 human-linguistics 的实战对照库迁移
  - 新增"编辑器发现的错误"案例积累机制

---

### Phase 3：多 Agent 管线（3-4 周）

**目标**：从"一个 Agent 调多个 skill"到"多个专业 Agent 各司其职"

1. **创建专业 Agent 定义**
  - 审稿 Agent：focus 通用审稿清单
  - 语感 Agent：focus human-linguistics
  - 设定 Agent：focus 世界观/数值/怪物一致性
  - 各 Agent 有受限的工具集（Constrainted Toolset）
2. **设计 5-Stage 审稿管线（先简化版）**
  ```
   Stage 1: 语感审查 → 语感Agent (human-linguistics)
   Stage 2: 设定检查 → 设定Agent (设定文件对照)
   Stage 3: 逻辑审查 → 审稿Agent (情节/角色合理性)
   Stage 4: 总编汇总 → 总编Agent (合并报告)
   Stage 5: 人工确认 → Human-in-the-Loop
  ```
3. **实现 Agent-to-Agent Review**
  - 审稿Agent 审查语感Agent 的工作成果
  - 语感Agent 审查设定Agent 的发现
  - 交叉验证，防止单一Agent 的盲区

---

### Phase 4：自进化系统（持续）

**目标**：每次审稿都是学习机会，系统自动完善

1. **错误案例自动积累**
  - 每次用户修正 → 记录到 cases/
  - 同类错误出现 3 次 → 自动升级到"高频红线"
2. **知识库自动扩展**
  - Agent 发现规则无法覆盖的新语病 → 建议追加规则
  - 用户确认后 → 自动更新知识库
3. **质量度量**
  - 跟踪 AI 代码率（类比文章中的 25% → 90%）
  - 跟踪语病检出率和误报率
  - 定期生成质量报告

---

## 五、当前可立即启动的事项

就算不全部重做，以下几个改动可以马上做：

### 5.1 在 qidian-editor SKILL.md 开头增加 Agent 定义

```markdown
## ★ Agent 角色定义

你是起点中文网的总编 Agent"林远"。

**身份背景**：
- 起点中文网金牌编辑，从业 10 年，审过 500+ 本书
- 精通游戏降临、玄幻修仙、都市现实等多题材
- 对 AI 式语感有极高的敏感度

**核心职责**：
1. 需求理解与澄清——准确理解作者的审稿/写作需求
2. 任务拆解——将复杂需求拆分为可执行的子任务
3. 能力调度——根据任务类型调用对应的审查 skill
4. 质量把关——确保产出符合结构化约束和业务语义
5. 知识管理——维护知识库和案例库

**工作原则**：
- 先理解，再行动——不在未理解需求前直接动手
- 有证据地交付——每条审稿意见必须有规则依据
- 持续积累——发现新语病就追加到知识库
```

### 5.2 建立 cases/ 目录

把 human-linguistics 的 10 则实战案例独立出来，加上发现路径和修复方案。

### 5.3 将当前 skill 重命名为"总编Agent调度下的专业能力"

不是"拆掉"当前结构，而是在它上面加一层调度层。

---

## 六、与当前已有内容的映射


| 已有内容                       | Harness 体系中的位置                    | 下一步                |
| -------------------------- | --------------------------------- | ------------------ |
| qidian-editor/SKILL.md     | Agent 定义 + Rules 素材               | 拆分 Agent 定义和 Rules |
| game-datafied/SKILL.md     | Skills/game-review                | 增加 SOP 模板和 Gate    |
| human-linguistics/SKILL.md | Skills/language-audit + Wiki/语言参考 | 结构化拆为独立规则文件        |
| reference/                 | Wiki 原始素材                         | 保持 + 增加索引          |
| 实战对照库 10 则案例               | cases/ 雏形                         | 独立目录 + 扩展          |
| 设定/*.md                    | Wiki                              | 增加索引方便 Agent 查询    |


---

## 七、和阅文 Claw 的对比


| 维度       | 阅文 WriteClaw   | qidian-editor Harness         |
| -------- | -------------- | ----------------------------- |
| 定位       | 作家的 AI 助理      | 编辑的 AI 审稿系统                   |
| 能力       | 热梗收集/三江鉴赏/情节分析 | 语病审查/设定一致性/情节逻辑               |
| Agent 角色 | 编辑/助手/书童/运营官   | 总编/审稿官/语感官/设定官                |
| 差异化      | 面向作家的写作辅助      | 面向编辑的质量控制 + Agent 管线          |
| 优势       | 阅文生态数据 + 百万作品库 | 深度定制的审稿规则 + human-linguistics |


**结论**：Claw 和 qidian-editor Harness 不是竞争关系，而是互补关系。Claw 做"写"，Harness 做"审"。两者结合才是一个完整的创作系统。

---

## 八、成功标准


| 指标     | 当前             | Phase1 目标       | Phase3 目标       |
| ------ | -------------- | --------------- | --------------- |
| 语病检出率  | ~60%（人工判断）     | ~75%            | >90%            |
| 误报率    | —              | <20%            | <10%            |
| 审稿自动化率 | 30%（手动调 skill） | 50%（Agent 自动分类） | 80%（多 Agent 管线） |
| 案例库规模  | 10 则           | 30 则            | 100+ 则          |
| 规则覆盖率  | 13 类语病         | 20 类            | 30+ 类           |


---

> **一句话总结**：你现在已经建好了 Context Engineering 的基础（skill 分层 + 知识库），下一步是升级到 Harness Engineering——加一个总编 Agent 来调度、让专业 Agent 分工、用结构化流程控制质量、让系统从错误中学习。
>
> 这不是重建，而是在你已有的地基上加一层"智能调度层"。

