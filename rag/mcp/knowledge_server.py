"""
Minimal MCP stdio server for novel-harness knowledge packs.

This intentionally avoids third-party MCP dependencies. It implements the small
JSON-RPC surface needed to expose sync_packs.py as MCP tools.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNC_SCRIPT = PROJECT_ROOT / "rag" / "scripts" / "sync_packs.py"
PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _manifest_arg(arguments: dict[str, Any]) -> list[str]:
    manifest = arguments.get("manifest_url") or os.environ.get("NOVEL_HARNESS_REMOTE_MANIFEST")
    return ["--manifest", str(manifest)] if manifest else []


def _run_sync(args: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _require_pack_id(arguments: dict[str, Any]) -> str:
    pack_id = str(arguments.get("pack_id", "")).strip()
    if not PACK_ID_RE.match(pack_id):
        raise ValueError("pack_id must match ^[a-z0-9][a-z0-9-]*$")
    return pack_id


def list_knowledge_packs(arguments: dict[str, Any]) -> dict[str, Any]:
    include_remote = bool(arguments.get("include_remote", True))
    args = [*_manifest_arg(arguments), "--json", "list"]
    if include_remote:
        args.append("--include-remote")
    return _run_sync(args)


def list_installed_packs(arguments: dict[str, Any]) -> dict[str, Any]:
    return _run_sync(["--json", "installed"])


def install_knowledge_pack(arguments: dict[str, Any]) -> dict[str, Any]:
    pack_id = _require_pack_id(arguments)
    rebuild_index = bool(arguments.get("rebuild_index", True))
    args = [*_manifest_arg(arguments), "install", pack_id]
    if rebuild_index:
        args.append("--rebuild-index")
    return _run_sync(args)


def update_knowledge_pack(arguments: dict[str, Any]) -> dict[str, Any]:
    pack_id = _require_pack_id(arguments)
    rebuild_index = bool(arguments.get("rebuild_index", True))
    args = [*_manifest_arg(arguments), "update", pack_id]
    if rebuild_index:
        args.append("--rebuild-index")
    return _run_sync(args)


def remove_knowledge_pack(arguments: dict[str, Any]) -> dict[str, Any]:
    pack_id = _require_pack_id(arguments)
    rebuild_index = bool(arguments.get("rebuild_index", True))
    args = ["remove", pack_id]
    if rebuild_index:
        args.append("--rebuild-index")
    return _run_sync(args)


def rebuild_rag_index(arguments: dict[str, Any]) -> dict[str, Any]:
    return _run_sync(["rebuild-index"])


TOOLS = {
    "list_knowledge_packs": {
        "description": "List built-in and server-provided knowledge packs.",
        "handler": list_knowledge_packs,
        "inputSchema": {
            "type": "object",
            "properties": {
                "manifest_url": {"type": "string", "description": "Optional server manifest URL. Defaults to the project knowledge-pack market."},
                "include_remote": {"type": "boolean", "default": True},
            },
        },
    },
    "list_installed_packs": {
        "description": "List server-provided knowledge packs installed locally.",
        "handler": list_installed_packs,
        "inputSchema": {"type": "object", "properties": {}},
    },
    "install_knowledge_pack": {
        "description": "Install a knowledge pack into .harness/knowledge/remote/.",
        "handler": install_knowledge_pack,
        "inputSchema": {
            "type": "object",
            "required": ["pack_id"],
            "properties": {
                "pack_id": {"type": "string"},
                "manifest_url": {"type": "string", "description": "Optional server manifest URL. Defaults to the project knowledge-pack market."},
                "rebuild_index": {"type": "boolean", "default": True},
            },
        },
    },
    "update_knowledge_pack": {
        "description": "Update a knowledge pack by reinstalling it.",
        "handler": update_knowledge_pack,
        "inputSchema": {
            "type": "object",
            "required": ["pack_id"],
            "properties": {
                "pack_id": {"type": "string"},
                "manifest_url": {"type": "string", "description": "Optional server manifest URL. Defaults to the project knowledge-pack market."},
                "rebuild_index": {"type": "boolean", "default": True},
            },
        },
    },
    "remove_knowledge_pack": {
        "description": "Remove a locally installed server-provided knowledge pack.",
        "handler": remove_knowledge_pack,
        "inputSchema": {
            "type": "object",
            "required": ["pack_id"],
            "properties": {
                "pack_id": {"type": "string"},
                "rebuild_index": {"type": "boolean", "default": True},
            },
        },
    },
    "rebuild_rag_index": {
        "description": "Rebuild the local RAG index.",
        "handler": rebuild_rag_index,
        "inputSchema": {"type": "object", "properties": {}},
    },
}


def _tool_descriptions() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": spec["description"],
            "inputSchema": spec["inputSchema"],
        }
        for name, spec in TOOLS.items()
    ]


def _success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        params = message.get("params") or {}
        protocol_version = params.get("protocolVersion", "2024-11-05")
        return _success(
            request_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "novel-harness-knowledge", "version": "0.1.0"},
            },
        )

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return _success(request_id, {"tools": _tool_descriptions()})

    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        spec = TOOLS.get(name)
        if not spec:
            return _error(request_id, -32602, f"Unknown tool: {name}")

        try:
            payload = spec["handler"](arguments)
        except Exception as exc:  # MCP tools should report errors as tool results.
            payload = {"exit_code": 1, "stdout": "", "stderr": str(exc)}

        is_error = payload.get("exit_code", 1) != 0
        return _success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": is_error,
            },
        )

    return _error(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            message = json.loads(line)
            response = _handle(message)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
        except Exception as exc:
            response = _error(None, -32603, f"Internal error: {exc}")

        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
