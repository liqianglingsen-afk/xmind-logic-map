---
name: xmind-logic-map
description: Create reliable, editable XMind mind maps from videos, web pages, PDFs, ebooks, documents, transcripts, or long-form text. Use when the user asks to make a mind map, XMind file, logic map, 脑图, 思维导图, or structured visual outline—especially when the deliverable needs source links, notes, images, and compatibility with the XMind desktop app.
---

# XMind Logic Map

## Goal

Deliver a `.xmind` package that opens in the target XMind desktop version, is logically useful, and preserves source links, notes, and images where requested. Treat a ZIP that parses as insufficient: use XMind-compatible JSON and validate the actual package.

## Workflow

1. Identify the source and extract reliable content.
   - Video: collect title, author/channel, duration, date, description, links, subtitles or a local transcript.
   - Document/web page: preserve section/page cues and source links.
   - Do not turn a transcript into a node dump; synthesize decisions, steps, comparisons, risks, and actions.
2. Build a logic-first outline before packaging.
   - Start with source information and an explicit `重要资源链接` branch when a source/resource link exists.
   - Put source/resource links in human-readable topics with `href`.
   - For tutorials, favor: goal, prerequisites, workflow steps, validation, troubleshooting, risks, action checklist.
3. Use enhanced mode unless the user asks for text-only.
   - For normal videos, include 6–10 meaningful, real screenshots; place each below the relevant step.
   - Select frames after identifying state changes, not at arbitrary time intervals. Reject duplicate, blank, dark, or unreadable frames.
   - Add concise node titles for screenshots. Only burn labels into images when needed; use a CJK-capable font.
4. Generate a modern JSON-based XMind package using the compatibility contract below.
5. Run `scripts/validate_xmind.py` on the final file. Fix every error before delivery.
6. When the local XMind desktop app is accessible, open the final file before delivery. If it can be safely saved, reopen the saved result once. Do not claim desktop verification if it was not performed.

## Compatibility Contract (mandatory)

### Package layout

Create a ZIP whose root contains these files directly—never wrap them in another top-level folder:

```text
map.xmind
├── content.json
├── metadata.json
├── manifest.json
└── resources/                 # only when images/attachments exist
```

- Encode JSON as UTF-8.
- Use `/` in ZIP paths; reject absolute paths and `..` segments.
- Do not add `content.xml`, `meta.xml`, or `META-INF/manifest.xml` unless they were produced by a known-good XMind compatibility exporter. A malformed XML compatibility layer can break an otherwise valid package.
- Prefer the smallest supported JSON feature set. Do not invent undocumented fields.

### Required JSON baseline

`metadata.json`:

```json
{
  "dataStructureVersion": "2",
  "creator": { "name": "Codex" },
  "layoutEngineVersion": "3"
}
```

`manifest.json`:

```json
{
  "file-entries": {
    "content.json": {},
    "metadata.json": {},
    "resources/frame-01.png": {}
  }
}
```

`content.json` must be a JSON array of sheets. A sheet uses `rootTopic`, never `topic`:

```json
[
  {
    "id": "sheet-1",
    "class": "sheet",
    "title": "教程导图",
    "rootTopic": {
      "id": "root-1",
      "class": "topic",
      "title": "中心主题",
      "structureClass": "org.xmind.ui.logic.right",
      "children": { "attached": [] }
    }
  }
]
```

### Topic rules

- Assign a unique, stable string ID to every sheet, topic, relationship, summary, and other referenced object.
- Use `class: "topic"` and a string `title` for every topic.
- Put ordinary child topics only in `children.attached` as an array.
- Use `href` for a clickable source/resource URL. Keep a readable label as the title.
- Use `labels` only as an array of strings. Omit it when labels are unnecessary.
- Add relationships, summaries, boundaries, markers, style, or task metadata only when their schema and references are known valid for the target client. Omit unused advanced fields.

### Notes (strict schema)

Never write a note as `"plain": "text"`. XMind expects an object:

```json
"notes": {
  "plain": { "content": "结论：…\n证据：…\n风险提醒：…" },
  "realHTML": { "content": "结论：…<br>证据：…<br>风险提醒：…" }
}
```

- `notes.plain.content` must be a string.
- Include `realHTML.content` when creating rich notes; it must also be a string.
- Prefer notes for root, major steps, decision criteria, and risks—not every leaf.
- For tutorial maps, use this compact template: `结论` / `证据` / `风险提醒`.

### Images and resources

For every image topic:

```json
"image": {
  "src": "xap:resources/frame-01.png"
}
```

- Put the actual nonempty file at `resources/frame-01.png` in the ZIP.
- Register that same relative path in `manifest.json`.
- Keep the image-node count, actual resource count, and manifest resource count aligned.
- Do not put local file paths in `image.src`.
- Use image dimensions only when confirmed compatible; `src` alone is the safe baseline.

## Source and visual quality rules

- Make the original source clickable whenever a URL exists.
- Create `重要资源链接` as a top-level branch; its direct resource topics must be clickable when an accessible URL exists.
- State explicitly when a creator mentions a resource but does not publish an accessible link.
- Inspect selected screenshots as a set before packaging. Prefer instructional states: input, setting, choice, verification, result, or meaningful troubleshooting.

## Validation

Run the bundled validator:

```powershell
py "C:\Users\Q\.codex\skills\xmind-logic-map\scripts\validate_xmind.py" "<absolute-path-to-map.xmind>"
```

The validator checks ZIP integrity, root layout, JSON types, `rootTopic`, unique IDs, notes schema, topic trees, links, image/resource/manifest consistency, and relationship endpoints. It does not prove the visual layout is good or replace opening the file in XMind.

Before handoff, confirm:

- `content.json`, `metadata.json`, and `manifest.json` parse.
- Every sheet has `rootTopic`; no sheet has a legacy `topic` key.
- All IDs and cross-references are valid.
- Each note uses the object schema above.
- Every image reference exists, is nonempty, and is registered in the manifest.
- The ZIP contains no extra root folder and passes integrity testing.
- The original source is linked; required resource links exist.
- Selected frames are relevant and readable.
- XMind desktop opening was tested when possible; otherwise disclose that only structural validation was performed.

## Final response

Link the actual `.xmind` file. Report main-branch count, total nodes, images, notes, clickable links, and whether desktop opening was verified.

