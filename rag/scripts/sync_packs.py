"""
知识包同步辅助脚本。

该脚本是未来 MCP 服务可以直接封装的本地执行层，
负责管理 .harness/knowledge/remote/ 下的远程知识包。
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urljoin

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKS_DIR = PROJECT_ROOT / ".harness" / "knowledge" / "packs"
REMOTE_DIR = PROJECT_ROOT / ".harness" / "knowledge" / "remote"
BUILTIN_MANIFEST = PACKS_DIR / "builtin.manifest.json"
DEFAULT_REMOTE_MANIFEST = PACKS_DIR / "remote.example.json"

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}


def _load_json(path_or_url):
    source = str(path_or_url)
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    path = Path(source)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return json.loads(path.read_text(encoding="utf-8"))


def _load_builtin_manifest():
    if not BUILTIN_MANIFEST.exists():
        return {"packs": []}
    return _load_json(BUILTIN_MANIFEST)


def _load_remote_manifest(path_or_url=None):
    manifest_source = path_or_url or DEFAULT_REMOTE_MANIFEST
    return _load_json(manifest_source)


def _installed_packs():
    if not REMOTE_DIR.exists():
        return []

    packs = []
    for child in sorted(REMOTE_DIR.iterdir()):
        if not child.is_dir():
            continue

        pack_json = child / "pack.json"
        if pack_json.exists():
            try:
                data = json.loads(pack_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {"id": child.name, "status": "invalid-manifest"}
        else:
            data = {"id": child.name, "status": "installed"}

        data.setdefault("path", str(child.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        packs.append(data)
    return packs


def list_packs(args):
    builtin = _load_builtin_manifest().get("packs", [])
    remote = _load_remote_manifest(args.manifest).get("packs", []) if args.include_remote else []
    installed_ids = {pack.get("id") for pack in _installed_packs()}

    rows = []
    for pack in builtin:
        rows.append({
            "id": pack.get("id"),
            "name": pack.get("name"),
            "version": pack.get("version"),
            "category": pack.get("category"),
            "source": "builtin",
            "installed": True,
        })

    for pack in remote:
        rows.append({
            "id": pack.get("id"),
            "name": pack.get("name"),
            "version": pack.get("version"),
            "category": pack.get("category"),
            "source": "remote",
            "installed": pack.get("id") in installed_ids,
        })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    for row in rows:
        marker = "已安装" if row["installed"] else "可安装"
        print(f"{row['id']} [{row['source']}/{marker}] {row.get('name', '')} v{row.get('version', '')}")


def list_installed(args):
    packs = _installed_packs()
    if args.json:
        print(json.dumps(packs, ensure_ascii=False, indent=2))
        return

    if not packs:
        print("尚未安装远程知识包。")
        return

    for pack in packs:
        print(f"{pack.get('id')} {pack.get('version', '')} - {pack.get('path', '')}")


def _find_remote_pack(manifest, pack_id):
    for pack in manifest.get("packs", []):
        if pack.get("id") == pack_id:
            return pack
        raise SystemExit(f"远程 manifest 中找不到知识包: {pack_id}")


def _download(url, dest):
    with urllib.request.urlopen(url, timeout=60) as response:
        dest.write_bytes(response.read())


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_checksum(path, checksum):
    if not checksum or checksum == "sha256:REPLACE_WITH_REAL_CHECKSUM":
        return

    algorithm, _, expected = checksum.partition(":")
    if algorithm.lower() != "sha256" or not expected:
        raise SystemExit(f"不支持的 checksum 格式: {checksum}")

    actual = _sha256(path)
    if actual.lower() != expected.lower():
        raise SystemExit(f"checksum 不匹配: 期望 {expected}, 实际 {actual}")


def _safe_extract_zip(zip_path, target_dir):
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.endswith("/"):
                continue

            dest = (target_dir / name).resolve()
            if target_dir.resolve() not in dest.parents:
                raise SystemExit(f"已阻止不安全的 zip 路径: {info.filename}")

            if dest.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise SystemExit(f"已阻止不支持的文件类型: {info.filename}")

        archive.extractall(target_dir)


def install_pack(args):
    manifest = _load_remote_manifest(args.manifest)
    pack = _find_remote_pack(manifest, args.pack_id)
    base_url = manifest.get("base_url", "")
    archive_url = pack.get("url", "")
    if not archive_url:
        raise SystemExit(f"知识包缺少 url: {args.pack_id}")

    if not archive_url.startswith(("http://", "https://")):
        archive_url = urljoin(base_url.rstrip("/") + "/", archive_url)

    REMOTE_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = REMOTE_DIR / args.pack_id

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        archive_path = tmp_dir / f"{args.pack_id}.zip"
        unpack_dir = tmp_dir / "unpack"
        unpack_dir.mkdir()

        print(f"正在下载 {args.pack_id}: {archive_url}")
        _download(archive_url, archive_path)
        _verify_checksum(archive_path, pack.get("checksum"))
        _safe_extract_zip(archive_path, unpack_dir)

        pack_json = unpack_dir / "pack.json"
        if not pack_json.exists():
            pack_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(unpack_dir), str(target_dir))

    print(f"已安装 {args.pack_id} -> {target_dir.relative_to(PROJECT_ROOT)}")
    if args.rebuild_index:
        rebuild_index(args)


def remove_pack(args):
    target_dir = REMOTE_DIR / args.pack_id
    if not target_dir.exists():
        print(f"知识包尚未安装: {args.pack_id}")
        return
    shutil.rmtree(target_dir)
    print(f"已移除 {args.pack_id}")
    if args.rebuild_index:
        rebuild_index(args)


def rebuild_index(_args):
    script = PROJECT_ROOT / "rag" / "scripts" / "build_index.py"
    print("正在重建 RAG 索引...")
    subprocess.run([sys.executable, str(script)], cwd=PROJECT_ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="同步 novel-harness 知识包")
    parser.add_argument("--manifest", help="远程 manifest 路径或 URL")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出内置和远程知识包")
    list_parser.add_argument("--include-remote", action="store_true", help="包含远程 manifest 中的知识包")
    list_parser.set_defaults(func=list_packs)

    installed_parser = subparsers.add_parser("installed", help="列出已安装的远程知识包")
    installed_parser.set_defaults(func=list_installed)

    install_parser = subparsers.add_parser("install", help="安装远程知识包")
    install_parser.add_argument("pack_id")
    install_parser.add_argument("--rebuild-index", action="store_true")
    install_parser.set_defaults(func=install_pack)

    update_parser = subparsers.add_parser("update", help="更新远程知识包")
    update_parser.add_argument("pack_id")
    update_parser.add_argument("--rebuild-index", action="store_true")
    update_parser.set_defaults(func=install_pack)

    remove_parser = subparsers.add_parser("remove", help="移除已安装的远程知识包")
    remove_parser.add_argument("pack_id")
    remove_parser.add_argument("--rebuild-index", action="store_true")
    remove_parser.set_defaults(func=remove_pack)

    rebuild_parser = subparsers.add_parser("rebuild-index", help="重建本地 RAG 索引")
    rebuild_parser.set_defaults(func=rebuild_index)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
