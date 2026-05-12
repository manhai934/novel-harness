"""
normalizer.py — 文档标准化器

职责：
- 读取 Markdown 文件原始内容
- 从路径和内容中提取 metadata
- 输出统一的 document 结构
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SOURCE_TO_CATEGORY = {
    "human-linguistics": {
        "rules": "common.humanization",
        "references": "common.language",
    },
    "plot-review": {
        "rules": "common.outline_review",
        "references": "common.consistency",
    },
    "plot-ideation": {
        "rules": "common.ideation",
        "references": "common.ideation",
    },
    "rhythm-review": {
        "rules": "common.rhythm",
        "references": "common.rhythm",
    },
    "game-datafied": {
        "rules": "common.outline",
        "references": "common.outline",
    },
    "projects": {
        "project": "common.project",
    },
}

# 特殊文件名映射（处理跨 skill 目录的特殊文档）
FILE_CATEGORY_OVERRIDES = {
    "章节写前准备清单": "common.prewrite",
    "大纲质量评估清单": "common.outline_review",
    "状态一致性补充清单": "common.consistency",
    "去AI味最小修改指南": "common.humanization",
    "句式节奏档案": "common.rhythm",
    "阅读体验与章节润色检查": "common.rhythm",
}


def _extract_skill_name(rel_path):
    """从相对路径中提取技能目录名"""
    parts = rel_path.replace("\\", "/").split("/")
    try:
        skills_idx = parts.index("skills")
        if skills_idx + 1 < len(parts):
            return parts[skills_idx + 1]
    except ValueError:
        pass
    return None


def _infer_stage(rel_path, content):
    """确定 stage（适用阶段）"""
    stages = []
    lower = content.lower()
    path_lower = rel_path.lower()

    # 从路径推断
    if any(k in path_lower for k in ("ideation", "灵感", "构思")):
        stages.append("ideation")
    if any(k in path_lower for k in ("outline", "大纲", "结构")):
        stages.append("outline")
    if any(k in path_lower for k in ("prewrite", "写前", "准备")):
        stages.append("prewrite")
    if any(k in path_lower for k in ("rhythm", "节奏", "润色", "阅读体验")):
        stages.extend(["drafting", "revision"])
    if any(k in path_lower for k in ("human", "去ai", "修改", "自然")):
        stages.append("revision")
    if any(k in path_lower for k in ("review", "审查", "评估", "审稿")):
        stages.append("review")

    # 从内容推断
    if any(k in lower for k in ("大纲", "骨架", "结构评估")):
        if "outline" not in stages:
            stages.append("outline")
        if "review" not in stages:
            stages.append("review")
    if any(k in lower for k in ("写前", "准备", "开始写")):
        if "prewrite" not in stages:
            stages.append("prewrite")
    if any(k in lower for k in ("修改", "润色", "去ai", "总结腔")):
        if "revision" not in stages:
            stages.append("revision")

    # 默认
    if not stages:
        stages.extend(["drafting", "review"])

    # 去重
    return list(dict.fromkeys(stages))


def _infer_doc_id(rel_path):
    """从路径推断 doc_id"""
    parts = rel_path.replace("\\", "/").split("/")
    file_name = Path(rel_path).stem

    skill_name = _extract_skill_name(rel_path)
    if skill_name:
        return f"{skill_name}.{file_name}"

    if rel_path.replace("\\", "/").startswith(".harness/projects/"):
        return f"project.{file_name}"

    return file_name


def _infer_category(rel_path):
    """从路径推断 category"""
    path = rel_path.replace("\\", "/")
    file_name = Path(rel_path).stem

    # 文件名覆盖
    if file_name in FILE_CATEGORY_OVERRIDES:
        return FILE_CATEGORY_OVERRIDES[file_name]

    # projects
    if path.startswith(".harness/projects/"):
        return "common.project"

    skill_name = _extract_skill_name(rel_path)
    if not skill_name:
        return "common"

    is_rule = "/rules/" in path
    is_ref = "/references/" in path

    mapping = SOURCE_TO_CATEGORY.get(skill_name)
    if mapping:
        if is_rule and "rules" in mapping:
            return mapping["rules"]
        if is_ref and "references" in mapping:
            return mapping["references"]

    return "common"


def _infer_scope(rel_path):
    """推断 scope"""
    if rel_path.replace("\\", "/").startswith(".harness/projects/"):
        return "project"
    return "common"


def _infer_tags(rel_path, content):
    """提取标签"""
    tags = []
    path = rel_path.replace("\\", "/")
    file_name = Path(rel_path).stem

    tags.append(file_name)

    skill_name = _extract_skill_name(rel_path)
    if skill_name:
        tags.append(skill_name)

    # 从内容标题提取
    import re
    m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    if m:
        tags.append(m.group(1).strip())

    return tags


def _infer_priority(rel_path):
    """推断优先级（1=最高, 5=最低）"""
    path = rel_path.replace("\\", "/")
    if "/rules/" in path:
        return 1
    if "/references/" in path:
        return 2
    if path.startswith(".harness/projects/"):
        return 3
    return 4


def normalize_document(rel_path, source_type):
    """标准化单个文件为 document 对象

    Args:
        rel_path: 相对路径
        source_type: 源类型 (rule/reference/project)

    Returns:
        document dict 或 None（读取失败时）
    """
    abs_path = PROJECT_ROOT / rel_path

    try:
        content = abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[normalizer] 无法读取文件: {rel_path} ({e})")
        return None

    # 提取标题
    import re
    m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = m.group(1).strip() if m else Path(rel_path).stem

    doc_id = _infer_doc_id(rel_path)
    category = _infer_category(rel_path)
    priority = _infer_priority(rel_path)
    tags = _infer_tags(rel_path, content)
    stage = _infer_stage(rel_path, content)

    return {
        "doc_id": doc_id,
        "title": title,
        "source_path": rel_path.replace("\\", "/"),
        "source_type": source_type,
        "category": category,
        "stage": stage,
        "scope": _infer_scope(rel_path),
        "tags": tags,
        "priority": priority,
        "status": "active",
        "_raw_content": content,  # 内部传递，不持久化
    }
