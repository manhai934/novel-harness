# .harness — L0 项目上下文层

> 本目录是 novel-harness Harness 工程体系的 L0 层。
> 作用：告诉 Agent "当前在写哪本书"，以及这本书的创作约束是什么。

---

## 层级定位

```
L0（项目上下文）← .harness/
   ├── 项目选择：当前在写哪本小说
   ├── 世界观注入：加载对应的 projects/ 目录
   └── 创作约束：本项目的底线规则

L1（常驻层）← SKILL.md
   └── Agent 定义 + 启动流程 + 任务分类 + 通用审稿规则

L2（阶段触发）← game-datafied / human-linguistics / plot-review …
   └── 各子模块按需加载

L3（按需查询）← cases/ + projects/
   └── 案例库 / 小说项目设定 / 角色档案 / 数值体系
```

---

## 使用方式

每次开始写作或审稿时：
1. Agent 读取 `current-project.md`，确认当前项目
2. 如果没有记录或用户想换项目 → 引导用户设置
3. 加载 `projects/` 下对应项目模板中的创作约束
4. 注入世界观设定 → 进入 L1 审稿流程
