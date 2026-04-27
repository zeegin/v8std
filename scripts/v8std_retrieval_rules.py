from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9_:-]+")


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for path in [current, *current.parents]:
        if (path / "zensical.toml").is_file():
            return path
    return Path.cwd()


def normalize_text(value: str) -> str:
    value = value.replace("ё", "е").replace("Ё", "Е")
    return " ".join(value.strip().casefold().split())


def tokenize(value: str) -> list[str]:
    return [match.group(0).casefold().replace("ё", "е") for match in WORD_RE.finditer(value)]


@dataclass(frozen=True)
class RetrievalRule:
    id: str
    primary: str
    aliases: tuple[str, ...]
    diagnostics: tuple[str, ...]
    standards: tuple[str, ...]
    description: str = ""

    @property
    def target_ids(self) -> tuple[str, ...]:
        targets: list[str] = []
        for value in [self.primary, *self.diagnostics, *self.standards]:
            if value and value not in targets:
                targets.append(value)
        return tuple(targets)


@dataclass(frozen=True)
class RuleMatch:
    rule: RetrievalRule
    alias: str


class RetrievalRules:
    def __init__(self, rules: list[RetrievalRule]) -> None:
        self.rules = rules
        self._alias_index: list[tuple[str, str, RetrievalRule]] = []
        for rule in rules:
            for alias in rule.aliases:
                normalized = normalize_text(alias)
                if normalized:
                    self._alias_index.append((normalized, alias, rule))
        self._alias_index.sort(key=lambda item: len(item[0]), reverse=True)

    @classmethod
    def load(cls, path: Path | None = None) -> "RetrievalRules":
        rules_path = path or repo_root_from(Path(__file__)) / "retrieval-rules.yml"
        if not rules_path.is_file():
            return cls([])

        payload = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        rules = []
        for raw in payload.get("rules", []):
            if not isinstance(raw, dict):
                continue
            rules.append(
                RetrievalRule(
                    id=str(raw.get("id", "")).strip(),
                    primary=str(raw.get("primary", "")).strip(),
                    aliases=tuple(str(item) for item in raw.get("aliases", []) if str(item).strip()),
                    diagnostics=tuple(
                        str(item) for item in raw.get("diagnostics", []) if str(item).strip()
                    ),
                    standards=tuple(
                        str(item) for item in raw.get("standards", []) if str(item).strip()
                    ),
                    description=str(raw.get("description", "")).strip(),
                )
            )
        return cls([rule for rule in rules if rule.id])

    def aliases_for_page(self, page_id: str) -> list[str]:
        aliases: list[str] = []
        for rule in self.rules:
            if page_id == rule.primary:
                aliases.extend(rule.aliases)
        return dedupe(aliases)

    def match_text(self, value: str) -> list[RuleMatch]:
        normalized = normalize_text(value)
        if not normalized:
            return []

        matches: list[RuleMatch] = []
        seen: set[tuple[str, str]] = set()
        for alias_norm, alias, rule in self._alias_index:
            if alias_norm == normalized or alias_norm in normalized or normalized in alias_norm:
                key = (rule.id, alias)
                if key not in seen:
                    matches.append(RuleMatch(rule=rule, alias=alias))
                    seen.add(key)
        return matches

    def analyze_snippet(self, snippet: str) -> dict[str, Any]:
        tokens = dedupe(tokenize(snippet))
        normalized = normalize_text(snippet)
        signals = []

        query_strings = extract_query_strings(snippet)
        for query_text in query_strings:
            query_norm = normalize_text(query_text)
            if "выбрать разрешенные" in query_norm:
                signals.append(
                    {
                        "type": "sdbl_keyword",
                        "value": "ВЫБРАТЬ РАЗРЕШЕННЫЕ",
                        "target_ids": ["std415"],
                    }
                )

        for match in self.match_text(snippet):
            signals.append(
                {
                    "type": "rule",
                    "rule": match.rule.id,
                    "value": match.alias,
                    "target_ids": list(match.rule.target_ids),
                }
            )

        return {
            "normalized_text": normalized[:1000],
            "tokens": tokens[:80],
            "signals": signals,
        }


def dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def extract_query_strings(snippet: str) -> list[str]:
    result: list[str] = []
    if "запрос" not in snippet.casefold() and "выбрать" not in snippet.casefold():
        return result

    for match in re.finditer(r'"((?:[^"]|"")*)"', snippet, re.DOTALL):
        text = match.group(1).replace('""', '"')
        if "выбрать" in text.casefold():
            result.append(text)
    return result
