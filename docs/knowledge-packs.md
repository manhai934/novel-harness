# 知识包使用说明

知识包是 novel-harness 的全局参考资料层，用来给 RAG 提供题材、写法、去 AI 化、平台风格等可检索资料。

## 目录

```text
.harness/knowledge/
├── builtin/   # 随仓库发布的内置知识包
├── packs/     # 知识包 manifest
├── remote/    # 远程下载知识包，本地使用，不上传 Git
└── user/      # 用户私有知识包，默认不索引，不上传 Git
```

## 当前内置包

- `deslop-basic`：去 AI 味基础规则。
- `webnovel-writing-basic`：黄金三章、章节结构、爽点和钩子。
- `survival-topic`：全民求生、庇护所、资源循环、天灾压迫题材。

## 常用命令

```powershell
python rag/scripts/sync_packs.py list
python rag/scripts/sync_packs.py installed
python rag/scripts/build_index.py
```

远程包能力已经预留：

```powershell
python rag/scripts/sync_packs.py --manifest .harness/knowledge/packs/remote.example.json list --include-remote
python rag/scripts/sync_packs.py --manifest <远程manifest地址> install survival-topic --rebuild-index
```

## 版权边界

知识包只放自写规则、拆解总结、授权资料和短句级自写示例。不要放未授权小说正文、平台章节原文或可替代原作阅读的大段摘录。

## RAG 策略

默认索引：

- `.harness/knowledge/builtin/**/*.md`
- `.harness/knowledge/remote/**/*.md`
- `.harness/skills/**/references/*.md`
- `.harness/skills/**/rules/*.md`
- `.harness/project-templates/*.md`

默认不索引：

- `.harness/knowledge/user/**`
- `projects/**`
- `rag/data/**`

