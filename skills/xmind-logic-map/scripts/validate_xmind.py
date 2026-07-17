#!/usr/bin/env python3
"""Validate the safe, JSON-based subset of an XMind package."""

from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter
from pathlib import PurePosixPath


def fail(message: str) -> None:
    raise ValueError(message)


def safe_zip_path(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def validate_topic(topic: object, seen_ids: set[str], stats: Counter, image_sources: list[str]) -> None:
    if not isinstance(topic, dict):
        fail("topic must be an object")
    if topic.get("class") != "topic":
        fail(f"topic {topic.get('id', '<missing>')} has invalid class")
    topic_id = topic.get("id")
    if not isinstance(topic_id, str) or not topic_id:
        fail("every topic needs a nonempty string id")
    if topic_id in seen_ids:
        fail(f"duplicate id: {topic_id}")
    seen_ids.add(topic_id)
    if not isinstance(topic.get("title"), str):
        fail(f"topic {topic_id} needs a string title")
    stats["topics"] += 1

    href = topic.get("href")
    if href is not None:
        if not isinstance(href, str) or not href:
            fail(f"topic {topic_id} has invalid href")
        stats["links"] += 1

    labels = topic.get("labels")
    if labels is not None and (not isinstance(labels, list) or not all(isinstance(x, str) for x in labels)):
        fail(f"topic {topic_id} has invalid labels")

    notes = topic.get("notes")
    if notes is not None:
        if not isinstance(notes, dict):
            fail(f"topic {topic_id} notes must be an object")
        plain = notes.get("plain")
        if not isinstance(plain, dict) or not isinstance(plain.get("content"), str):
            fail(f"topic {topic_id} notes.plain.content must be a string")
        real_html = notes.get("realHTML")
        if real_html is not None and (not isinstance(real_html, dict) or not isinstance(real_html.get("content"), str)):
            fail(f"topic {topic_id} notes.realHTML.content must be a string")
        stats["notes"] += 1

    image = topic.get("image")
    if image is not None:
        if not isinstance(image, dict) or not isinstance(image.get("src"), str):
            fail(f"topic {topic_id} image must contain a string src")
        src = image["src"]
        if not src.startswith("xap:resources/") or ".." in src or "\\" in src:
            fail(f"topic {topic_id} has unsafe or unsupported image src: {src}")
        image_sources.append(src.removeprefix("xap:"))
        stats["images"] += 1

    children = topic.get("children")
    if children is not None:
        if not isinstance(children, dict):
            fail(f"topic {topic_id} children must be an object")
        attached = children.get("attached", [])
        if not isinstance(attached, list):
            fail(f"topic {topic_id} children.attached must be an array")
        for child in attached:
            validate_topic(child, seen_ids, stats, image_sources)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_xmind.py <map.xmind>", file=sys.stderr)
        return 2
    map_path = sys.argv[1]
    with zipfile.ZipFile(map_path) as archive:
        bad_file = archive.testzip()
        if bad_file:
            fail(f"ZIP CRC error: {bad_file}")
        names = {name for name in archive.namelist() if not name.endswith("/")}
        if not all(safe_zip_path(name) for name in names):
            fail("ZIP contains an unsafe path")
        required = {"content.json", "metadata.json", "manifest.json"}
        missing = required - names
        if missing:
            fail(f"missing required package files: {', '.join(sorted(missing))}")
        content = json.loads(archive.read("content.json"))
        metadata = json.loads(archive.read("metadata.json"))
        manifest = json.loads(archive.read("manifest.json"))

        if not isinstance(content, list) or not content:
            fail("content.json must be a nonempty sheet array")
        if not isinstance(metadata, dict):
            fail("metadata.json must be an object")
        entries = manifest.get("file-entries") if isinstance(manifest, dict) else None
        if not isinstance(entries, dict):
            fail("manifest.json file-entries must be an object")

        seen_ids: set[str] = set()
        stats: Counter = Counter(sheets=0, topics=0, notes=0, links=0, images=0)
        image_sources: list[str] = []
        relationship_endpoints: list[tuple[object, object]] = []
        for sheet in content:
            if not isinstance(sheet, dict) or sheet.get("class") != "sheet":
                fail("each content item must be a sheet object")
            sheet_id = sheet.get("id")
            if not isinstance(sheet_id, str) or not sheet_id or sheet_id in seen_ids:
                fail("each sheet needs a unique nonempty string id")
            seen_ids.add(sheet_id)
            if "topic" in sheet:
                fail(f"sheet {sheet_id} uses legacy topic; use rootTopic")
            if not isinstance(sheet.get("title"), str) or not isinstance(sheet.get("rootTopic"), dict):
                fail(f"sheet {sheet_id} needs title and rootTopic")
            validate_topic(sheet["rootTopic"], seen_ids, stats, image_sources)
            stats["sheets"] += 1
            relationships = sheet.get("relationships", [])
            if not isinstance(relationships, list):
                fail(f"sheet {sheet_id} relationships must be an array")
            for relationship in relationships:
                if not isinstance(relationship, dict) or relationship.get("class") != "relationship":
                    fail(f"sheet {sheet_id} has invalid relationship")
                relation_id = relationship.get("id")
                if not isinstance(relation_id, str) or not relation_id or relation_id in seen_ids:
                    fail("each relationship needs a unique nonempty string id")
                seen_ids.add(relation_id)
                relationship_endpoints.append((relationship.get("end1Id"), relationship.get("end2Id")))

        for end1, end2 in relationship_endpoints:
            if end1 not in seen_ids or end2 not in seen_ids:
                fail("relationship endpoint references a missing id")

        image_set = set(image_sources)
        if len(image_set) != len(image_sources):
            fail("duplicate image src values are not allowed in the safe subset")
        zip_resources = {name for name in names if name.startswith("resources/")}
        manifest_resources = {name for name in entries if name.startswith("resources/")}
        if image_set != zip_resources or image_set != manifest_resources:
            fail("image references, resource files, and manifest entries must match exactly")
        for resource in zip_resources:
            if not archive.read(resource):
                fail(f"resource is empty: {resource}")

    print(json.dumps({"status": "ok", **stats, "resource_files": len(image_sources)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        raise SystemExit(1)

