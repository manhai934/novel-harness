# knowledge 知识包层

`.harness/knowledge/` 是 novel-harness 的统一知识包目录，用来承载可被 RAG 检索的题材参考、去 AI 化规则、写作方法、平台风格和后续 MCP 下载的扩展资料。

它和 skill 内部的 `references/` 不同：

- `skills/**/references/`：某个 skill 自带的局部引用资料。
- `knowledge/`：贯穿整个项目、可按包安装和索引的全局知识库。

## 目录边界

```text
.harness/knowledge/
├── included/  # 随项目自带的公开知识包
├── packs/     # 知识包 manifest、版本和来源说明
├── remote/    # MCP 从服务器下载的知识包，本地目录，不上传 Git
├── pack-recommendation.md  # 写作前素材/知识包推荐规则
└── user/      # 用户私有知识包，本地目录，不上传 Git
```

## 写作前推荐规则

开书、设计故事背景、大纲、章节写作或需要专项审稿前，先按 `pack-recommendation.md` 推荐可选知识包。

核心边界：

- 只给选项，不替用户决定启用哪个题材包。
- 用户确认前，不安装、不启用、不强制套用任何知识包。
- 没有精准匹配时，只能给相近候选，并明确说明“相近，不是精准”。
- 用户选择暂不使用素材包时，继续使用通用写作规则。
- 知识包推荐会临时挂起原任务；安装和 RAG 重建完成后，恢复到挂起前的下一步继续执行。

## 默认 RAG 策略

默认索引：

```text
.harness/knowledge/included/
.harness/knowledge/remote/
.harness/skills/
.harness/project-templates/
docs/
```

默认不索引：

```text
projects/
rag/data/
.harness/knowledge/user/
```

`user/` 用于未来私有资料扩展，只有用户明确开启时才进入索引。

## 管理命令

```powershell
python rag/scripts/sync_packs.py list
python rag/scripts/sync_packs.py installed
python rag/scripts/sync_packs.py --manifest <manifest路径或URL> install <pack_id> --rebuild-index
```

`sync_packs.py` 是后续 MCP 知识包服务的本地执行层。MCP 只负责把 AI 工具调用转成这些本地动作。

## 知识包分类

- `deslop/`：去 AI 化、人性化、句式、语感、正则规则。
- `topics/`：题材包，例如全民求生、游戏数据化、电竞、修仙、都市、悬疑。
- `writing/`：写作技法，例如黄金三章、爽点、钩子、节奏、伏笔。
- `market/`：平台风格，例如番茄、起点、知乎短篇等。
- `cases/`：自写案例、修改前后对照、问题复盘。

## 版权边界

知识包只能放自写规则、拆解总结、授权资料和短句级自写示例。不要放未授权小说正文、平台章节原文或可替代原作阅读的大段摘录。
