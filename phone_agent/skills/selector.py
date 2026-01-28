"""UI tree parsing and selector resolution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree


@dataclass(frozen=True)
class UINode:
    text: str
    resource_id: str
    content_desc: str
    class_name: str
    clickable: bool
    bounds: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return int((left + right) / 2), int((top + bottom) / 2)

    @property
    def area(self) -> int:
        left, top, right, bottom = self.bounds
        return max(0, right - left) * max(0, bottom - top)


_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _parse_bounds(bounds: str) -> tuple[int, int, int, int] | None:
    if not bounds:
        return None
    match = _BOUNDS_RE.search(bounds)
    if not match:
        return None
    left, top, right, bottom = map(int, match.groups())
    return left, top, right, bottom


def parse_uiautomator_xml(xml_str: str) -> list[UINode]:
    nodes: list[UINode] = []
    if not xml_str:
        return nodes
    try:
        root = ElementTree.fromstring(xml_str)
    except ElementTree.ParseError:
        return nodes

    for elem in root.iter():
        if elem.tag != "node":
            continue
        bounds = _parse_bounds(elem.attrib.get("bounds", ""))
        if not bounds:
            continue
        node = UINode(
            text=elem.attrib.get("text", "") or "",
            resource_id=elem.attrib.get("resource-id", "") or "",
            content_desc=elem.attrib.get("content-desc", "") or "",
            class_name=elem.attrib.get("class", "") or "",
            clickable=elem.attrib.get("clickable", "false") == "true",
            bounds=bounds,
        )
        nodes.append(node)
    return nodes


def _parse_harmony_layout(data: Any) -> list[UINode]:
    nodes: list[UINode] = []

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        attrs = node.get("attributes", {}) if isinstance(node.get("attributes"), dict) else {}
        bounds = _parse_bounds(attrs.get("bounds", "") or attrs.get("origBounds", ""))
        if bounds:
            text = attrs.get("text", "") or ""
            content_desc = (
                attrs.get("description", "")
                or attrs.get("accessibilityId", "")
                or attrs.get("contentDesc", "")
                or ""
            )
            resource_id = attrs.get("id", "") or attrs.get("resourceId", "") or ""
            class_name = attrs.get("type", "") or attrs.get("class", "") or ""
            clickable_val = attrs.get("clickable", False)
            clickable = str(clickable_val).lower() in ("true", "1", "yes")
            nodes.append(
                UINode(
                    text=text,
                    resource_id=resource_id,
                    content_desc=content_desc,
                    class_name=class_name,
                    clickable=clickable,
                    bounds=bounds,
                )
            )

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                walk(child)
        elif isinstance(children, dict):
            for child in children.values():
                walk(child)

    if isinstance(data, list):
        for item in data:
            walk(item)
    else:
        walk(data)
    return nodes


def parse_ui_dump(raw_text: str) -> list[UINode]:
    if not raw_text:
        return []
    text = raw_text.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        return _parse_harmony_layout(payload)
    return parse_uiautomator_xml(text)


def extract_texts(nodes: list[UINode]) -> list[str]:
    texts: list[str] = []
    for node in nodes:
        if node.text:
            texts.append(node.text)
        if node.content_desc:
            texts.append(node.content_desc)
    return texts


def _match_text(value: str, target: str, mode: str) -> bool:
    if mode == "exact":
        return value == target
    if mode == "contains":
        return target in value
    if mode == "regex":
        try:
            return re.search(target, value) is not None
        except re.error:
            return False
    return False


def node_matches_selector(node: UINode, selector: dict[str, Any]) -> bool:
    match_mode = selector.get("match", "contains")
    if selector.get("text"):
        if not _match_text(node.text, selector["text"], match_mode):
            return False
    if selector.get("content_desc"):
        if not _match_text(node.content_desc, selector["content_desc"], match_mode):
            return False
    if selector.get("resource_id"):
        if not _match_text(node.resource_id, selector["resource_id"], match_mode):
            return False
    if selector.get("class_name"):
        if not _match_text(node.class_name, selector["class_name"], match_mode):
            return False
    if selector.get("clickable") is True and not node.clickable:
        return False
    return True


def find_nodes(nodes: list[UINode], selector: dict[str, Any]) -> list[UINode]:
    return [node for node in nodes if node_matches_selector(node, selector)]


def pick_best_node(nodes: list[UINode]) -> UINode | None:
    if not nodes:
        return None
    # Prefer clickable nodes, then larger area.
    return sorted(nodes, key=lambda n: (n.clickable, n.area), reverse=True)[0]


def resolve_selector_to_point(
    nodes: list[UINode], selector: dict[str, Any]
) -> tuple[int, int] | None:
    matches = find_nodes(nodes, selector)
    if not matches:
        return None
    index = selector.get("index")
    if isinstance(index, int) and 0 <= index < len(matches):
        return matches[index].center
    best = pick_best_node(matches)
    if not best:
        return None
    return best.center
