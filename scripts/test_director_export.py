#!/usr/bin/env python3
"""覆盖 Theodore Director JSON 导出器的核心映射规则。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from export_director_plan import build_plan, default_output_path


def write_fixture(root: Path) -> None:
    """写入含三类素材、重名分镜和跨段长镜头的最小项目。"""
    (root / "素材映射.md").write_text(
        """# 《测试项目》素材映射

### 1. `hero`
- 类型：图片
- 本地路径：input/hero.png

### 2. `walk`
- 类型：视频
- 本地路径：
- 启用视频伴音：是

### 3. `music`
- 类型：音频
- 本地路径：input/music.wav
""",
        encoding="utf-8",
    )
    (root / "分镜设计.md").write_text(
        """### 雨巷初遇｜00:00—00:05
- 长镜头跨段：否

### 雨巷初遇｜00:05—00:10
- 长镜头跨段：否

### 屋檐避雨｜00:10—00:15
- 长镜头跨段：是（接续上一个分镜）
""",
        encoding="utf-8",
    )
    (root / "H3分镜提示词.md").write_text(
        """## 雨巷初遇01｜00:00—00:05
```text
integrated_multimodal_description: {{ref:hero}}
overall_soundscape: N/A
non_diegetic_music: N/A
```

## 雨巷初遇02｜00:05—00:10
```text
integrated_multimodal_description: {{ref:walk}}
overall_soundscape: N/A
non_diegetic_music: N/A
```

## 屋檐避雨｜00:10—00:15（接续上一个分镜）
```text
integrated_multimodal_description: {{ref:walk.audio}} {{ref:music}}
overall_soundscape: N/A
non_diegetic_music: N/A
```
""",
        encoding="utf-8",
    )


def main() -> None:
    """执行无外部依赖的导出断言。"""
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        write_fixture(root)
        plan, missing_paths = build_plan(root)
        assert plan["schemaVersion"] == 5
        assert [shot["title"] for shot in plan["shots"]] == ["雨巷初遇01", "雨巷初遇02", "屋檐避雨"]
        assert [shot["latentRelay"] for shot in plan["shots"]] == [False, False, True]
        assert plan["assets"][1]["includeVideoAudio"] is True
        assert missing_paths == ["walk"]
        output_path = default_output_path(root, plan)
        output_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        assert json.loads(output_path.read_text(encoding="utf-8"))["shots"][2]["id"] == "shot_003"
        # 使用正式校验器确认 JSON 与三个 Markdown 交付物可彼此核对。
        validation = subprocess.run(
            [sys.executable, "-X", "utf8", str(Path(__file__).with_name("validate_project.py")), str(root)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert validation.returncode == 0, validation.stdout + validation.stderr
    print("Director export tests passed.")


if __name__ == "__main__":
    main()
