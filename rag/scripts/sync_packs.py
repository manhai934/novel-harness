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
import urllib.error
import zipfile
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKS_DIR = PROJECT_ROOT / ".harness" / "knowledge" / "packs"
REMOTE_DIR = PROJECT_ROOT / ".harness" / "knowledge" / "remote"
INCLUDED_MANIFEST = PACKS_DIR / "included.manifest.json"
DEFAULT_REMOTE_MANIFEST = "http://47.103.57.247:9000/manifest"

ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml"}


def _load_json(path_or_url):
    source = str(path_or_url)
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    path = Path(source)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_included_manifest():
    if not INCLUDED_MANIFEST.exists():
        return {"packs": []}
    return _load_json(INCLUDED_MANIFEST)


def _with_type_query(path_or_url, pack_type):
    if not pack_type:
        return path_or_url

    source = str(path_or_url)
    if not source.startswith(("http://", "https://")):
        return path_or_url

    parsed = urlparse(source)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["type"] = pack_type
    return urlunparse(parsed._replace(query=urlencode(query)))


def _remote_base_url(path_or_url):
    source = str(path_or_url)
    parsed = urlparse(source)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urljoin(source, ".")


def _normalize_types_payload(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("types", [])
    return []


def _normalize_packs_payload(payload, base_url, pack_type, types):
    if isinstance(payload, list):
        return {
            "base_url": base_url,
            "types": types,
            "selected_type": pack_type,
            "packs": payload,
            "pack_count": len(payload),
        }

    if isinstance(payload, dict):
        result = dict(payload)
        result.setdefault("base_url", base_url)
        result.setdefault("types", types)
        result.setdefault("selected_type", pack_type)
        result["pack_count"] = len(result.get("packs", []))
        return result

    return {
        "base_url": base_url,
        "types": types,
        "selected_type": pack_type,
        "packs": [],
        "pack_count": 0,
    }


def _load_remote_types(path_or_url=None):
    manifest_source = path_or_url or DEFAULT_REMOTE_MANIFEST
    try:
        return _load_remote_manifest(manifest_source).get("types", [])
    except (urllib.error.HTTPError, urllib.error.URLError):
        base_url = _remote_base_url(manifest_source)
        if not base_url:
            raise
        return _normalize_types_payload(_load_json(urljoin(base_url, "types")))


def _load_type_packs_endpoint(path_or_url, pack_type):
    base_url = _remote_base_url(path_or_url)
    if not base_url:
        raise

    types = _load_remote_types(path_or_url)
    endpoint = urljoin(base_url, f"types/{quote(pack_type)}/packs")
    return _normalize_packs_payload(_load_json(endpoint), base_url, pack_type, types)


def _load_remote_manifest(path_or_url=None, pack_type=None):
    manifest_source = path_or_url or DEFAULT_REMOTE_MANIFEST
    try:
        manifest = _load_json(_with_type_query(manifest_source, pack_type))
    except (urllib.error.HTTPError, urllib.error.URLError):
        if pack_type:
            return _load_type_packs_endpoint(manifest_source, pack_type)
        raise

    if pack_type and "selected_type" not in manifest:
        manifest = _filter_manifest_by_type(manifest, pack_type)
    return manifest


def _filter_manifest_by_type(manifest, pack_type):
    types = manifest.get("types", [])
    type_info = next((item for item in types if item.get("key") == pack_type), None)
    oss_prefix = (type_info or {}).get("oss_prefix", "")

    filtered = []
    for pack in manifest.get("packs", []):
        if _pack_type(pack, types) == pack_type:
            filtered.append(pack)
            continue
        if oss_prefix and str(pack.get("url", "")).startswith(oss_prefix):
            filtered.append(pack)

    result = dict(manifest)
    result["selected_type"] = pack_type
    result["packs"] = filtered
    result["pack_count"] = len(filtered)
    return result


def _pack_type(pack, types=None):
    for key in ("type", "pack_type"):
        value = pack.get(key)
        if value:
            return value

    category = pack.get("category")
    if category and types and any(item.get("key") == category for item in types):
        return category

    url = str(pack.get("url", ""))
    for item in types or []:
        prefix = item.get("oss_prefix")
        if prefix and url.startswith(prefix):
            return item.get("key")

    return category


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
                data = json.loads(pack_json.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                data = {"id": child.name, "status": "invalid-manifest"}
        else:
            data = {"id": child.name, "status": "installed"}

        data.setdefault("path", str(child.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        packs.append(data)
    return packs


def list_packs(args):
    included = _load_included_manifest().get("packs", [])
    manifest = _load_remote_manifest(args.manifest, args.pack_type) if args.include_remote else {}
    remote = manifest.get("packs", [])
    types = manifest.get("types", [])
    installed_ids = {pack.get("id") for pack in _installed_packs()}

    rows = []
    for pack in included:
        rows.append({
            "id": pack.get("id"),
            "name": pack.get("name"),
            "version": pack.get("version"),
            "category": pack.get("category"),
            "origin": "included",
            "origin_label": "内置",
            "installed": True,
        })

    for pack in remote:
        pack_type = _pack_type(pack, types)
        rows.append({
            "id": pack.get("id"),
            "name": pack.get("name"),
            "version": pack.get("version"),
            "category": pack.get("category"),
            "type": pack_type,
            "origin": "server",
            "origin_label": "云端",
            "installed": pack.get("id") in installed_ids,
        })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    for row in rows:
        marker = "已安装" if row["installed"] else "可安装"
        type_label = f"/{row.get('type')}" if row.get("type") else ""
        print(f"{row['id']} [{row['origin_label']}{type_label}/{marker}] {row.get('name', '')} v{row.get('version', '')}")


def list_types(args):
    types = _load_remote_types(args.manifest)
    if args.json:
        print(json.dumps(types, ensure_ascii=False, indent=2))
        return

    if not types:
        print("远程 manifest 未返回类型列表。")
        return

    for item in types:
        print(f"{item.get('key')} {item.get('label', '')} ({item.get('count', 0)}) - {item.get('oss_prefix', '')}")


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


def _download_pack_archive(manifest, pack, archive_url, dest):
    try:
        _download(archive_url, dest)
        return
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise

    base_url = manifest.get("base_url", "")
    if not base_url:
        raise SystemExit(f"知识包下载失败，且 manifest 缺少 base_url: {pack.get('id')}")

    download_api = urljoin(base_url.rstrip("/") + "/", f"packs/{pack.get('id')}/download")
    with urllib.request.urlopen(download_api, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    signed_url = payload.get("download_url")
    if not signed_url:
        raise SystemExit(f"下载接口未返回 download_url: {download_api}")

    _download(signed_url, dest)


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
    manifest = _load_remote_manifest(args.manifest, getattr(args, "pack_type", None))
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
        _download_pack_archive(manifest, pack, archive_url, archive_path)
        _verify_checksum(archive_path, pack.get("checksum"))
        _safe_extract_zip(archive_path, unpack_dir)

        pack_json = unpack_dir / "pack.json"
        if not pack_json.exists():
            pack_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(unpack_dir, target_dir)

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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="同步 novel-harness 知识包")
    parser.add_argument("--manifest", help="远程 manifest 路径或 URL")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="列出内置和远程知识包")
    list_parser.add_argument("--include-remote", action="store_true", help="包含远程 manifest 中的知识包")
    list_parser.add_argument("--type", dest="pack_type", help="只列出指定类型的远程知识包")
    list_parser.set_defaults(func=list_packs)

    types_parser = subparsers.add_parser("types", help="列出远程知识包类型")
    types_parser.set_defaults(func=list_types)

    installed_parser = subparsers.add_parser("installed", help="列出已安装的远程知识包")
    installed_parser.set_defaults(func=list_installed)

    install_parser = subparsers.add_parser("install", help="安装远程知识包")
    install_parser.add_argument("pack_id")
    install_parser.add_argument("--type", dest="pack_type", help="从指定类型中查找远程知识包")
    install_parser.add_argument("--rebuild-index", action="store_true")
    install_parser.set_defaults(func=install_pack)

    update_parser = subparsers.add_parser("update", help="更新远程知识包")
    update_parser.add_argument("pack_id")
    update_parser.add_argument("--type", dest="pack_type", help="从指定类型中查找远程知识包")
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
