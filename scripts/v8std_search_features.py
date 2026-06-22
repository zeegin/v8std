from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


STD_RE = re.compile(r"^#?(?:std|стд|стандарт)?\s*[-:_]?\s*(\d{2,4})$", re.IGNORECASE)
ACC_RE = re.compile(r"^#?(?:acc|апк)\s*[-:_]?\s*(\d+)$", re.IGNORECASE)
V8CS_RE = re.compile(r"^#?(?:v8cs|edt)\s*[-:_]?\s*(.+)$", re.IGNORECASE)
BSLLS_RE = re.compile(r"^#?bslls\s*[-:_]?\s*(.+)$", re.IGNORECASE)
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-zа-яё0-9])(?=[A-ZА-ЯЁ])")
WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
PAREN_RE = re.compile(r"\(([^()]{2,120})\)")
STD_MARKER_RE = re.compile(r"\s+#std\d+\s*$", re.IGNORECASE)
MARKDOWN_HEADING_PREFIX_RE = re.compile(r"^\s{0,3}#\s+(.+?)\s*$", re.MULTILINE)
NUMERIC_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.?$")
GENERIC_HEADING_ALIASES = {
    "источник",
    "источники",
    "стандарт",
    "стандарты",
    "проверка",
    "проверки",
    "пример",
    "примеры",
    "см. также",
    "см также",
    "неправильно",
    "правильно",
    "в стандарте не указано",
}

RU_TO_EN = str.maketrans(
    {
        "й": "q",
        "ц": "w",
        "у": "e",
        "к": "r",
        "е": "t",
        "н": "y",
        "г": "u",
        "ш": "i",
        "щ": "o",
        "з": "p",
        "х": "[",
        "ъ": "]",
        "ф": "a",
        "ы": "s",
        "в": "d",
        "а": "f",
        "п": "g",
        "р": "h",
        "о": "j",
        "л": "k",
        "д": "l",
        "ж": ";",
        "э": "'",
        "я": "z",
        "ч": "x",
        "с": "c",
        "м": "v",
        "и": "b",
        "т": "n",
        "ь": "m",
        "б": ",",
        "ю": ".",
    }
)

RU_SUFFIXES = (
    "иями",
    "ями",
    "ами",
    "ого",
    "ему",
    "ыми",
    "ими",
    "ией",
    "иях",
    "ях",
    "ах",
    "ов",
    "ев",
    "ей",
    "ом",
    "ем",
    "ам",
    "ям",
    "ой",
    "ый",
    "ий",
    "ая",
    "ое",
    "ые",
    "ую",
    "юю",
    "ых",
    "их",
    "а",
    "я",
    "е",
    "у",
    "ы",
    "и",
    "о",
    "ь",
)


@dataclass(frozen=True)
class CodeLookupCandidate:
    key: str
    detail: str
    source: str


def normalize_search_text(value: str) -> str:
    value = value.replace("ё", "е").replace("Ё", "Е")
    value = re.sub(r"[`\"'«»]+", " ", value)
    value = re.sub(r"\s+", " ", value.strip())
    return value.casefold()


def keyboard_layout_variants(value: str) -> list[str]:
    variants = [value]
    translated = value.casefold().translate(RU_TO_EN)
    if translated != value.casefold():
        variants.append(translated)
    return dedupe(variants)


def split_identifier_tokens(value: str) -> list[str]:
    value = CAMEL_BOUNDARY_RE.sub(" ", value)
    value = re.sub(r"[_:/.-]+", " ", value)
    return [token.casefold().replace("ё", "е") for token in WORD_RE.findall(value)]


def identifier_phrase(value: str) -> str:
    return " ".join(split_identifier_tokens(value))


def search_terms(value: str) -> list[str]:
    tokens = [token.casefold().replace("ё", "е") for token in WORD_RE.findall(value)]
    tokens.extend(split_identifier_tokens(value))
    result: list[str] = []
    for token in tokens:
        result.append(token)
        stem = light_ru_stem(token)
        if stem != token:
            result.append(stem)
    return dedupe(result)


def canonical_search_terms(value: str) -> list[str]:
    result: list[str] = []
    for token in search_terms(value):
        result.append(light_ru_stem(token))
    return dedupe(result)


def light_ru_stem(token: str) -> str:
    token = token.casefold().replace("ё", "е")
    if not re.fullmatch(r"[а-я]+", token):
        return token
    for suffix in RU_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def compact_code(value: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "", normalize_search_text(value))


def code_lookup_candidates(value: str) -> list[CodeLookupCandidate]:
    candidates: list[CodeLookupCandidate] = []
    seen: set[str] = set()

    for variant in keyboard_layout_variants(value):
        detail = "keyboard_layout" if variant != value.casefold() else "code_variant"
        for key in _code_keys_for_variant(variant):
            if key not in seen:
                candidates.append(CodeLookupCandidate(key=key, detail=detail, source=variant))
                seen.add(key)
    return candidates


def code_lookup_variants(value: str) -> list[str]:
    return [candidate.key for candidate in code_lookup_candidates(value)]


def is_code_like_query(value: str) -> bool:
    if code_lookup_candidates(value):
        return True
    stripped = value.strip()
    if len(stripped) < 6 or len(stripped) > 100:
        return False
    if re.search(r"\s", stripped):
        return False
    return bool(re.search(r"[A-Za-z]", stripped))


def fuzzy_code_forms(value: str) -> list[str]:
    forms = []
    for variant in keyboard_layout_variants(value):
        normalized = normalize_search_text(variant)
        forms.append(re.sub(r"[^a-z0-9а-я]+", "", normalized))
        phrase = identifier_phrase(variant)
        if phrase:
            forms.append(re.sub(r"[^a-z0-9а-я]+", "", phrase))
    return [form for form in dedupe(forms) if len(form) >= 6]


def generated_aliases_for_page(page: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    page_id = str(page.get("id", "")).strip()
    page_type = str(page.get("type", "")).strip()
    title = str(page.get("title", "")).strip()
    body = str(page.get("body_markdown", "") or "")

    aliases.extend(_aliases_from_id(page_id, page_type))
    aliases.extend(_aliases_from_path_like_value(str(page.get("source_path", ""))))
    aliases.extend(_aliases_from_path_like_value(str(page.get("url", ""))))
    aliases.extend(_aliases_from_path_like_value(str(page.get("markdown_url", ""))))
    aliases.extend(_aliases_from_title(title))
    aliases.extend(_aliases_from_primary_markdown_heading(body))

    return dedupe(clean_alias(alias) for alias in aliases)


def _code_keys_for_variant(value: str) -> list[str]:
    normalized = normalize_search_text(value)
    compact = compact_code(normalized)
    keys: list[str] = []

    std_match = STD_RE.match(normalized) or re.match(r"^std(\d{2,4})$", compact)
    if std_match:
        keys.append(f"std{std_match.group(1)}")
    elif re.match(r"^#?\d{2,4}$", normalized):
        keys.append(f"std{normalized.lstrip('#')}")

    acc_match = ACC_RE.match(normalized) or re.match(r"^acc(\d+)$", compact)
    if acc_match:
        keys.append(f"acc:{acc_match.group(1)}")

    v8cs_match = V8CS_RE.match(normalized)
    if v8cs_match:
        keys.append(f"v8cs:{v8cs_match.group(1).strip()}")

    bslls_match = BSLLS_RE.match(normalized)
    if bslls_match:
        keys.append(f"bslls:{bslls_match.group(1).strip()}")

    return dedupe(keys)


def _aliases_from_id(page_id: str, page_type: str) -> list[str]:
    aliases = [page_id]
    if page_type == "diagnostic" and ":" in page_id:
        family, code = page_id.split(":", 1)
        if family != "acc":
            aliases.append(code)
            aliases.extend(_identifier_aliases(code))
        if family == "bslls":
            aliases.append(f"bslls {code}")
        elif family == "v8cs":
            aliases.append(f"edt {code}")
            aliases.append(f"v8cs {code}")
        elif family == "acc":
            aliases.append(f"acc {code}")
            aliases.append(f"апк {code}")
    elif page_id.startswith("std") and page_id[3:].isdigit():
        number = page_id[3:]
        aliases.extend([f"#std{number}", f"std {number}", f"стандарт {number}"])
    else:
        aliases.extend(_identifier_aliases(page_id))
    return aliases


def _aliases_from_path_like_value(value: str) -> list[str]:
    if not value:
        return []
    path = value.rstrip("/")
    if "://" in path:
        path = path.split("://", 1)[1].split("/", 1)[-1]
    stem = Path(path).stem
    if not stem or stem in {"index", "mcp"} or stem.isdigit():
        return []
    return [stem, *_identifier_aliases(stem)]


def _aliases_from_title(title: str) -> list[str]:
    if not title:
        return []
    aliases = [title]
    stripped_marker = STD_MARKER_RE.sub("", title).strip()
    if stripped_marker and stripped_marker != title:
        aliases.append(stripped_marker)
    aliases.extend(match.group(1).strip() for match in PAREN_RE.finditer(title))
    aliases.extend(_identifier_aliases(match.group(1).strip()) for match in PAREN_RE.finditer(title))
    return _flatten(aliases)


def _aliases_from_primary_markdown_heading(body: str) -> list[str]:
    match = MARKDOWN_HEADING_PREFIX_RE.search(body)
    if match is None:
        return []
    heading = re.sub(r"\s*\{#[^}]+}\s*$", "", match.group(1)).strip()
    if not heading or not useful_heading_alias(heading):
        return []
    return [heading]


def useful_heading_alias(value: str) -> bool:
    normalized = normalize_search_text(value).strip(".")
    return not (
        NUMERIC_HEADING_RE.match(value.strip())
        or normalized in GENERIC_HEADING_ALIASES
    )


def _identifier_aliases(value: str) -> list[str]:
    tokens = split_identifier_tokens(value)
    if len(tokens) <= 1:
        return []
    spaced = " ".join(tokens)
    kebab = "-".join(tokens)
    snake = "_".join(tokens)
    return [spaced, kebab, snake]


def _flatten(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            result.append(value)
        elif isinstance(value, Iterable):
            result.extend(str(item) for item in value)
    return result


def clean_alias(value: str) -> str:
    value = " ".join(str(value).split()).strip()
    return value[:180]


def dedupe(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        if not value:
            continue
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
