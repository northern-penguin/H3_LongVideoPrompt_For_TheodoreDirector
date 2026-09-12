---
name: h3-seg-prompt-design
description: Design long-form H3 video projects as 5–15 second generation segments, including inspiration, locked reference-asset mapping, storyboard continuity, dialogue and voiceover, and H3-compliant per-segment prompts. Use when a user wants segmented H3 prompts or a long video planned for repeated H3 generation; do not use for unrelated video models or ordinary prose scripts.
metadata:
  short-description: Design segmented long-form H3 video prompts
---

# H3 Segmented Prompt Design

Create a complete, locally organized H3 long-video prompt package without expanding the user's reference-asset set.

## Required reading

Before acting, read [references/workflow-rules.md](references/workflow-rules.md) completely.

For every H3 prompt-writing task, also read [references/h3-base-guide.md](references/h3-base-guide.md) completely. If any reference image, video, audio, keyframe, reusable subject, or source-media relationship is involved, also read [references/h3-full-reference-guide.md](references/h3-full-reference-guide.md) completely.

When exporting a Theodore Director configuration, also read [references/theodore-director-plan-v5.md](references/theodore-director-plan-v5.md) completely.

## Core workflow

1. If the user has no concrete concept, offer several distinct, segment-friendly ideas. Do not create a project folder until a theme is selected.
2. Once a theme or rough concept exists, create a folder named after the video theme inside the active workspace. Preserve any existing content if the folder already exists.
3. Confirm the complete reference-asset set with the user. Assign unique, easy aliases and create `素材映射.md`. Paths may remain empty, but every planned asset needs a textual description and role.
4. Treat the confirmed asset list as locked. Never add a generated segment, preceding clip, tail frame, companion audio, or inferred asset unless the user explicitly adds it.
5. Design shot content first, estimate its natural duration from action, dialogue, pauses, and camera motion, and only then divide it into 5–15 second generation segments in `分镜设计.md`. Never preallocate uniform durations or a segment count and fill them with content; equal durations are acceptable only when independently justified by the content. If a continuous shot needs more than 15 seconds, split it at natural action beats, keeping every segment within 5–15 seconds, and mark every segment after the first within that split group `（接续上一个分镜）` with `长镜头跨段：是（接续上一个分镜）`. Preserve uninterrupted action and camera continuity. Give each segment a concise descriptive name and a content-based duration rationale; derive the final segment count and cumulative timeline afterward. Treat a user-specified total runtime as a soft target with approximately 10% tolerance unless the user explicitly requires strict timing; prioritize natural pacing over exact second counts. In `分镜设计.md`, describe the visible scene in rich, concrete detail, especially character actions: starting pose, ordered movement, gaze and expression changes, object interactions, and ending state, coordinated with the camera. Follow workflow rules for visual detail and target-runtime handling.
6. After storyboard approval, write `H3分镜提示词.md`. Use the corresponding `分镜设计.md` segment name as each prompt heading; if a name is duplicated, append a two-digit occurrence number to that name (`雨巷初遇01`, `雨巷初遇02`). Treat every segment prompt as a self-contained, separately submitted H3 generation request: select the base or full-reference structure per segment and use only that segment's required content plus the locked source assets. Follow the official guide fields, language rules, timing, speakers, soundscape, and music rules.
7. Run `scripts/export_director_plan.py` against the video folder to generate `<项目名>.director.json`, then run `scripts/validate_project.py`. Resolve all errors and report any warnings that require user judgment, including empty Director asset paths.

## Non-negotiable invariants

- One H3 generation segment lasts from 5 through 15 seconds inclusive.
- Per segment, use no more than 9 reference images, 3 reference videos, and 3 reference audio tracks. A reference video's companion audio counts independently when explicitly enabled.
- Asset citations use `{{ref:别名}}`; companion audio uses `{{ref:别名.audio}}`.
- `<Subject N>` is not an asset citation and must never be replaced by `{{ref:...}}`.
- Decide `<Subject N>` from the actual reusable visible content in that project and segment. Scene references such as streets or shops normally remain direct environment references; do not mechanically turn every asset into a Subject.
- Keep recurring Subject numbers and speaker IDs stable across the whole project. Unused numbers may be absent from an individual segment.
- A `（接续上一个分镜）` marker is allowed only for an explicit, uninterrupted long-take continuation. It never authorizes a new asset or a `{{ref:分镜NN成片}}` citation.
- Every final prompt code block is independent. Do not mention, summarize, rely on, or instruct continuation from any other storyboard or prompt segment, including phrases such as “recurring across segments,” “continues from the previous segment,” or “this segment leads into the next one.” A `（接续上一个分镜）` marker may appear only in its Markdown heading and must have no corresponding wording inside the code block.
- Write prompt sections in English. Preserve original language only inside `<d>` for dialogue or lyrics and for visible on-screen text.
- Do not invent legible on-screen text when the user requests none.
- Do not begin final prompt authoring before the user has confirmed the storyboard direction.

## Included resources

- Copy or adapt [assets/素材映射模板.md](assets/素材映射模板.md), [assets/分镜设计模板.md](assets/分镜设计模板.md), and [assets/H3分镜提示词模板.md](assets/H3分镜提示词模板.md) when they save time; replace every placeholder.
- Validate with:

```powershell
python scripts/export_director_plan.py "<视频项目文件夹>"
python scripts/validate_project.py "<视频项目文件夹>"
```
