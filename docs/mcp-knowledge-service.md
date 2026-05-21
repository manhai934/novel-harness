# MCP 知识包服务设计

novel-harness 的 MCP 知识包服务目标是：让 AI 工具可以按需列出、安装、更新知识包，并在安装后触发本地 RAG 重建。

当前仓库先落地本地执行层：`rag/scripts/sync_packs.py`。后续 MCP 服务只封装这些能力，不重复实现下载和校验逻辑。

## 目标工具

```text
list_knowledge_packs
install_knowledge_pack
update_knowledge_pack
remove_knowledge_pack
list_installed_packs
rebuild_rag_index
```

## 对应本地命令

| MCP tool | 本地命令 |
|---|---|
| `list_knowledge_packs` | `python rag/scripts/sync_packs.py list --include-remote` |
| `list_installed_packs` | `python rag/scripts/sync_packs.py installed` |
| `install_knowledge_pack` | `python rag/scripts/sync_packs.py install <pack_id> --rebuild-index` |
| `update_knowledge_pack` | `python rag/scripts/sync_packs.py update <pack_id> --rebuild-index` |
| `remove_knowledge_pack` | `python rag/scripts/sync_packs.py remove <pack_id> --rebuild-index` |
| `rebuild_rag_index` | `python rag/scripts/sync_packs.py rebuild-index` |

## 安全规则

- 只允许安装到 `.harness/knowledge/remote/{pack_id}/`。
- zip 解压必须阻止 path traversal。
- 只允许 `.md`、`.txt`、`.json`、`.yaml`、`.yml` 文件。
- 支持 `sha256` checksum 校验。
- 不执行远程脚本。
- 不覆盖 `.harness/agents/`、`.harness/skills/`、`.harness/project-templates/` 等核心目录。

## Agent 协作规则

规划、写作、审稿、上下文 Agent 发现参考资料不足时，不直接编造题材规则。它们只向总编 Agent 报告缺口。

总编 Agent 负责向用户确认：

```text
当前任务缺少 {题材/风格/审稿} 参考包。
建议通过 MCP 安装 {pack_id}，并重建 RAG 索引。
是否继续？
```

用户确认后，再调用 MCP 安装并重新委派原任务。
