"""Condition evaluation for skills."""

from __future__ import annotations

import re
from typing import Any

from phone_agent.skills.selector import find_nodes
from phone_agent.skills.utils import hamming_distance


def _normalize_text(value: str) -> str:
    return value.casefold().strip()


def _match_text_list(texts: list[str], targets: list[str]) -> bool:
    normalized = [_normalize_text(t) for t in texts]
    return all(_normalize_text(target) in normalized for target in targets)


def _match_text_any(texts: list[str], targets: list[str]) -> bool:
    normalized = [_normalize_text(t) for t in texts]
    return any(_normalize_text(target) in normalized for target in targets)


def _match_text_contains(texts: list[str], targets: list[str]) -> bool:
    normalized = [_normalize_text(t) for t in texts]
    return all(
        any(_normalize_text(target) in text for text in normalized)
        for target in targets
    )


def _match_text_any_contains(texts: list[str], targets: list[str]) -> bool:
    normalized = [_normalize_text(t) for t in texts]
    return any(
        any(_normalize_text(target) in text for text in normalized)
        for target in targets
    )


def _match_regex_list(texts: list[str], patterns: list[str], require_all: bool) -> bool:
    normalized = [_normalize_text(t) for t in texts]
    results = []
    for pattern in patterns:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            results.append(False)
            continue
        results.append(any(regex.search(text) for text in normalized))
    return all(results) if require_all else any(results)


def evaluate_condition(spec: dict[str, Any] | None, observation: Any) -> bool | None:
    if spec is None:
        return True
    if not isinstance(spec, dict):
        return None

    if "all" in spec:
        results = [evaluate_condition(item, observation) for item in spec.get("all", [])]
        if any(result is False for result in results):
            return False
        if any(result is None for result in results):
            return None
        return True

    if "any" in spec:
        results = [evaluate_condition(item, observation) for item in spec.get("any", [])]
        if any(result is True for result in results):
            return True
        if all(result is False for result in results):
            return False
        return None

    if "not" in spec:
        result = evaluate_condition(spec.get("not"), observation)
        if result is None:
            return None
        return not result

    if "app_is" in spec:
        expected = spec.get("app_is")
        if isinstance(expected, list):
            return observation.app_name in expected
        return observation.app_name == expected

    if "app_in" in spec:
        expected = spec.get("app_in")
        if isinstance(expected, list):
            return observation.app_name in expected
        return False

    texts = observation.ui_texts
    if ("text_all" in spec or "text_any" in spec or "text_contains" in spec or "text_any_contains" in spec or "text_regex_any" in spec or "text_regex_all" in spec) and not texts:
        return None

    if "text_all" in spec:
        return _match_text_list(texts, spec.get("text_all", []))

    if "text_any" in spec:
        return _match_text_any(texts, spec.get("text_any", []))

    if "text_contains" in spec:
        return _match_text_contains(texts, spec.get("text_contains", []))

    if "text_any_contains" in spec:
        return _match_text_any_contains(texts, spec.get("text_any_contains", []))

    if "text_regex_all" in spec:
        return _match_regex_list(texts, spec.get("text_regex_all", []), True)

    if "text_regex_any" in spec:
        return _match_regex_list(texts, spec.get("text_regex_any", []), False)

    if "selector" in spec:
        selector = spec.get("selector")
        if not observation.ui_nodes:
            return None
        return bool(find_nodes(observation.ui_nodes, selector))

    if "screen_hash" in spec:
        if observation.screen_hash is None:
            return None
        expected = spec.get("screen_hash", {})
        if isinstance(expected, str):
            expected_hash = expected
            max_distance = 0
        else:
            expected_hash = expected.get("value")
            max_distance = int(expected.get("distance", 0))
        if not expected_hash:
            return None
        try:
            distance = hamming_distance(observation.screen_hash, expected_hash)
        except ValueError:
            return None
        return distance <= max_distance

    return None
