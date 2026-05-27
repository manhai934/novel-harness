# 知识包使用说明

知识包是 novel-harness 的全局参考资料层，用来给 RAG 提供题材、写法、去 AI 化、平台风格等可检索资料。

## 目录

```text
.harness/knowledge/
├── included/  # 随项目自带的知识包
├── packs/     # 知识包 manifest
├── remote/    # 远程下载知识包，本地使用，不上传 Git
└── user/      # 用户私有知识包，默认不索引，不上传 Git
```

## 当前内置包

- `deslop-basic`：去 AI 味基础规则。
- `webnovel-writing-basic`：黄金三章、章节结构、爽点和钩子。
- `survival-topic`：全民求生、庇护所、资源循环、天灾压迫题材。

## 启用前先安装依赖

如果要重建 RAG 索引，必须先给当前正在使用的 Python 安装依赖：

```powershell
python -m pip install -r rag/requirements.txt
```

注意要使用同一个 Python。比如你用下面这个命令安装知识包：

```powershell
python rag/scripts/sync_packs.py --manifest <远程manifest地址> install topic-xuanhuan --rebuild-index
```

那么依赖也要安装到这个 `python` 对应的环境里。否则重建索引时可能会报：

```text
ModuleNotFoundError: No module named 'numpy'
```

## 常用命令

```powershell
python -m pip install -r rag/requirements.txt
python rag/scripts/sync_packs.py list
python rag/scripts/sync_packs.py list --include-remote
python rag/scripts/sync_packs.py installed
python rag/scripts/build_index.py
```

仓库已内置测试版知识包市场地址，默认会读取：

```text
http://47.103.57.247:9000/manifest
```

安装云端知识包：

```powershell
python rag/scripts/sync_packs.py list --include-remote
python rag/scripts/sync_packs.py install topic-xuanhuan --rebuild-index
```

如果你要临时测试其他 manifest，可以继续使用 `--manifest <远程manifest地址>` 覆盖默认市场。

## 版权边界

知识包只放自写规则、拆解总结、授权资料和短句级自写示例。不要放未授权小说正文、平台章节原文或可替代原作阅读的大段摘录。

## RAG 策略

默认索引：

- `.harness/knowledge/included/**/*.md`
- `.harness/knowledge/remote/**/*.md`
- `.harness/skills/**/references/*.md`
- `.harness/skills/**/rules/*.md`
- `.harness/project-templates/*.md`

默认不索引：

- `.harness/knowledge/user/**`
- `projects/**`
- `rag/data/**`
