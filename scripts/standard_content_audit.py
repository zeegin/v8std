from __future__ import annotations

import argparse
import json
import hashlib
import re
import time
from collections import Counter
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

try:
    from scripts.atomic_files import atomic_write_text
    from scripts.standard_sources import load_registry
except ModuleNotFoundError:
    from atomic_files import atomic_write_text
    from standard_sources import load_registry


CLAUSE_HEADING_RE = re.compile(
    r"^###### (?P<number>\d+(?:\.\d+)*(?:\.[А-ЯA-Z])?)(?:\.)?"
    r"(?:\s+(?P<title>.*))?$"
)
SECTION_HEADING_RE = re.compile(r"^## (?P<title>.+)$")
ANY_HEADING_RE = re.compile(r"^#{1,6}\s+")
STANDARD_MARKER_RE = re.compile(r"^###### #std(?P<number>\d+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^# (?P<title>.+)$", re.MULTILINE)
ITS_SOURCE_RE = re.compile(r"https://its\.1c\.ru/db/v8std#content:(?P<number>\d+)")
BACKLINK_BLOCK_RE = re.compile(
    r"<!-- diagnostic-backlinks:start.*?<!-- diagnostic-backlinks:end[^>]*-->",
    re.DOTALL,
)
NORMATIVE_RE = re.compile(
    r"\b(?:не\s+)?(?:используйте|делайте|выполняйте|следует|должен|должна|"
    r"должны|нельзя|запрещается|допускается|рекомендуется|можно|включайте|"
    r"пишите|выбирайте|передавайте|применяйте|размещайте)\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:Кб|Мб|Гб|мс|с|мин|%))?\b",
    re.IGNORECASE,
)
SEMANTIC_NUMBER_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:тыс(?:\.|яч[а-я]*)?|млн|Кб|Мб|Гб|"
    r"мс|сек(?:унд[а-я]*)?|мин(?:ут[а-я]*)?|час(?:ов|а)?|дн(?:ей|я)?|%))?\b",
    re.IGNORECASE,
)
NUMERIC_CONTEXT_RE = re.compile(
    r"\b(?:не\s+(?:более|менее)|более|менее|до|от|свыше|превыш\w*|"
    r"миним\w*|максим\w*|интервал\w*|периодич\w*|количеств\w*|"
    r"размер\w*|длин\w*|верс\w*|запис\w*|секунд\w*|минут\w*|"
    r"час\w*|день|дня|дней|процент\w*|пиксел\w*)\b|%|\b(?:Кб|Мб|Гб|мс)\b",
    re.IGNORECASE,
)
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[А-ЯA-ZЁ0-9«])")
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]*")
MARKDOWN_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
SCOPE_PREFIX_RE = re.compile(r"^Область применения\s*:", re.IGNORECASE)
CODE_LINE_RE = re.compile(
    r"^(?://|#|Конец(?:Если|Цикла|Процедуры|Функции|Попытки|Выбора)|"
    r"Иначе\s*;?$|ИначеЕсли\s+.*\s+Тогда\b|Процедура\b|Функция\b|Возврат\b|"
    r"ВЫБРАТЬ\b|ИЗ\b|ГДЕ\b|ПО\s*\(|УПОРЯДОЧИТЬ\b|СГРУППИРОВАТЬ\b|"
    r"ЕСТЬNULL\b|Для\s+.*\s+Цикл\b|Если\s+.*\s+Тогда\b|КОГДА\b|"
    r"ВызватьИсключение\b|\|)",
    re.IGNORECASE,
)
PROHIBIT_RE = re.compile(
    r"\b(?:не\s+(?:следует|долж(?:ен|на|но|ны)|допускается|рекомендуется)|"
    r"нельзя|запрещ\w*|недопуст\w*|не\s+\w+(?:йте|айте|ите))\b",
    re.IGNORECASE,
)
RECOMMEND_RE = re.compile(
    r"\b(?:рекоменду\w*|лучше|целесообразно)\b", re.IGNORECASE
)
ALLOW_RE = re.compile(
    r"\b(?:допуска\w*|допустим\w*|разреш\w*|можно)\b", re.IGNORECASE
)
REQUIRE_RE = re.compile(
    r"\b(?:следует|долж(?:ен|на|но|ны)|необходимо|требуется|надо|нужно|"
    r"используйте|делайте|выполняйте|применяйте|указывайте|выбирайте|"
    r"передавайте|размещайте|пишите|включайте|[а-яё]+(?:йте|ите))\b",
    re.IGNORECASE,
)
CONDITION_RE = re.compile(
    r"\b(?:если|когда|в\s+случае|при\s+условии|только\s+если)\b",
    re.IGNORECASE,
)
EXCEPTION_RE = re.compile(
    r"\b(?:кроме(?!\s+того)|за\s+исключением|в\s+порядке\s+исключения|"
    r"исключение\s+(?:составляют|составляет|—|-)|исключением\s+явля\w*)\b",
    re.IGNORECASE,
)
SOURCE_CLAUSE_RE = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*(?:\.[А-ЯA-Z])?)\."
    r"(?=\s|$)\s*(?P<text>[\s\S]*)$"
)
MAX_SOURCE_BYTES = 8 * 1024 * 1024
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Clause:
    number: str
    section: str
    title: str
    text: str
    normative_terms: tuple[str, ...]
    numeric_terms: tuple[str, ...]


@dataclass(frozen=True)
class LocalStandard:
    standard: str
    title: str
    russian_url: str
    english_url: str | None
    clauses: tuple[Clause, ...]
    source_path: str


@dataclass(frozen=True)
class SourceSnapshot:
    url: str
    fetched_at: str
    status: str
    sha256: str
    title: str
    clauses: tuple[Clause, ...]
    error: str | None


@dataclass(frozen=True)
class StructuralFinding:
    standard: str
    kind: str
    clause: str | None
    source_value: str
    local_value: str
    confidence: str


@dataclass(frozen=True)
class SemanticUnit:
    unit_id: str
    clause: str
    text: str
    weight: int
    numeric_terms: tuple[str, ...]
    modality: str
    has_condition: bool
    has_exception: bool


class _SourceHTMLParser(HTMLParser):
    BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP_TAGS = {"script", "style", "nav", "header", "footer"}

    def __init__(self, language: str) -> None:
        super().__init__(convert_charrefs=True)
        self.language = language
        self.target_depth = 0 if language == "ru" else -1
        self.skip_depth = 0
        self.current_tag: str | None = None
        self.current_text: list[str] = []
        self.blocks: list[tuple[str, str]] = []
        self.iframe_src: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if (
            tag == "iframe"
            and self.language == "ru"
            and attributes.get("id") == "w_metadata_doc_frame"
        ):
            source = attributes.get("src")
            self.iframe_src = (
                quote(source.strip(), safe="/:@?&=+#%") if source else None
            )
        if self.language == "en" and attributes.get("id") == "xwikicontent":
            self.target_depth = 1
            return
        if self.target_depth > 0 and self.language == "en":
            self.target_depth += 1
        if self.target_depth < 0:
            return
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        if self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self._finish_block()
            self.current_tag = tag
        if self.skip_depth == 0 and tag == "br":
            self.current_text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.target_depth < 0:
            return
        if self.skip_depth == 0 and tag == self.current_tag:
            self._finish_block()
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if self.language == "en" and self.target_depth > 0:
            self.target_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.target_depth >= 0 and self.skip_depth == 0 and self.current_tag:
            self.current_text.append(data)

    def close(self) -> None:
        super().close()
        self._finish_block()

    def _finish_block(self) -> None:
        if self.current_tag is not None:
            text = re.sub(r"[ \t\r\f\v]+", " ", "".join(self.current_text))
            text = re.sub(r"\s*\n\s*", "\n", text).strip()
            if text:
                self.blocks.append((self.current_tag, text))
        self.current_tag = None
        self.current_text = []


def canonical_russian_url(standard: str) -> str:
    if not re.fullmatch(r"std\d+", standard):
        raise ValueError(f"invalid standard id: {standard}")
    return f"https://its.1c.ru/db/v8std/content/{standard[3:]}/hdoc"


def _charset(headers: Any) -> str:
    content_type = headers.get("Content-Type", "") if headers is not None else ""
    match = re.search(r"charset=([^;\s]+)", content_type, re.IGNORECASE)
    return match.group(1).strip('"') if match else "utf-8"


def _open_bytes(
    url: str, opener: Callable[..., Any]
) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "v8std-local-audit/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with opener(request, timeout=30) as response:
                body = response.read(MAX_SOURCE_BYTES + 1)
                if len(body) > MAX_SOURCE_BYTES:
                    raise ValueError(f"source response exceeds {MAX_SOURCE_BYTES} bytes")
                return body, _charset(response.headers)
        except HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES or attempt == 2:
                break
        except URLError as error:
            last_error = error
            if attempt == 2:
                break
        time.sleep(0.2 * (2**attempt))
    assert last_error is not None
    raise last_error


def _source_clauses(blocks: list[tuple[str, str]]) -> tuple[Clause, ...]:
    clauses: list[Clause] = []
    preamble: list[str] = []
    current_number: str | None = None
    current_lines: list[str] = []

    def finish() -> None:
        nonlocal current_number, current_lines
        if current_number is not None:
            clauses.append(
                _clause_from_lines(current_number, "", "", current_lines)
            )
        current_number = None
        current_lines = []

    expanded_blocks: list[tuple[str, str]] = []
    inline_clause_re = re.compile(
        r"\n(?=\d+(?:\.\d+)*(?:\.[А-ЯA-Z])?\.(?=\s|$)\s*)"
    )
    for tag, text in blocks:
        expanded_blocks.extend((tag, part) for part in inline_clause_re.split(text))

    for tag, text in expanded_blocks:
        if tag in {"h2", "h3", "h4", "h5", "h6"} and text.casefold() in {
            "см. также",
            "see also",
        }:
            break
        if tag == "h1":
            continue
        match = SOURCE_CLAUSE_RE.match(text)
        if match is not None:
            if current_number is None and not clauses and preamble:
                clauses.append(_clause_from_lines("", "", "", preamble))
                preamble = []
            finish()
            current_number = match.group("number")
            current_lines = [match.group("text")]
        elif current_number is not None:
            current_lines.append(text)
        elif tag not in {"h2", "h3", "h4", "h5", "h6"}:
            preamble.append(text)
    finish()
    if not clauses and preamble:
        clauses.append(_clause_from_lines("", "", "", preamble))
    return tuple(clauses)


def _parse_source_html(body: bytes, charset: str, language: str) -> tuple[str, tuple[Clause, ...], str | None]:
    text = body.decode(charset, errors="replace")
    parser = _SourceHTMLParser(language)
    parser.feed(text)
    parser.close()
    h1 = next((value for tag, value in parser.blocks if tag == "h1"), "")
    if language == "en" and not h1:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
        title = unescape(title_match.group(1)).strip() if title_match else ""
        h1 = re.sub(r"\s+-\s+XWiki$", "", title)
    return h1, _source_clauses(parser.blocks), parser.iframe_src


def fetch_snapshot(
    url: str,
    language: str,
    opener: Callable[..., Any] = urlopen,
) -> SourceSnapshot:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        body, charset = _open_bytes(url, opener)
        title, clauses, iframe_src = _parse_source_html(body, charset, language)
        if language == "ru" and iframe_src:
            inner_url = urljoin(url, iframe_src)
            body, charset = _open_bytes(inner_url, opener)
            title, clauses, _unused = _parse_source_html(body, charset, language)
        if language == "ru" and not clauses:
            raise ValueError("Russian source contains no numbered clauses")
        return SourceSnapshot(
            url=url,
            fetched_at=fetched_at,
            status="fetched",
            sha256=hashlib.sha256(body).hexdigest(),
            title=title,
            clauses=clauses,
            error=None,
        )
    except (HTTPError, URLError, UnicodeError, ValueError) as error:
        return SourceSnapshot(
            url=url,
            fetched_at=fetched_at,
            status="unavailable",
            sha256="",
            title="",
            clauses=(),
            error=str(error),
        )


def _signal_key(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold().replace(",", ".")


def _excerpt(value: str, limit: int = 280) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def _semantic_modality(text: str) -> str:
    if PROHIBIT_RE.search(text):
        return "prohibit"
    if RECOMMEND_RE.search(text):
        return "recommend"
    if ALLOW_RE.search(text):
        return "allow"
    if REQUIRE_RE.search(text):
        return "require"
    return "neutral"


def _normalized_numbers(text: str) -> tuple[str, ...]:
    without_references = re.sub(
        r"\b(?:п\.|пункт(?:а|е|ом)?|стандарт(?:а|е|ом)?)\s*\d+(?:\.\d+)*",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    if not NUMERIC_CONTEXT_RE.search(without_references):
        return ()
    normalized: set[str] = set()
    for match in SEMANTIC_NUMBER_RE.finditer(without_references):
        raw = re.sub(r"\s+", "", match.group(0)).casefold().replace(",", ".")
        scale = 1
        if re.search(r"тыс", raw):
            scale = 1_000
        elif "млн" in raw:
            scale = 1_000_000
        number_match = re.match(r"\d+(?:\.\d+)?", raw)
        assert number_match is not None
        suffix = raw[number_match.end() :]
        suffix = re.sub(r"^(?:тыс(?:\.|яч[а-я]*)?|млн)", "", suffix)
        value = float(number_match.group(0)) * scale
        numeric = str(int(value)) if value.is_integer() else str(value)
        normalized.add(numeric + suffix)
    return tuple(sorted(normalized))


def _looks_like_code_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped or CODE_LINE_RE.search(stripped):
        return True
    if re.match(r"^\[\d{1,4}[./-]\d{1,2}[./-]\d{1,4}\s+\d{1,2}:\d{2}", stripped):
        return True
    if stripped.endswith((";", "Тогда")) and (
        "=" in stripped or ">" in stripped or "<" in stripped
    ):
        return True
    if re.search(r"\w+\([^)]*\)\s*;?$", stripped) and len(WORD_RE.findall(stripped)) < 5:
        return True
    if re.search(r"\bКАК\b", stripped) and not re.search(r"[.!?;:]$", stripped):
        return True
    if sum(character in "=|<>" for character in stripped) >= 2:
        return True
    if stripped.endswith(('";', '");')):
        return True
    return False


def _semantic_paragraphs(text: str, markup: str) -> list[str]:
    if markup not in {"source", "markdown"}:
        raise ValueError(f"unsupported semantic markup: {markup}")
    cleaned = HTML_COMMENT_RE.sub(" ", text)
    if markup == "markdown":
        cleaned = MARKDOWN_CODE_RE.sub(" ", cleaned)
        cleaned = re.sub(r"`#!\w+\s+([^`]+)`", r"`\1`", cleaned)
        cleaned = cleaned.replace("`", "")
        cleaned = re.sub(r"!\[[^]]*]\([^)]*\)(?:\{[^}]*\})?", " ", cleaned)
        cleaned = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", cleaned)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        raw_paragraphs = re.split(r"\n\s*\n", cleaned)
        paragraphs: list[str] = []
        for paragraph in raw_paragraphs:
            groups: list[list[str]] = []
            current: list[str] = []
            for line in paragraph.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("!!!"):
                    continue
                bullet = re.match(r"^[-*+]\s+(.*)$", stripped)
                if bullet:
                    if current:
                        groups.append(current)
                    current = [bullet.group(1)]
                else:
                    current.append(stripped)
            if current:
                groups.append(current)
            paragraphs.extend(" ".join(group) for group in groups if group)
        return paragraphs
    return [line.strip() for line in cleaned.splitlines() if line.strip()]


def extract_semantic_units(
    clauses: tuple[Clause, ...], *, markup: str
) -> tuple[SemanticUnit, ...]:
    units: list[SemanticUnit] = []
    for clause in clauses:
        index = 0
        for paragraph in _semantic_paragraphs(clause.text, markup):
            paragraph = re.sub(r"^[-*+]\s+", "", paragraph).strip()
            if re.match(
                r"^(?:Дополнительная информация \(ИТС\)|См\.\s+также)\s*:?$",
                paragraph,
                re.IGNORECASE,
            ):
                break
            if SCOPE_PREFIX_RE.search(paragraph):
                continue
            if paragraph.casefold().rstrip(":") in {
                "правильно",
                "неправильно",
                "пример",
                "например",
                "методическая рекомендация (полезный совет)",
                "рекомендация (полезный совет)",
                "дополнительная информация (итс)",
            }:
                continue
            paragraph = re.sub(
                r"\bп\.\s*(?=\d+(?:\.\d+)*)",
                "пункт ",
                paragraph,
                flags=re.IGNORECASE,
            )
            for sentence in SENTENCE_BOUNDARY_RE.split(paragraph):
                sentence = re.sub(r"\s+", " ", sentence).strip(" -–—•\t")
                if markup == "source":
                    sentence = re.sub(
                        r"^\d+(?:\.\d+)*[.)]?\s+(?=[А-ЯЁ])",
                        "",
                        sentence,
                    )
                if re.match(r"^см\.\s+также\b", sentence, re.IGNORECASE):
                    continue
                is_numeric_conditional_example = bool(
                    re.match(r"^например\b", sentence, re.IGNORECASE)
                    and SEMANTIC_NUMBER_RE.search(sentence)
                    and CONDITION_RE.search(sentence)
                )
                if (
                    re.match(r"^например\b", sentence, re.IGNORECASE)
                    and not is_numeric_conditional_example
                ):
                    continue
                if _looks_like_code_line(sentence):
                    continue
                if len(sentence) < 12 or len(WORD_RE.findall(sentence)) < 3:
                    continue
                index += 1
                numeric_terms = _normalized_numbers(sentence)
                modality = _semantic_modality(sentence)
                has_condition = bool(CONDITION_RE.search(sentence))
                has_exception = bool(EXCEPTION_RE.search(sentence))
                if (
                    markup == "source"
                    and modality == "neutral"
                    and not numeric_terms
                    and not has_condition
                    and not has_exception
                    and len(WORD_RE.findall(sentence)) <= 5
                    and not re.search(r"[.!?;:]$|[—–]", sentence)
                ):
                    continue
                weight = min(
                    4,
                    1
                    + int(bool(numeric_terms))
                    + int(modality != "neutral")
                    + int(has_condition or has_exception),
                )
                units.append(
                    SemanticUnit(
                        unit_id=f"{clause.number or 'preamble'}:{index}",
                        clause=clause.number,
                        text=sentence,
                        weight=weight,
                        numeric_terms=numeric_terms,
                        modality=modality,
                        has_condition=has_condition,
                        has_exception=has_exception,
                    )
                )
    return tuple(units)


def semantic_unit_windows(
    units: tuple[SemanticUnit, ...], *, max_size: int = 3
) -> tuple[SemanticUnit, ...]:
    windows: list[SemanticUnit] = list(units)
    for start in range(len(units)):
        for size in range(2, max_size + 1):
            group = units[start : start + size]
            if len(group) != size or len({unit.clause for unit in group}) != 1:
                continue
            modalities = {unit.modality for unit in group if unit.modality != "neutral"}
            windows.append(
                SemanticUnit(
                    unit_id=f"{group[0].unit_id}..{group[-1].unit_id}",
                    clause=group[0].clause,
                    text=" ".join(unit.text for unit in group),
                    weight=sum(unit.weight for unit in group),
                    numeric_terms=tuple(
                        sorted({term for unit in group for term in unit.numeric_terms})
                    ),
                    modality=next(iter(modalities)) if len(modalities) == 1 else "mixed",
                    has_condition=any(unit.has_condition for unit in group),
                    has_exception=any(unit.has_exception for unit in group),
                )
            )
    return tuple(windows)


def semantic_local_clauses(standard: LocalStandard) -> tuple[Clause, ...]:
    content = Path(standard.source_path).read_text(encoding="utf-8")
    title = _single_match(TITLE_RE, content, "H1 title")
    body = content[title.end() :]
    body = re.split(
        r"^###### (?:См\. также|Источник(?:и)?)\s*$",
        body,
        maxsplit=1,
        flags=re.MULTILINE,
    )[0]
    preamble_lines: list[str] = []
    for line in body.splitlines():
        if CLAUSE_HEADING_RE.match(line):
            break
        if line.startswith("#"):
            continue
        preamble_lines.append(line)
    preamble_text = "\n".join(preamble_lines).strip()
    clauses: list[Clause] = []
    if preamble_text:
        clauses.append(_clause_from_lines("", "", "", [preamble_text]))
    clauses.extend(standard.clauses)
    return tuple(clauses)


def compare_semantic_units(
    source_units: tuple[SemanticUnit, ...],
    local_units: tuple[SemanticUnit, ...],
    similarities: list[list[float]],
    *,
    preserved_threshold: float = 0.76,
) -> list[dict[str, Any]]:
    if len(similarities) != len(source_units) or any(
        len(row) != len(local_units) for row in similarities
    ):
        raise ValueError("semantic similarity matrix shape mismatch")
    comparisons: list[dict[str, Any]] = []
    for source_index, source in enumerate(source_units):
        if not local_units:
            comparisons.append(
                {
                    "source_unit": asdict(source),
                    "local_unit": None,
                    "similarity": 0.0,
                    "weight": source.weight,
                    "status": "needs_review",
                    "reasons": ["missing_local_meaning"],
                    "decision": None,
                }
            )
            continue
        ranked = [
            (
                float(similarities[source_index][local_index])
                + (
                    0.20
                    * len(set(source.numeric_terms) & set(local.numeric_terms))
                    / len(source.numeric_terms)
                    if source.numeric_terms
                    else 0.0
                )
                + (
                    0.05
                    if source.modality != "neutral"
                    and source.modality == local.modality
                    else 0.0
                ),
                float(similarities[source_index][local_index]),
                local.clause == source.clause,
                local_index,
            )
            for local_index, local in enumerate(local_units)
        ]
        _rank, similarity, _same_clause, local_index = max(ranked)
        local = local_units[local_index]
        reasons: list[str] = []
        if source.numeric_terms and not set(source.numeric_terms).issubset(
            set(local.numeric_terms)
        ):
            reasons.append("numeric_constraint_changed")
        if source.modality != "neutral" and source.modality != local.modality:
            reasons.append("modality_changed")
        if source.has_condition and not local.has_condition and similarity < 0.82:
            reasons.append("condition_changed")
        if source.has_exception and not local.has_exception and similarity < 0.82:
            reasons.append("exception_changed")
        if similarity < preserved_threshold:
            reasons.append("low_semantic_similarity")
        comparisons.append(
            {
                "source_unit": asdict(source),
                "local_unit": asdict(local),
                "similarity": round(similarity, 4),
                "weight": source.weight,
                "status": "needs_review" if reasons else "preserved",
                "reasons": reasons,
                "decision": "preserved" if not reasons else None,
            }
        )
    return comparisons


def semantic_difference_percent(comparisons: list[dict[str, Any]]) -> float:
    total_weight = sum(int(item["weight"]) for item in comparisons)
    if total_weight == 0:
        return 0.0
    changed_weight = sum(
        int(item["weight"])
        for item in comparisons
        if item.get("decision") == "changed"
    )
    return round(100 * changed_weight / total_weight, 1)


def decide_semantic_comparison(
    comparison: dict[str, Any], nli: dict[str, float]
) -> dict[str, Any]:
    decided = dict(comparison)
    decided["nli"] = {key: round(float(value), 4) for key, value in nli.items()}
    reasons = set(comparison.get("reasons", []))
    entailment = float(nli["entailment"])
    contradiction = float(nli["contradiction"])
    similarity = float(comparison.get("similarity", 0.0))
    source_unit = comparison.get("source_unit") or {}
    source_modality = source_unit.get("modality", "neutral")
    source_conditional = bool(
        source_unit.get("has_condition") or source_unit.get("has_exception")
    )
    if "missing_local_meaning" in reasons:
        decision, confidence, basis = "changed", "high", "missing_local_meaning"
    elif "numeric_constraint_changed" in reasons and entailment < 0.50:
        decision, confidence, basis = "changed", "high", "numeric_constraint"
    elif similarity < 0.45 and entailment < 0.10 and source_modality != "neutral":
        decision, confidence, basis = "changed", "high", "unmatched_meaning"
    elif similarity < 0.35 and entailment < 0.05 and source_conditional:
        decision, confidence, basis = "changed", "high", "unmatched_condition"
    elif entailment >= 0.80 and "numeric_constraint_changed" not in reasons:
        decision, confidence, basis = "preserved", "high", "nli_entailment"
    else:
        decision, confidence, basis = None, "needs_review", "ambiguous"
    decided["decision"] = decision
    decided["decision_confidence"] = confidence
    decided["decision_basis"] = basis
    return decided


def generate_semantic_audit(
    standards: list[LocalStandard],
    cache_dir: Path,
    *,
    sentence_model_path: Path,
    nli_model_path: Path,
    batch_size: int = 32,
) -> dict[str, Any]:
    try:
        import torch
        from sentence_transformers import SentenceTransformer
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as error:
        raise RuntimeError(
            "semantic audit requires sentence-transformers, transformers and torch"
        ) from error

    sentence_model = SentenceTransformer(
        str(sentence_model_path), local_files_only=True
    )
    tokenizer = AutoTokenizer.from_pretrained(
        str(nli_model_path), local_files_only=True
    )
    nli_model = AutoModelForSequenceClassification.from_pretrained(
        str(nli_model_path), local_files_only=True
    )
    nli_model.eval()
    label_ids = nli_model.config.label2id
    required_labels = {"entailment", "neutral", "contradiction"}
    if set(label_ids) != required_labels:
        raise ValueError(f"unexpected NLI labels: {sorted(label_ids)}")

    manifest = json.loads(
        (cache_dir / "manifest.json").read_text(encoding="utf-8")
    )
    source_records = {item["standard"]: item for item in manifest["standards"]}
    records: list[dict[str, Any]] = []
    for position, standard in enumerate(standards, start=1):
        russian = _load_source_snapshot(
            cache_dir / "sources" / f"ru-{standard.standard[3:]}.json"
        )
        source_units = extract_semantic_units(russian.clauses, markup="source")
        local_base_units = extract_semantic_units(
            semantic_local_clauses(standard), markup="markdown"
        )
        local_units = semantic_unit_windows(local_base_units)
        embeddings = sentence_model.encode(
            [unit.text for unit in source_units + local_units],
            batch_size=max(1, batch_size),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        source_embeddings = embeddings[: len(source_units)]
        local_embeddings = embeddings[len(source_units) :]
        similarities = (source_embeddings @ local_embeddings.T).tolist()
        comparisons = compare_semantic_units(
            source_units, local_units, similarities
        )

        candidate_indexes = [
            index
            for index, comparison in enumerate(comparisons)
            if comparison["status"] == "needs_review"
            and comparison["local_unit"] is not None
        ]
        for offset in range(0, len(candidate_indexes), max(1, batch_size)):
            indexes = candidate_indexes[offset : offset + max(1, batch_size)]
            premises = [comparisons[index]["local_unit"]["text"] for index in indexes]
            hypotheses = [comparisons[index]["source_unit"]["text"] for index in indexes]
            encoded = tokenizer(
                premises,
                hypotheses,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with torch.inference_mode():
                probabilities = torch.softmax(nli_model(**encoded).logits, dim=-1)
            for index, probability in zip(indexes, probabilities):
                nli = {
                    label: float(probability[label_ids[label]])
                    for label in required_labels
                }
                comparisons[index] = decide_semantic_comparison(
                    comparisons[index], nli
                )

        for index, comparison in enumerate(comparisons):
            if comparison["local_unit"] is None:
                comparisons[index] = decide_semantic_comparison(
                    comparison,
                    {"entailment": 0.0, "neutral": 1.0, "contradiction": 0.0},
                )
            elif comparison["status"] == "preserved":
                comparison["decision_confidence"] = "high"
                comparison["decision_basis"] = "embedding_and_anchors"
                comparison["nli"] = None

        total_weight = sum(item["weight"] for item in comparisons)
        changed = [item for item in comparisons if item["decision"] == "changed"]
        unresolved = [item for item in comparisons if item["decision"] is None]
        changed_weight = sum(item["weight"] for item in changed)
        unresolved_weight = sum(item["weight"] for item in unresolved)
        lower_bound = round(100 * changed_weight / total_weight, 1) if total_weight else 0.0
        unresolved_percent = (
            round(100 * unresolved_weight / total_weight, 1) if total_weight else 0.0
        )
        english: SourceSnapshot | None = None
        source_record = source_records[standard.standard]
        if source_record["english"]["status"] == "fetched":
            english = _load_source_snapshot(
                cache_dir / "sources" / f"en-{standard.standard[3:]}.json"
            )
        changed_units: list[dict[str, Any]] = []
        for item in changed:
            clause = item["source_unit"]["clause"]
            changed_units.append(
                {
                    "unit_id": item["source_unit"]["unit_id"],
                    "clause": clause,
                    "weight": item["weight"],
                    "source_text": item["source_unit"]["text"],
                    "local_text": item["local_unit"]["text"] if item["local_unit"] else None,
                    "english_text": _clause_evidence(english.clauses, clause)
                    if english
                    else None,
                    "similarity": item["similarity"],
                    "reasons": item["reasons"],
                    "nli": item.get("nli"),
                    "basis": item["decision_basis"],
                }
            )
        records.append(
            {
                "standard": standard.standard,
                "title": standard.title,
                "total_units": len(comparisons),
                "total_weight": total_weight,
                "preserved_units": sum(
                    item["decision"] == "preserved" for item in comparisons
                ),
                "changed_units_count": len(changed),
                "unresolved_units": len(unresolved),
                "difference_lower_bound_percent": lower_bound,
                "unresolved_percent": unresolved_percent,
                "status": (
                    "смысл отличается >5%"
                    if lower_bound > 5.0
                    else "расхождение >5% не подтверждено"
                ),
                "confidence": "high" if lower_bound > 5.0 else "limited",
                "changed_units": changed_units,
            }
        )
        print(
            f"semantic {position}/{len(standards)} {standard.standard}: "
            f">5={lower_bound > 5.0} lower={lower_bound}% unresolved={unresolved_percent}%"
        )
    return {
        "version": 1,
        "audit_at": manifest["audit_at"],
        "threshold_percent": 5.0,
        "metric": {
            "name": "weighted_confirmed_semantic_loss_lower_bound",
            "denominator": "weighted Russian ITS semantic units",
            "weights": "base 1; +1 numeric; +1 modality; +1 condition or exception; max 4",
            "rule": "changed high-confidence weight / total source weight * 100",
        },
        "models": {
            "sentence": sentence_model_path.name,
            "nli": nli_model_path.name,
        },
        "standards": records,
    }


def apply_manual_semantic_review(
    semantic: dict[str, Any], decisions: dict[str, Any]
) -> dict[str, Any]:
    threshold = float(semantic.get("threshold_percent", 5.0))
    decision_records = decisions.get("standards")
    if not isinstance(decision_records, dict):
        raise ValueError("manual semantic decisions must contain a standards object")
    candidates = {
        item["standard"]
        for item in semantic["standards"]
        if float(item["difference_lower_bound_percent"]) > threshold
    }
    missing = sorted(candidates - set(decision_records))
    if missing:
        raise ValueError("missing manual decisions: " + ", ".join(missing))

    reviewed_standards: list[dict[str, Any]] = []
    for item in semantic["standards"]:
        reviewed = dict(item)
        reviewed["automatic_difference_lower_bound_percent"] = item[
            "difference_lower_bound_percent"
        ]
        reviewed["automatic_changed_units"] = item.get("changed_units", [])
        decision = decision_records.get(item["standard"])
        if decision is None:
            reviewed.update(
                {
                    "manual_reviewed": False,
                    "manual_difference_percent": None,
                    "semantic_status": "порог >5% автоматически не выявлен",
                    "review_conclusion": None,
                    "confirmed_units": [],
                    "dismissed_units": [],
                }
            )
            reviewed_standards.append(reviewed)
            continue

        selected_ids = decision.get("confirmed_unit_ids", [])
        if not isinstance(selected_ids, list) or len(selected_ids) != len(
            set(selected_ids)
        ):
            raise ValueError(f"invalid confirmed unit ids: {item['standard']}")
        units_by_id = {
            unit["unit_id"]: unit for unit in item.get("changed_units", [])
        }
        unknown = sorted(set(selected_ids) - set(units_by_id))
        if unknown:
            raise ValueError(
                f"unknown confirmed unit ids for {item['standard']}: "
                + ", ".join(unknown)
            )
        evidence_overrides = decision.get("evidence_overrides", {})
        if not isinstance(evidence_overrides, dict) or (
            set(evidence_overrides) - set(selected_ids)
        ):
            raise ValueError(f"invalid evidence overrides: {item['standard']}")
        confirmed_units: list[dict[str, Any]] = []
        for unit_id in selected_ids:
            evidence_override = evidence_overrides.get(unit_id, {})
            if not isinstance(evidence_override, dict) or (
                set(evidence_override) - {"source_text", "local_text", "english_text"}
            ):
                raise ValueError(f"invalid evidence override: {item['standard']}")
            confirmed_units.append({**units_by_id[unit_id], **evidence_override})
        confirmed_weight = sum(int(unit["weight"]) for unit in confirmed_units)
        total_weight = int(item["total_weight"])
        manual_percent = (
            round(100 * confirmed_weight / total_weight, 1) if total_weight else 0.0
        )
        manual_decision = decision.get("decision")
        if manual_decision not in {"confirmed_gt_5", "not_confirmed"}:
            raise ValueError(f"invalid manual decision: {item['standard']}")
        if manual_decision == "confirmed_gt_5" and manual_percent <= threshold:
            raise ValueError(
                f"confirmed percentage does not exceed threshold: {item['standard']}"
            )
        if manual_decision == "not_confirmed" and selected_ids:
            raise ValueError(
                f"not-confirmed decision selects units: {item['standard']}"
            )
        reviewed.update(
            {
                "manual_reviewed": True,
                "manual_difference_percent": manual_percent,
                "semantic_status": (
                    "смысл отличается >5%"
                    if manual_decision == "confirmed_gt_5"
                    else "порог >5% не подтверждён вручную"
                ),
                "review_conclusion": str(decision.get("conclusion", "")).strip(),
                "confirmed_units": confirmed_units,
                "dismissed_units": [
                    unit
                    for unit_id, unit in units_by_id.items()
                    if unit_id not in selected_ids
                ],
            }
        )
        reviewed_standards.append(reviewed)

    return {
        **semantic,
        "version": 2,
        "manual_review": {
            "method": decisions.get("method", "manual candidate adjudication"),
            "reviewed_candidates": len(candidates),
        },
        "standards": reviewed_standards,
    }


def compare_structure(
    local: LocalStandard, russian: SourceSnapshot
) -> list[StructuralFinding]:
    if russian.status != "fetched":
        return [
            StructuralFinding(
                local.standard,
                "source_unavailable",
                None,
                russian.error or russian.status,
                "",
                "high",
            )
        ]

    source_numbers = [clause.number for clause in russian.clauses if clause.number]
    local_numbers = [clause.number for clause in local.clauses if clause.number]
    if not source_numbers and local_numbers:
        return [
            StructuralFinding(
                local.standard,
                "source_unnumbered_local_numbered",
                None,
                _excerpt(russian.clauses[0].text),
                ", ".join(local_numbers),
                "high",
            )
        ]

    findings: list[StructuralFinding] = []
    if source_numbers != local_numbers:
        findings.append(
            StructuralFinding(
                local.standard,
                "numbering_sequence",
                None,
                ", ".join(source_numbers),
                ", ".join(local_numbers),
                "high",
            )
        )
        source_counts = Counter(source_numbers)
        local_counts = Counter(local_numbers)
        for number in sorted(source_counts.keys() | local_counts.keys()):
            for _index in range(max(0, source_counts[number] - local_counts[number])):
                findings.append(
                    StructuralFinding(
                        local.standard,
                        "missing_clause",
                        number,
                        _excerpt(
                            next(
                                clause.text
                                for clause in russian.clauses
                                if clause.number == number
                            )
                        ),
                        "",
                        "high",
                    )
                )
            for _index in range(max(0, local_counts[number] - source_counts[number])):
                findings.append(
                    StructuralFinding(
                        local.standard,
                        "extra_clause",
                        number,
                        "",
                        _excerpt(
                            next(
                                clause.text
                                for clause in local.clauses
                                if clause.number == number
                            )
                        ),
                        "high",
                    )
                )

    source_by_number: dict[str, list[Clause]] = {}
    local_by_number: dict[str, list[Clause]] = {}
    for clause in russian.clauses:
        if clause.number:
            source_by_number.setdefault(clause.number, []).append(clause)
    for clause in local.clauses:
        if clause.number:
            local_by_number.setdefault(clause.number, []).append(clause)
    for number in sorted(source_by_number.keys() & local_by_number.keys()):
        for source_clause, local_clause in zip(
            source_by_number[number], local_by_number[number]
        ):
            if source_clause.normative_terms and not local_clause.normative_terms:
                findings.append(
                    StructuralFinding(
                        local.standard,
                        "normative_signal_changed",
                        number,
                        _excerpt(source_clause.text),
                        _excerpt(local_clause.text),
                        "needs_review",
                    )
                )
            local_numeric = {_signal_key(value) for value in local_clause.numeric_terms}
            for value in source_clause.numeric_terms:
                if _signal_key(value) not in local_numeric:
                    findings.append(
                        StructuralFinding(
                            local.standard,
                            "numeric_term_missing",
                            number,
                            _excerpt(source_clause.text),
                            _excerpt(local_clause.text),
                            "needs_review",
                        )
                    )
    return findings


def _load_source_snapshot(path: Path) -> SourceSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["clauses"] = tuple(Clause(**item) for item in payload["clauses"])
    return SourceSnapshot(**payload)


def generate_structural_findings(
    standards: list[LocalStandard], cache_dir: Path
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for standard in standards:
        source_path = cache_dir / "sources" / f"ru-{standard.standard[3:]}.json"
        russian = _load_source_snapshot(source_path)
        findings = compare_structure(standard, russian)
        numbering_kinds = {
            "source_unnumbered_local_numbered",
            "numbering_sequence",
            "missing_clause",
            "extra_clause",
        }
        records.append(
            {
                "standard": standard.standard,
                "title": standard.title,
                "numbering_status": (
                    "изменена нумерация"
                    if any(item.kind in numbering_kinds for item in findings)
                    else "совпадает"
                ),
                "local_numbers": [
                    clause.number for clause in standard.clauses if clause.number
                ],
                "russian_numbers": [
                    clause.number for clause in russian.clauses if clause.number
                ],
                "findings": [asdict(item) for item in findings],
            }
        )
    return {"version": 1, "standards": records}


FINDING_EXPLANATIONS = {
    "source_unnumbered_local_numbered": (
        "Русская статья ИТС не нумерует требования, но локальная адаптация "
        "вводит собственную нумерацию."
    ),
    "numbering_sequence": (
        "Последовательность номеров локальной страницы отличается от русской ИТС."
    ),
    "missing_clause": "Пункт русской ИТС отсутствует под тем же номером локально.",
    "extra_clause": "Локальный номер отсутствует в русской ИТС.",
    "normative_signal_changed": (
        "Нормативный маркер источника не найден в локальном пункте; требуется "
        "проверить возможный эквивалентный пересказ."
    ),
    "numeric_term_missing": (
        "Число или ограничение источника не найдено буквально в локальном пункте; "
        "требуется контекстная проверка."
    ),
    "source_unavailable": "Русский источник недоступен для проверки.",
}
CONFIRMED_NUMBERING_KINDS = {
    "source_unnumbered_local_numbered",
    "numbering_sequence",
    "missing_clause",
    "extra_clause",
}


def _clause_evidence(clauses: tuple[Clause, ...], number: str | None) -> str | None:
    if number is None:
        return _excerpt(clauses[0].text) if clauses else None
    return next(
        (_excerpt(clause.text) for clause in clauses if clause.number == number),
        None,
    )


def build_review_ledger(
    standards: list[LocalStandard],
    cache_dir: Path,
    manifest: dict[str, Any],
    structural: dict[str, Any],
    semantic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_by_id = {item["standard"]: item for item in manifest["standards"]}
    structural_by_id = {
        item["standard"]: item for item in structural["standards"]
    }
    semantic_by_id = (
        {item["standard"]: item for item in semantic["standards"]}
        if semantic
        else {}
    )
    reviews: list[dict[str, Any]] = []
    for standard in standards:
        source_record = manifest_by_id[standard.standard]
        russian = _load_source_snapshot(
            cache_dir / "sources" / f"ru-{standard.standard[3:]}.json"
        )
        english: SourceSnapshot | None = None
        if source_record["english"]["status"] == "fetched":
            english = _load_source_snapshot(
                cache_dir / "sources" / f"en-{standard.standard[3:]}.json"
            )
        structural_record = structural_by_id[standard.standard]
        observations: list[dict[str, Any]] = []
        for finding in structural_record["findings"]:
            kind = finding["kind"]
            clause = finding["clause"]
            confirmed = kind in CONFIRMED_NUMBERING_KINDS
            russian_evidence = finding["source_value"] or _clause_evidence(
                russian.clauses, clause
            )
            local_evidence = finding["local_value"] or _clause_evidence(
                standard.clauses, clause
            )
            if confirmed and not russian_evidence:
                russian_evidence = "[пункт отсутствует]"
            if confirmed and not local_evidence:
                local_evidence = "[пункт отсутствует]"
            observations.append(
                {
                    "kind": kind,
                    "clause": clause,
                    "russian_evidence": russian_evidence,
                    "local_evidence": local_evidence,
                    "english_evidence": (
                        _clause_evidence(english.clauses, clause) if english else None
                    ),
                    "explanation": FINDING_EXPLANATIONS[kind],
                    "confidence": "high" if confirmed else "needs_review",
                    "confirmed": confirmed,
                }
            )

        russian_numbers = [clause.number for clause in russian.clauses if clause.number]
        english_numbers = (
            [clause.number for clause in english.clauses if clause.number]
            if english
            else None
        )
        if english_numbers is not None and russian_numbers != english_numbers:
            observations.append(
                {
                    "kind": "official_source_structure_difference",
                    "clause": None,
                    "russian_evidence": ", ".join(russian_numbers) or "без нумерации",
                    "local_evidence": ", ".join(
                        clause.number for clause in standard.clauses if clause.number
                    )
                    or "без нумерации",
                    "english_evidence": ", ".join(english_numbers) or "без нумерации",
                    "explanation": (
                        "Структура русской и английской официальных статей различается. "
                        "Это сигнал расхождения редакций, а не автоматически дефект сайта."
                    ),
                    "confidence": "needs_review",
                    "confirmed": False,
                }
            )

        numbering_changed = structural_record["numbering_status"] == "изменена нумерация"
        semantic_record = semantic_by_id.get(standard.standard)
        semantic_status = (
            semantic_record["semantic_status"]
            if semantic_record
            else "смысл не проверен"
        )
        if semantic_record:
            for unit in semantic_record["confirmed_units"]:
                observations.append(
                    {
                        "kind": "semantic_loss_gt_5",
                        "clause": unit.get("clause"),
                        "russian_evidence": unit.get("source_text"),
                        "local_evidence": unit.get("local_text"),
                        "english_evidence": unit.get("english_text"),
                        "explanation": semantic_record["review_conclusion"],
                        "confidence": "high",
                        "confirmed": True,
                    }
                )
        if semantic_status == "смысл отличается >5%":
            status = semantic_status
        elif numbering_changed:
            status = "изменена нумерация"
        elif semantic_record and semantic_record["manual_reviewed"]:
            status = "порог >5% не подтверждён вручную"
        elif semantic_record:
            status = "порог >5% автоматически не выявлен"
        else:
            status = "нужна ручная проверка"
        reviews.append(
            {
                "standard": standard.standard,
                "title": standard.title,
                "status": status,
                "confidence": (
                    "high"
                    if numbering_changed or semantic_status == "смысл отличается >5%"
                    else "limited"
                ),
                "numbering_status": structural_record["numbering_status"],
                "semantic_status": semantic_status,
                "semantic_difference_percent": (
                    semantic_record["manual_difference_percent"]
                    if semantic_record
                    and semantic_record["manual_difference_percent"] is not None
                    else semantic_record["automatic_difference_lower_bound_percent"]
                    if semantic_record
                    else None
                ),
                "semantic_automatic_percent": (
                    semantic_record["automatic_difference_lower_bound_percent"]
                    if semantic_record
                    else None
                ),
                "semantic_unresolved_percent": (
                    semantic_record["unresolved_percent"] if semantic_record else None
                ),
                "semantic_conclusion": (
                    semantic_record["review_conclusion"] if semantic_record else None
                ),
                "russian_status": source_record["russian"]["status"],
                "english_status": source_record["english"]["status"],
                "checked_clauses": [clause.number for clause in standard.clauses],
                "observations": observations,
            }
        )
    return {
        "version": 1,
        "audit_at": manifest["audit_at"],
        "reviews": reviews,
    }


def validate_review_ledger(
    standards: list[LocalStandard], ledger: dict[str, Any]
) -> None:
    reviews = ledger.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("reviews must be an array")
    expected_ids = [standard.standard for standard in standards]
    review_ids = [review.get("standard") for review in reviews]
    if review_ids != expected_ids or len(set(review_ids)) != len(review_ids):
        raise ValueError("review ids do not match the local standard inventory")
    by_id = {standard.standard: standard for standard in standards}
    for review in reviews:
        standard = by_id[review["standard"]]
        expected_clauses = [clause.number for clause in standard.clauses]
        if review.get("checked_clauses") != expected_clauses:
            raise ValueError(f"incomplete clause coverage: {standard.standard}")
        if review.get("status") not in {
            "изменена нумерация",
            "нужна ручная проверка",
            "смысл отличается >5%",
            "порог >5% не подтверждён вручную",
            "порог >5% автоматически не выявлен",
        }:
            raise ValueError(f"invalid review status: {standard.standard}")
        for observation in review.get("observations", []):
            required = {
                "kind",
                "clause",
                "russian_evidence",
                "local_evidence",
                "english_evidence",
                "explanation",
                "confidence",
                "confirmed",
            }
            if set(observation) != required:
                raise ValueError(f"invalid observation schema: {standard.standard}")
            if observation["confirmed"] and (
                not observation["russian_evidence"]
                or not observation["local_evidence"]
                or observation["confidence"] != "high"
            ):
                raise ValueError(
                    f"confirmed observation lacks evidence: {standard.standard}"
                )


def _english_label(status: str) -> str:
    return {
        "fetched": "есть английский источник",
        "not_mapped": "нет английского источника",
        "unavailable": "английский источник недоступен",
    }.get(status, status)


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _report_stats(reviews: dict[str, Any]) -> dict[str, int]:
    items = reviews["reviews"]
    return {
        "total": len(items),
        "numbering": sum(
            item.get("numbering_status") == "изменена нумерация"
            or (
                "numbering_status" not in item
                and item["status"] == "изменена нумерация"
            )
            for item in items
        ),
        "semantic_changed": sum(
            item.get("semantic_status") == "смысл отличается >5%"
            or item["status"] == "смысл отличается >5%"
            for item in items
        ),
        "semantic_candidates": sum(
            item.get("semantic_conclusion") is not None for item in items
        ),
        "unresolved_gt_5": sum(
            float(item.get("semantic_unresolved_percent") or 0) > 5 for item in items
        ),
        "english": sum(item["english_status"] == "fetched" for item in items),
        "unmapped": sum(item["english_status"] == "not_mapped" for item in items),
        "official_differences": sum(
            observation["kind"] == "official_source_structure_difference"
            for item in items
            for observation in item["observations"]
        ),
        "confirmed": sum(
            bool(observation["confirmed"])
            for item in items
            for observation in item["observations"]
        ),
    }


def render_markdown_report(
    manifest: dict[str, Any], reviews: dict[str, Any]
) -> str:
    sources = {item["standard"]: item for item in manifest["standards"]}
    stats = _report_stats(reviews)
    lines = [
        "# Аудит всех стандартов",
        "",
        f"Снимок источников: `{reviews['audit_at']}`.",
        "",
        f"Проверено стандартов: **{stats['total']}**.",
        f"Подтверждено смысловое расхождение строго больше 5%: **{stats['semantic_changed']}**.",
        f"Подтверждённо изменена нумерация: **{stats['numbering']}**.",
        f"Вручную разобрано автоматических кандидатов: **{stats['semantic_candidates']}**.",
        f"Подтверждённых английских пар: **{stats['english']}**; без пары: **{stats['unmapped']}**.",
        f"Различий структуры русской и английской официальных статей: **{stats['official_differences']}**.",
        "",
        "> Русская ИТС — эталон смысла и нумерации. Английская статья — дополнительный сигнал. "
        "Процент — взвешенная доля подтверждённых смысловых единиц, а не процент разных слов. "
        "Неразрешённая доля не считается дефектом и показана отдельно.",
        "",
        "| Стандарт | Заголовок | Русский источник | Английский источник | Нумерация | Смысл | Разница | Неразрешено | Наблюдения |",
        "|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for review in reviews["reviews"]:
        source = sources[review["standard"]]
        russian = f"[ИТС]({source['russian']['url']})"
        if source["english"]["url"]:
            english = f"[1Ci KB]({source['english']['url']})"
        else:
            english = _english_label(source["english"]["status"])
        numbering = review.get("numbering_status") or (
            "изменена нумерация"
            if review["status"] == "изменена нумерация"
            else "совпадает"
        )
        semantic_status = review.get("semantic_status", review["status"])
        semantic_percent = review.get("semantic_difference_percent")
        unresolved_percent = review.get("semantic_unresolved_percent")
        cells = [
            review["standard"],
            review["title"],
            russian,
            english,
            numbering,
            semantic_status,
            f"{semantic_percent}%" if semantic_percent is not None else "—",
            f"{unresolved_percent}%" if unresolved_percent is not None else "—",
            len(review["observations"]),
        ]
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")

    lines.extend(["", "## Детальные наблюдения", ""])
    for review in reviews["reviews"]:
        lines.extend([f"### {review['standard']} — {review['title']}", ""])
        if not review["observations"]:
            lines.extend(
                [
                    review.get("semantic_conclusion")
                    or "Подтверждённых смысловых потерь свыше 5% не зафиксировано.",
                    "",
                ]
            )
            continue
        for observation in sorted(
            review["observations"],
            key=lambda item: (not item["confirmed"], item["kind"]),
        ):
            clause = f", пункт {observation['clause']}" if observation["clause"] else ""
            marker = "подтверждено" if observation["confirmed"] else "требует проверки"
            lines.extend(
                [
                    f"- **{observation['kind']}**{clause} — {marker}.",
                    f"  - Русская ИТС: {_markdown_cell(observation['russian_evidence'])}",
                    f"  - Наш сайт: {_markdown_cell(observation['local_evidence'])}",
                ]
            )
            if observation["english_evidence"]:
                lines.append(
                    f"  - English 1Ci KB: {_markdown_cell(observation['english_evidence'])}"
                )
            lines.extend([f"  - Вывод: {observation['explanation']}", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_html_report(manifest: dict[str, Any], reviews: dict[str, Any]) -> str:
    sources = {item["standard"]: item for item in manifest["standards"]}
    stats = _report_stats(reviews)
    rows: list[str] = []
    status_options = sorted({item["status"] for item in reviews["reviews"]})
    for review in reviews["reviews"]:
        source = sources[review["standard"]]
        status = review["status"]
        russian_url = escape(source["russian"]["url"], quote=True)
        if source["english"]["url"]:
            english_cell = (
                f'<a href="{escape(source["english"]["url"], quote=True)}" '
                'target="_blank" rel="noopener">1Ci KB</a>'
            )
        else:
            english_cell = escape(_english_label(source["english"]["status"]))
        details: list[str] = []
        if review["observations"]:
            for observation in sorted(
                review["observations"],
                key=lambda item: (not item["confirmed"], item["kind"]),
            ):
                badge = "Подтверждено" if observation["confirmed"] else "Проверить"
                evidence = [
                    f'<p><b>Русская ИТС:</b> {escape(str(observation["russian_evidence"]))}</p>',
                    f'<p><b>Наш сайт:</b> {escape(str(observation["local_evidence"]))}</p>',
                ]
                if observation["english_evidence"]:
                    evidence.append(
                        f'<p><b>English 1Ci KB:</b> {escape(str(observation["english_evidence"]))}</p>'
                    )
                details.append(
                    '<div class="observation">'
                    f'<div class="observation-title"><span>{escape(observation["kind"])}</span>'
                    f'<span class="mini-badge">{badge}</span></div>'
                    + "".join(evidence)
                    + f'<p><b>Вывод:</b> {escape(observation["explanation"])}</p></div>'
                )
        else:
            details.append(
                '<p class="muted">'
                + escape(
                    review.get("semantic_conclusion")
                    or "Подтверждённых смысловых потерь свыше 5% не зафиксировано."
                )
                + "</p>"
            )
        search_text = " ".join(
            [
                review["standard"],
                review["title"],
                status,
                review.get("semantic_conclusion") or "",
            ]
            + [item["kind"] for item in review["observations"]]
        ).casefold()
        numbering = (
            "Изменена"
            if review.get("numbering_status") == "изменена нумерация"
            or (
                "numbering_status" not in review
                and status == "изменена нумерация"
            )
            else "Совпадает"
        )
        semantic_percent = review.get("semantic_difference_percent")
        unresolved_percent = review.get("semantic_unresolved_percent")
        rows.append(
            f'<tr class="audit-row" data-status="{escape(status, quote=True)}" '
            f'data-search="{escape(search_text, quote=True)}">'
            f'<td><code>{escape(review["standard"])}</code></td>'
            f'<td><strong>{escape(review["title"])}</strong><details><summary>Доказательства '
            f'({len(review["observations"])})</summary>{"".join(details)}</details></td>'
            f'<td><a href="{russian_url}" target="_blank" rel="noopener">ИТС</a></td>'
            f'<td>{english_cell}</td><td>{numbering}</td>'
            f'<td><span class="status">{escape(status)}</span></td>'
            f'<td>{escape(str(semantic_percent)) + "%" if semantic_percent is not None else "—"}</td>'
            f'<td>{escape(str(unresolved_percent)) + "%" if unresolved_percent is not None else "—"}</td>'
            f'<td>{len(review["observations"])}</td></tr>'
        )
    options = "".join(
        f'<option value="{escape(status, quote=True)}">{escape(status)}</option>'
        for status in status_options
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">
<title>Аудит всех стандартов v8std</title>
<style>
:root{{--bg:#f4f6f8;--surface:#fff;--ink:#17202a;--muted:#667085;--line:#d9dee7;--accent:#315efb;--danger:#b42318;--success:#067647}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1500px;margin:auto;padding:32px}}h1{{margin:0 0 8px;font-size:32px}}.lead{{color:var(--muted);max-width:900px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:24px 0}}.card{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px}}.card b{{display:block;font-size:28px}}.card span{{color:var(--muted)}}
.controls{{position:sticky;top:0;z-index:3;display:flex;gap:12px;background:rgba(244,246,248,.95);padding:12px 0}}input,select{{min-height:42px;border:1px solid var(--line);border-radius:8px;background:#fff;padding:0 12px;font:inherit}}input{{flex:1}}
.table-wrap{{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px}}table{{width:100%;border-collapse:collapse;min-width:1320px}}th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}}th{{background:#eef1f5;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}td:nth-child(2){{min-width:410px}}a{{color:var(--accent)}}code{{white-space:nowrap}}details{{margin-top:8px}}summary{{cursor:pointer;color:var(--accent)}}.status,.mini-badge{{display:inline-block;border-radius:999px;background:#eef2ff;padding:3px 8px;font-size:12px}}tr[data-status="изменена нумерация"] .status,tr[data-status="смысл отличается >5%"] .status{{background:#fee4e2;color:var(--danger)}}tr[data-status="порог >5% не подтверждён вручную"] .status{{background:#ecfdf3;color:var(--success)}}.observation{{margin:10px 0;padding:12px;border-left:3px solid var(--line);background:#f8fafc}}.observation-title{{display:flex;justify-content:space-between;gap:8px;font-weight:700}}.observation p{{margin:6px 0}}.muted{{color:var(--muted)}}
@media(max-width:700px){{main{{padding:18px}}.controls{{flex-direction:column}}}}
</style></head><body><main>
<h1>Аудит всех стандартов</h1><p class="lead">Локальное сопоставление 317 страниц с русской ИТС и подтверждёнными английскими статьями. Русская ИТС определяет смысл и нумерацию; английская версия служит дополнительным сигналом. Процент — взвешенная доля подтверждённых смысловых единиц, а не доля изменённых слов. Неразрешённые единицы показаны отдельно и не считаются дефектами.</p>
<p class="muted">Снимок источников: {escape(reviews['audit_at'])}</p>
<section class="cards"><div class="card"><b>{stats['total']}</b><span>стандартов</span></div><div class="card"><b>{stats['semantic_changed']}</b><span>смысл отличается &gt;5%</span></div><div class="card"><b>{stats['numbering']}</b><span>изменена нумерация</span></div><div class="card"><b>{stats['semantic_candidates']}</b><span>кандидатов разобрано вручную</span></div><div class="card"><b>{stats['english']}</b><span>английских пар</span></div></section>
<div class="controls"><input id="text-filter" type="search" placeholder="Поиск по номеру, заголовку или типу расхождения"><select id="status-filter"><option value="">Все статусы</option>{options}</select><span id="shown-count" class="muted"></span></div>
<div class="table-wrap"><table><thead><tr><th>Стандарт</th><th>Заголовок и доказательства</th><th>RU</th><th>EN</th><th>Нумерация</th><th>Статус</th><th>Разница</th><th>Неразрешено</th><th>Набл.</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</main><script>
const textFilter=document.getElementById('text-filter');const statusFilter=document.getElementById('status-filter');const rows=[...document.querySelectorAll('.audit-row')];const shown=document.getElementById('shown-count');
function applyFilters(){{const q=textFilter.value.trim().toLocaleLowerCase('ru');const status=statusFilter.value;let count=0;for(const row of rows){{const visible=(!q||row.dataset.search.includes(q))&&(!status||row.dataset.status===status);row.hidden=!visible;if(visible)count++;}}shown.textContent=`Показано: ${{count}} из ${{rows.length}}`;}}
textFilter.addEventListener('input',applyFilters);statusFilter.addEventListener('change',applyFilters);applyFilters();
</script></body></html>"""


def _snapshot_payload(snapshot: SourceSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def _status_counts(records: list[dict[str, Any]], language: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        status = record[language]["status"]
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def fetch_sources(
    standards: list[LocalStandard],
    cache_dir: Path,
    *,
    fetcher: Callable[[str, str], SourceSnapshot] = fetch_snapshot,
    workers: int = 4,
) -> dict[str, Any]:
    sources_dir = cache_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    tasks: dict[Any, tuple[str, str]] = {}
    snapshots: dict[tuple[str, str], SourceSnapshot] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for standard in standards:
            tasks[
                executor.submit(
                    fetcher, canonical_russian_url(standard.standard), "ru"
                )
            ] = (standard.standard, "ru")
            if standard.english_url:
                tasks[executor.submit(fetcher, standard.english_url, "en")] = (
                    standard.standard,
                    "en",
                )
        for future in as_completed(tasks):
            key = tasks[future]
            snapshots[key] = future.result()

    records: list[dict[str, Any]] = []
    fetched_times: list[str] = []
    for standard in standards:
        russian = snapshots[(standard.standard, "ru")]
        russian_file = sources_dir / f"ru-{standard.standard[3:]}.json"
        atomic_write_text(
            russian_file,
            json.dumps(_snapshot_payload(russian), ensure_ascii=False, indent=2)
            + "\n",
        )
        fetched_times.append(russian.fetched_at)
        if standard.english_url:
            english = snapshots[(standard.standard, "en")]
            english_file = sources_dir / f"en-{standard.standard[3:]}.json"
            atomic_write_text(
                english_file,
                json.dumps(_snapshot_payload(english), ensure_ascii=False, indent=2)
                + "\n",
            )
            english_record: dict[str, Any] = {
                "status": english.status,
                "url": english.url,
                "snapshot": str(english_file),
                "error": english.error,
            }
            fetched_times.append(english.fetched_at)
        else:
            english_record = {
                "status": "not_mapped",
                "url": None,
                "snapshot": None,
                "error": None,
            }
        records.append(
            {
                "standard": standard.standard,
                "title": standard.title,
                "local_path": standard.source_path,
                "russian": {
                    "status": russian.status,
                    "url": russian.url,
                    "snapshot": str(russian_file),
                    "error": russian.error,
                },
                "english": english_record,
            }
        )

    manifest = {
        "version": 1,
        "audit_at": max(fetched_times) if fetched_times else "",
        "counts": {
            "russian": _status_counts(records, "russian"),
            "english": _status_counts(records, "english"),
        },
        "standards": records,
    }
    atomic_write_text(
        cache_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return manifest


def _print_source_status(manifest: dict[str, Any]) -> None:
    print(f"standards: {len(manifest['standards'])}")
    for language in ("russian", "english"):
        counts = manifest["counts"][language]
        summary = ", ".join(f"{key}={value}" for key, value in counts.items())
        print(f"{language}: {summary}")
    for record in manifest["standards"]:
        for language in ("russian", "english"):
            source = record[language]
            if source["status"] == "unavailable":
                print(
                    f"{record['standard']} {language}: {source['url']} "
                    f"({source['error']})"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all local v8std standards")
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_parser = subparsers.add_parser("fetch", help="snapshot official sources")
    fetch_parser.add_argument("--cache-dir", type=Path, required=True)
    fetch_parser.add_argument("--workers", type=int, default=4)
    status_parser = subparsers.add_parser("source-status", help="show snapshot states")
    status_parser.add_argument("--cache-dir", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare", help="compare source structure")
    compare_parser.add_argument("--cache-dir", type=Path, required=True)
    compare_parser.add_argument("--output", type=Path, required=True)
    semantic_parser = subparsers.add_parser(
        "semantic", help="calculate conservative semantic difference lower bounds"
    )
    semantic_parser.add_argument("--cache-dir", type=Path, required=True)
    semantic_parser.add_argument("--sentence-model", type=Path, required=True)
    semantic_parser.add_argument("--nli-model", type=Path, required=True)
    semantic_parser.add_argument("--batch-size", type=int, default=32)
    semantic_parser.add_argument("--output", type=Path, required=True)
    adjudicate_parser = subparsers.add_parser(
        "adjudicate", help="apply manual decisions to semantic candidates"
    )
    adjudicate_parser.add_argument("--semantic", type=Path, required=True)
    adjudicate_parser.add_argument("--decisions", type=Path, required=True)
    adjudicate_parser.add_argument("--output", type=Path, required=True)
    review_parser = subparsers.add_parser("review", help="build review ledger")
    review_parser.add_argument("--cache-dir", type=Path, required=True)
    review_parser.add_argument("--structural", type=Path, required=True)
    review_parser.add_argument("--semantic", type=Path)
    review_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate", help="validate review ledger")
    validate_parser.add_argument("--cache-dir", type=Path, required=True)
    validate_parser.add_argument("--reviews", type=Path, required=True)
    report_parser = subparsers.add_parser("report", help="render local reports")
    report_parser.add_argument("--cache-dir", type=Path, required=True)
    report_parser.add_argument("--reviews", type=Path, required=True)
    report_parser.add_argument("--markdown", type=Path, required=True)
    report_parser.add_argument("--html", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "fetch":
        standards = inventory_local_standards(
            Path("docs/std"), Path("data/standard-english-sources.json")
        )
        manifest = fetch_sources(
            standards, args.cache_dir, workers=max(1, args.workers)
        )
        _print_source_status(manifest)
        return 0
    if args.command == "compare":
        standards = inventory_local_standards(
            Path("docs/std"), Path("data/standard-english-sources.json")
        )
        payload = generate_structural_findings(standards, args.cache_dir)
        atomic_write_text(
            args.output,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
        changed = sum(bool(item["findings"]) for item in payload["standards"])
        print(f"structural comparisons: {len(standards)}, findings: {changed}")
        return 0
    if args.command == "semantic":
        standards = inventory_local_standards(
            Path("docs/std"), Path("data/standard-english-sources.json")
        )
        payload = generate_semantic_audit(
            standards,
            args.cache_dir,
            sentence_model_path=args.sentence_model,
            nli_model_path=args.nli_model,
            batch_size=max(1, args.batch_size),
        )
        atomic_write_text(
            args.output,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
        flagged = sum(
            item["status"] == "смысл отличается >5%"
            for item in payload["standards"]
        )
        print(f"semantic audit: {len(standards)} standards, >5%: {flagged}")
        return 0
    if args.command == "adjudicate":
        semantic = json.loads(args.semantic.read_text(encoding="utf-8"))
        decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
        payload = apply_manual_semantic_review(semantic, decisions)
        atomic_write_text(
            args.output,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        )
        confirmed = sum(
            item["semantic_status"] == "смысл отличается >5%"
            for item in payload["standards"]
        )
        print(
            f"manual semantic review: {payload['manual_review']['reviewed_candidates']} "
            f"candidates, confirmed >5%: {confirmed}"
        )
        return 0
    if args.command in {"review", "validate"}:
        standards = inventory_local_standards(
            Path("docs/std"), Path("data/standard-english-sources.json")
        )
        if args.command == "review":
            manifest = json.loads(
                (args.cache_dir / "manifest.json").read_text(encoding="utf-8")
            )
            structural = json.loads(args.structural.read_text(encoding="utf-8"))
            semantic = (
                json.loads(args.semantic.read_text(encoding="utf-8"))
                if args.semantic
                else None
            )
            ledger = build_review_ledger(
                standards, args.cache_dir, manifest, structural, semantic
            )
            validate_review_ledger(standards, ledger)
            atomic_write_text(
                args.output,
                json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            )
            print(f"review ledger: {len(ledger['reviews'])} standards")
            return 0
        ledger = json.loads(args.reviews.read_text(encoding="utf-8"))
        validate_review_ledger(standards, ledger)
        print(f"{len(standards)} audit review records valid")
        return 0
    if args.command == "report":
        manifest = json.loads(
            (args.cache_dir / "manifest.json").read_text(encoding="utf-8")
        )
        reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
        atomic_write_text(args.markdown, render_markdown_report(manifest, reviews))
        atomic_write_text(args.html, render_html_report(manifest, reviews))
        print(f"{len(reviews['reviews'])} standards rendered")
        return 0
    manifest = json.loads(
        (args.cache_dir / "manifest.json").read_text(encoding="utf-8")
    )
    _print_source_status(manifest)
    return 0


def _single_match(pattern: re.Pattern[str], content: str, label: str) -> re.Match[str]:
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise ValueError(f"expected one {label}, found {len(matches)}")
    return matches[0]


def _clause_from_lines(
    number: str, section: str, title: str, lines: list[str]
) -> Clause:
    text = "\n".join(lines).strip()
    return Clause(
        number=number,
        section=section,
        title=title.strip(),
        text=text,
        normative_terms=tuple(match.group(0) for match in NORMATIVE_RE.finditer(text)),
        numeric_terms=tuple(match.group(0) for match in NUMBER_RE.finditer(text)),
    )


def _parse_clauses(content: str) -> tuple[Clause, ...]:
    cleaned = BACKLINK_BLOCK_RE.sub("", content)
    clauses: list[Clause] = []
    current_number: str | None = None
    current_section = ""
    current_title = ""
    current_lines: list[str] = []

    def finish() -> None:
        nonlocal current_number, current_title, current_lines
        if current_number is not None:
            clauses.append(
                _clause_from_lines(
                    current_number, current_section, current_title, current_lines
                )
            )
        current_number = None
        current_title = ""
        current_lines = []

    for line in cleaned.splitlines():
        section_match = SECTION_HEADING_RE.match(line)
        if section_match is not None:
            finish()
            current_section = section_match.group("title").strip()
            continue
        match = CLAUSE_HEADING_RE.match(line)
        if match is not None:
            finish()
            current_number = match.group("number")
            current_title = match.group("title") or ""
            continue
        if current_number is not None and ANY_HEADING_RE.match(line):
            finish()
            continue
        if current_number is not None:
            current_lines.append(line)
    finish()

    seen: set[tuple[str, str]] = set()
    for clause in clauses:
        key = (clause.section, clause.number)
        if key in seen:
            raise ValueError(f"duplicate clause {clause.number}")
        seen.add(key)
    return tuple(clauses)


def parse_local_standard(
    path: Path, english_sources: Mapping[str, str]
) -> LocalStandard:
    content = path.read_text(encoding="utf-8")
    marker = _single_match(STANDARD_MARKER_RE, content, "standard marker")
    title = _single_match(TITLE_RE, content, "H1 title")
    filename_number = path.stem
    marker_number = marker.group("number")
    source_section = re.search(
        r"^###### Источник(?:и)?\s*$\n(?P<body>.*)\Z",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if source_section is None:
        raise ValueError("expected source section")
    source_matches = list(ITS_SOURCE_RE.finditer(source_section.group("body")))
    source = next(
        (match for match in source_matches if match.group("number") == filename_number),
        None,
    )
    source_number = source.group("number") if source is not None else "missing"
    if len({filename_number, marker_number, source_number}) != 1:
        raise ValueError(
            "identity mismatch: "
            f"filename={filename_number}, marker={marker_number}, source={source_number}"
        )
    standard = f"std{filename_number}"
    return LocalStandard(
        standard=standard,
        title=title.group("title").strip(),
        russian_url=source.group(0),
        english_url=english_sources.get(standard),
        clauses=_parse_clauses(content),
        source_path=str(path),
    )


def inventory_local_standards(
    docs_dir: Path, english_registry: Path
) -> list[LocalStandard]:
    payload = json.loads(english_registry.read_text(encoding="utf-8"))
    english_sources = {
        item["standard"]: item["english_url"] for item in payload["sources"]
    }
    pages = sorted(docs_dir.glob("*.md"), key=lambda path: int(path.stem))
    standards = [parse_local_standard(path, english_sources) for path in pages]
    ids = [item.standard for item in standards]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate standard ids in local inventory")
    return standards


if __name__ == "__main__":
    raise SystemExit(main())
