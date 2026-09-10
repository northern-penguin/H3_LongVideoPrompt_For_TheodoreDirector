#!/usr/bin/env python3
"""校验H3分段提示词项目的关键机械约束。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from export_director_plan import build_plan, default_output_path


REQUIRED_FILES = ("素材映射.md", "分镜设计.md", "H3分镜提示词.md")
FULL_FIELDS = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)
BASE_FIELDS = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)

# 这些措辞会使本应单独提交的分镜提示词依赖其他分镜，需明确拦截。
CROSS_SEGMENT_PATTERNS = (
    r"(?:上一|上个|前一|之前|下一|下个|后续)分镜",
    r"(?:承接|延续|衔接|接续|回顾|预告)(?:上一|上个|前一|之前|下一|下个|后续)?(?:个)?分镜",
    r"(?:previous|prior|next|following)\s+(?:segment|storyboard|prompt)",
    r"(?:continues?|continuation)\s+(?:from|into)\s+(?:the\s+)?(?:previous|prior|next|following)\s+(?:segment|storyboard|prompt)",
    r"(?:recurr(?:ing|s)?|repeats?)\s+(?:across|in)\s+(?:multiple|other)\s+(?:segments?|prompts?|storyboards?)",
)


def read_text(path: Path) -> str:
    """使用utf-8-sig兼容普通UTF-8和带BOM的Markdown文件。"""
    return path.read_text(encoding="utf-8-sig")


def parse_time(value: str) -> int:
    """把MM:SS转换为秒。"""
    minute, second = value.split(":")
    return int(minute) * 60 + int(second)


def parse_assets(mapping_text: str) -> dict[str, str]:
    """从素材三级标题与后续类型字段中提取别名和类型。"""
    assets: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^###\s+\d+\.\s+`([^`]+)`\s*$", mapping_text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(mapping_text)
        block = mapping_text[match.end() : end]
        type_match = re.search(r"(?m)^-\s*类型：\s*(图片|视频|音频)\s*$", block)
        if type_match:
            assets[match.group(1)] = type_match.group(1)
    return assets


def prompt_blocks(prompt_text: str) -> list[tuple[str, str]]:
    """提取每个分镜标题与紧随其后的text代码块。"""
    pattern = re.compile(
        r"(?ms)^##\s+(.+?｜[^\r\n]+)\s*\r?\n\s*```text\s*\r?\n(.*?)\r?\n```"
    )
    return [(match.group(1), match.group(2)) for match in pattern.finditer(prompt_text)]


def field_order(block: str) -> list[str]:
    """获取代码块中的顶级字段顺序。"""
    return re.findall(r"(?m)^([a-z_]+):", block)


def storyboard_segments(storyboard_text: str) -> list[tuple[str, bool, bool]]:
    """提取分镜名称及其是否为明确跨段长镜头，供提示词标题逐一核对。"""
    pattern = re.compile(r"(?ms)^###\s+(.+?)｜\d{2}:\d{2}—\d{2}:\d{2}[^\r\n]*\r?\n(.*?)(?=^###\s+|\Z)")
    segments: list[tuple[str, bool, bool]] = []
    for match in pattern.finditer(storyboard_text):
        label, content = match.groups()
        declaration = re.search(
            r"(?m)^-\s*长镜头跨段：\s*(是（接续上一个分镜）|否)\s*$", content
        )
        is_long_take_continuation = bool(
            declaration and declaration.group(1) == "是（接续上一个分镜）"
        )
        segments.append((label, is_long_take_continuation, declaration is not None))
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(description="校验H3分段提示词项目")
    parser.add_argument("project_dir", type=Path, help="包含三份Markdown交付物的视频项目目录")
    args = parser.parse_args()
    root = args.project_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    paths = {name: root / name for name in REQUIRED_FILES}
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"缺少必需文件：{name}")
    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    mapping = read_text(paths["素材映射.md"])
    storyboard = read_text(paths["分镜设计.md"])
    prompts = read_text(paths["H3分镜提示词.md"])
    expected_director_plan: dict[str, object] | None = None
    try:
        expected_director_plan, _ = build_plan(root)
        director_path = default_output_path(root, expected_director_plan)
        if not director_path.is_file():
            errors.append(f"缺少 Theodore Director 导出文件：{director_path.name}")
        else:
            try:
                director_plan = json.loads(read_text(director_path))
            except json.JSONDecodeError as exc:
                errors.append(f"{director_path.name} 不是有效 JSON：{exc}")
            else:
                if director_plan.get("schemaVersion") != 5:
                    errors.append(f"{director_path.name} 的 schemaVersion 必须为 Theodore Director v5。")
                expected_assets = expected_director_plan["assets"]
                actual_assets = director_plan.get("assets")
                if actual_assets != expected_assets:
                    errors.append(f"{director_path.name} 的素材映射与素材映射.md 不一致。")
                expected_shots = expected_director_plan["shots"]
                actual_shots = director_plan.get("shots")
                if not isinstance(actual_shots, list) or len(actual_shots) != len(expected_shots):
                    errors.append(f"{director_path.name} 的分镜数量与 H3分镜提示词.md 不一致。")
                else:
                    for shot_index, (expected_shot, actual_shot) in enumerate(
                        zip(expected_shots, actual_shots), start=1
                    ):
                        fields_to_check = ("id", "title", "prompt", "durationSeconds", "latentRelay")
                        if any(actual_shot.get(field) != expected_shot[field] for field in fields_to_check):
                            errors.append(
                                f"{director_path.name} 的第{shot_index}个分镜与 Markdown 标题、提示词、时长或长镜头接力声明不一致。"
                            )
    except ValueError as exc:
        errors.append(f"无法生成 Theodore Director 导出计划：{exc}")
    assets = parse_assets(mapping)
    if not assets:
        warnings.append("未从素材映射的三级标题中识别到带类型的素材。")

    # 禁止把已生成分镜自动登记或引用为新素材。
    generated_ref = re.compile(r"\{\{ref:分镜\d+成片(?:\.audio)?\}\}")
    for filename, text in (
        ("素材映射.md", mapping),
        ("分镜设计.md", storyboard),
        ("H3分镜提示词.md", prompts),
    ):
        if generated_ref.search(text):
            errors.append(f"{filename} 包含禁止的自动分镜素材引用。")

    blocks = prompt_blocks(prompts)
    headings = re.findall(r"(?m)^##\s+.+?｜\d{2}:\d{2}—\d{2}:\d{2}", prompts)
    if len(blocks) != len(headings):
        errors.append(f"识别到{len(headings)}个分镜标题，但只有{len(blocks)}个完整text代码块。")

    design_segments = storyboard_segments(storyboard)
    design_labels = [label for label, _, _ in design_segments]
    label_counts = {label: design_labels.count(label) for label in design_labels}
    occurrence_counts: dict[str, int] = {}
    expected_labels: list[str] = []
    for label in design_labels:
        occurrence_counts[label] = occurrence_counts.get(label, 0) + 1
        expected_labels.append(
            f"{label}{occurrence_counts[label]:02d}" if label_counts[label] > 1 else label
        )
    if len(expected_labels) != len(blocks):
        errors.append("分镜设计与分镜提示词的分镜数量不一致，无法核对标题名称。")

    previous_end: int | None = None
    for index, (title, block) in enumerate(blocks, start=1):
        title_match = re.match(r"(.+?)｜(\d{2}:\d{2})—(\d{2}:\d{2})", title)
        if not title_match:
            errors.append(f"无法解析分镜标题时间：{title}")
            continue
        label, start_text, end_text = title_match.groups()
        display_name = label
        if index <= len(expected_labels) and label != expected_labels[index - 1]:
            errors.append(f"分镜{index:02d}标题应为“{expected_labels[index - 1]}”，需与分镜设计名称一致；重名时在名称后追加组内序号。")
        start, end = parse_time(start_text), parse_time(end_text)
        duration = end - start
        if not 5 <= duration <= 15:
            errors.append(f"{display_name}时长为{duration}秒，不在5—15秒范围内。")
        if previous_end is not None and start != previous_end:
            warnings.append(f"{display_name}起点{start_text}与上一分镜终点不连续。")
        previous_end = end

        fields = field_order(block)
        expected = FULL_FIELDS if "subject_definitions" in fields else BASE_FIELDS
        if tuple(fields) != expected:
            errors.append(f"{display_name}字段顺序不符合基础三字段或完整参考六字段结构：{fields}")

        if re.search(r"<(?:Picture|Video|Audio)\s+\d+>", block, re.I):
            errors.append(f"{display_name}仍使用官方Picture/Video/Audio编号，没有改用自定义ref。")

        aliases = set(re.findall(r"\{\{ref:([^}]+)\}\}", block))
        base_aliases = {alias[:-6] if alias.endswith(".audio") else alias for alias in aliases}
        unknown = sorted(alias for alias in base_aliases if alias not in assets)
        if unknown:
            errors.append(f"{display_name}引用未登记素材：{', '.join(unknown)}")

        counts = {"图片": 0, "视频": 0, "音频": 0}
        for alias in aliases:
            if alias.endswith(".audio"):
                counts["音频"] += 1
            else:
                asset_type = assets.get(alias)
                if asset_type:
                    counts[asset_type] += 1
        if counts["图片"] > 9 or counts["视频"] > 3 or counts["音频"] > 3:
            errors.append(
                f"{display_name}超出素材上限：图片{counts['图片']}、"
                f"视频{counts['视频']}、音频{counts['音频']}。"
            )

        has_continuation_marker = title.endswith("（接续上一个分镜）")
        if "接续" in title and not has_continuation_marker:
            errors.append(f"{display_name}接续标记应写成（接续上一个分镜）。")
        if index <= len(design_segments):
            expected_continuation = design_segments[index - 1][1]
            has_declaration = design_segments[index - 1][2]
            if not has_declaration:
                errors.append(f"{display_name}在分镜设计中缺少“长镜头跨段：是（接续上一个分镜）”或“长镜头跨段：否”声明。")
            if expected_continuation != has_continuation_marker:
                errors.append(f"{display_name}的接续标记必须与分镜设计中的“长镜头跨段”声明一致。")

        # 标题允许接续标记，但提示词正文不得包含跨分镜生成依赖。
        for pattern in CROSS_SEGMENT_PATTERNS:
            if re.search(pattern, block, re.IGNORECASE):
                errors.append(f"{display_name}提示词包含跨分镜表述，代码块必须能独立生成。")
                break

    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")
    if errors:
        print(f"校验失败：{len(errors)}个错误，{len(warnings)}个警告。")
        return 1
    print(f"校验通过：{len(blocks)}个分镜，{len(assets)}项已登记素材，{len(warnings)}个警告。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
