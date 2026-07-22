import tempfile
import unittest
import subprocess
import json
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

from scripts.standard_content_audit import (
    Clause,
    LocalStandard,
    SourceSnapshot,
    compare_structure,
    build_review_ledger,
    validate_review_ledger,
    render_html_report,
    render_markdown_report,
    extract_semantic_units,
    compare_semantic_units,
    semantic_difference_percent,
    semantic_local_clauses,
    decide_semantic_comparison,
    apply_manual_semantic_review,
    canonical_russian_url,
    fetch_snapshot,
    fetch_sources,
    generate_structural_findings,
    inventory_local_standards,
    parse_local_standard,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ENGLISH_URL = (
    "https://kb.1ci.com/1C_Enterprise_Platform/Guides/Developer_Guides/"
    "1C_Enterprise_Development_Standards/Code_conventions/"
    "Using_1C_Enterprise_language_structures/Event_log/?language=en"
)


class LocalStandardParserTests(unittest.TestCase):
    def write_page(self, root: Path, name: str, content: str) -> Path:
        path = root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_parses_identity_clauses_and_signals(self):
        source = """###### #std498

# Использование Журнала регистрации

###### 1.

Журнал хранит события.

###### 2.1.А.

Не включайте конкретные данные. Ориентир — до 10 Кб.

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            standard = parse_local_standard(page, {"std498": ENGLISH_URL})

        self.assertEqual(standard.standard, "std498")
        self.assertEqual(standard.title, "Использование Журнала регистрации")
        self.assertEqual([clause.number for clause in standard.clauses], ["1", "2.1.А"])
        self.assertIn("Не включайте", standard.clauses[1].normative_terms)
        self.assertIn("10 Кб", standard.clauses[1].numeric_terms)
        self.assertEqual(standard.english_url, ENGLISH_URL)

    def test_excludes_managed_and_nonnumeric_sections_from_clause_text(self):
        source = """###### #std498

# Заголовок

###### 1.

Используйте правило.

<!-- diagnostic-backlinks:start clause=1 -->
###### Проверки

~[#acc:1](../diagnostics/acc/1.md)~
<!-- diagnostic-backlinks:end clause=1 -->

###### См. также

- [Другая страница](499.md)

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            standard = parse_local_standard(page, {})

        self.assertEqual(len(standard.clauses), 1)
        self.assertEqual(standard.clauses[0].text, "Используйте правило.")

    def test_rejects_duplicate_clause_numbers(self):
        source = """###### #std498

# Заголовок

###### 1.

Первый текст.

###### 1.

Повтор.

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            with self.assertRaisesRegex(ValueError, "duplicate clause 1"):
                parse_local_standard(page, {})

    def test_allows_numbering_to_restart_in_a_named_section(self):
        source = """###### #std498

# Заголовок

###### 1.

Первый раздел.

## Работа с файлами

###### 1.

Второй раздел.

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            standard = parse_local_standard(page, {})

        self.assertEqual([clause.number for clause in standard.clauses], ["1", "1"])
        self.assertEqual(
            [clause.section for clause in standard.clauses],
            ["", "Работа с файлами"],
        )

    def test_accepts_clause_headings_without_terminal_period(self):
        source = """###### #std498

# Заголовок

###### 1

Первый пункт.

###### 4.1

Вложенный пункт.

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            standard = parse_local_standard(page, {})

        self.assertEqual([clause.number for clause in standard.clauses], ["1", "4.1"])
        self.assertEqual([clause.title for clause in standard.clauses], ["", ""])

    def test_rejects_filename_marker_and_source_mismatch(self):
        source = """###### #std499

# Заголовок

###### 1.

Текст.

###### Источник

https://its.1c.ru/db/v8std#content:497
"""
        with tempfile.TemporaryDirectory() as temp:
            page = self.write_page(Path(temp), "498.md", source)
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                parse_local_standard(page, {})


class RepositoryInventoryTests(unittest.TestCase):
    def test_inventory_contains_exactly_every_standard_page(self):
        standards = inventory_local_standards(
            REPO_ROOT / "docs/std",
            REPO_ROOT / "data/standard-english-sources.json",
        )
        ids = {item.standard for item in standards}
        expected = {
            f"std{path.stem}" for path in (REPO_ROOT / "docs/std").glob("*.md")
        }
        self.assertEqual(len(standards), 317)
        self.assertEqual(len(ids), 317)
        self.assertEqual(ids, expected)

    def test_std467_limits_both_legacy_modes_to_administrators(self):
        standard = parse_local_standard(REPO_ROOT / "docs/std/467.md", {})
        clause = next(item for item in standard.clauses if item.number == "1.4")
        scope, modes = clause.text.casefold().split(
            "- толстого клиента обычного приложения", maxsplit=1
        )

        self.assertIn("администратор", scope)
        self.assertIn("полными правами", scope)
        self.assertIn("- внешнего соединения", modes)
        self.assertIn("- внешнего соединения.\n\nСтарые технологии", clause.text)
        self.assertIn("8.0", clause.text)
        self.assertIn("8.1", clause.text)

    def test_std535_explains_cross_dbms_precision_limits(self):
        standard = parse_local_standard(REPO_ROOT / "docs/std/535.md", {})
        clause = next(item for item in standard.clauses if item.number == "2")

        self.assertIn("31", clause.text)
        self.assertIn("суммарно", clause.text.casefold())
        self.assertIn("0.00001", clause.text)
        self.assertIn("20 разрядов целой части", clause.text.casefold())

    def test_std729_explains_the_practical_table_count_threshold(self):
        standard = parse_local_standard(REPO_ROOT / "docs/std/729.md", {})
        clause = next(item for item in standard.clauses if item.number == "2.2")

        self.assertRegex(clause.text, r"5\s*[–-]\s*7")
        self.assertIn("нелинейн", clause.text.casefold())
        self.assertIn("план выполнения", clause.text.casefold())

    def test_std774_explains_os_allowlisting_for_static_executables(self):
        standard = parse_local_standard(REPO_ROOT / "docs/std/774.md", {})
        clause = next(item for item in standard.clauses if item.number == "2.5")
        text = clause.text.casefold()

        self.assertIn("запрещать запуск", text)
        self.assertIn("кроме явно разрешенных", text)
        self.assertIn("временный каталог целиком", text)
        self.assertIn("вредоносный файл", text)
        self.assertIn("электронной подписи", text)
        self.assertIn("хеш", text)


class FakeResponse(BytesIO):
    def __init__(self, body: bytes, content_type: str = "text/html; charset=UTF-8"):
        super().__init__(body)
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SourceSnapshotTests(unittest.TestCase):
    def test_canonical_russian_url_uses_content_endpoint(self):
        self.assertEqual(
            canonical_russian_url("std498"),
            "https://its.1c.ru/db/v8std/content/498/hdoc",
        )

    def test_russian_snapshot_follows_document_iframe_and_decodes_charset(self):
        outer = (
            b'<iframe id="auth_check" src="https://login.1c.ru/check"></iframe>'
            b'<iframe id="w_metadata_doc_frame" title="Document" '
            b'src="&nbsp;/db/content/v8std/src/1&nbsp;200/498.htm"></iframe>'
        )
        inner = """<html><head><title>Журнал</title></head><body>
        <h1>Использование журнала</h1>
        <p><a id="1"></a>1. Журнал хранит события.</p>
        <p>Дополнение первого пункта.<br>2.1. Не следует<br>объединять события.</p>
        </body></html>""".encode("windows-1251")
        responses = [
            FakeResponse(outer),
            FakeResponse(inner, "text/html; charset=Windows-1251"),
        ]

        requested_urls = []

        def opener(request, timeout):
            self.assertEqual(timeout, 30)
            requested_urls.append(request.full_url)
            return responses.pop(0)

        snapshot = fetch_snapshot(
            canonical_russian_url("std498"), "ru", opener=opener
        )

        self.assertEqual(snapshot.status, "fetched")
        self.assertEqual(snapshot.title, "Использование журнала")
        self.assertEqual([clause.number for clause in snapshot.clauses], ["1", "2.1"])
        self.assertIn("Дополнение первого пункта", snapshot.clauses[0].text)
        self.assertIn("Не следует", snapshot.clauses[1].normative_terms)
        self.assertRegex(snapshot.sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(
            requested_urls[1],
            "https://its.1c.ru/db/content/v8std/src/1%C2%A0200/498.htm",
        )

    def test_english_snapshot_uses_only_xwiki_content(self):
        body = """<html><head><title>Event log - XWiki</title></head><body>
        <nav><p>99. Navigation noise.</p></nav>
        <div id="xwikicontent">
          <p>1. Event log stores events.</p>
          <p>2.1. Do not merge several events.</p>
        </div>
        </body></html>""".encode()

        snapshot = fetch_snapshot(
            ENGLISH_URL,
            "en",
            opener=lambda _request, timeout: FakeResponse(body),
        )

        self.assertEqual(snapshot.title, "Event log")
        self.assertEqual([clause.number for clause in snapshot.clauses], ["1", "2.1"])
        self.assertNotIn("Navigation noise", " ".join(c.text for c in snapshot.clauses))

    def test_decimal_code_literal_is_not_parsed_as_clause_number(self):
        body = """<html><body>
        <h1>Округление</h1>
        <p>1. Измените порядок операций.\n0.02 / 28346 * 9287492</p>
        <p>2. Явно задавайте разрядность.</p>
        </body></html>""".encode()

        snapshot = fetch_snapshot(
            canonical_russian_url("std535"),
            "ru",
            opener=lambda _request, timeout: FakeResponse(body),
        )

        self.assertEqual([clause.number for clause in snapshot.clauses], ["1", "2"])
        self.assertIn("0.02 / 28346", snapshot.clauses[0].text)

    def test_unnumbered_normative_source_is_fetched_as_whole_article_clause(self):
        body = """<html><head><title>Schedule - XWiki</title></head><body>
        <div id="xwikicontent">
          <p>Do not run a scheduled job more often than required.</p>
          <ul><li>The minimum interval is one minute.</li></ul>
          <h3>See also</h3><p>Another article</p>
        </div>
        </body></html>""".encode()

        snapshot = fetch_snapshot(
            ENGLISH_URL,
            "en",
            opener=lambda _request, timeout: FakeResponse(body),
        )

        self.assertEqual(snapshot.status, "fetched")
        self.assertEqual([clause.number for clause in snapshot.clauses], [""])
        self.assertIn("minimum interval", snapshot.clauses[0].text)
        self.assertNotIn("Another article", snapshot.clauses[0].text)

    def test_http_failure_is_explicitly_unavailable(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 503, "unavailable", {}, None)

        snapshot = fetch_snapshot(ENGLISH_URL, "en", opener=opener)

        self.assertEqual(snapshot.status, "unavailable")
        self.assertIn("503", snapshot.error)
        self.assertEqual(snapshot.clauses, ())

    def test_manifest_records_fetched_and_not_mapped_sources(self):
        clause = Clause("1", "", "", "Текст", (), ())
        standards = [
            LocalStandard(
                "std498",
                "Журнал",
                "https://its.1c.ru/db/v8std#content:498",
                ENGLISH_URL,
                (clause,),
                "docs/std/498.md",
            ),
            LocalStandard(
                "std499",
                "Исключения",
                "https://its.1c.ru/db/v8std#content:499",
                None,
                (clause,),
                "docs/std/499.md",
            ),
        ]

        def fetcher(url: str, language: str) -> SourceSnapshot:
            return SourceSnapshot(
                url=url,
                fetched_at="2026-07-22T00:00:00+00:00",
                status="fetched",
                sha256="a" * 64,
                title="Source",
                clauses=(clause,),
                error=None,
            )

        with tempfile.TemporaryDirectory() as temp:
            manifest = fetch_sources(
                standards, Path(temp), fetcher=fetcher, workers=1
            )
            written = list((Path(temp) / "sources").glob("*.json"))

        self.assertEqual(len(manifest["standards"]), 2)
        self.assertEqual(len(written), 3)
        self.assertEqual(
            manifest["standards"][1]["english"]["status"], "not_mapped"
        )
        self.assertEqual(manifest["counts"]["russian"]["fetched"], 2)
        self.assertEqual(manifest["counts"]["english"]["not_mapped"], 1)

    def test_cli_help_loads_after_all_functions_are_defined(self):
        result = subprocess.run(
            ["python3.12", str(REPO_ROOT / "scripts/standard_content_audit.py"), "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source-status", result.stdout)


class StructuralComparisonTests(unittest.TestCase):
    def local(self, clauses: tuple[Clause, ...]) -> LocalStandard:
        return LocalStandard(
            "std498",
            "Журнал",
            "https://its.1c.ru/db/v8std#content:498",
            ENGLISH_URL,
            clauses,
            "docs/std/498.md",
        )

    def source(self, clauses: tuple[Clause, ...]) -> SourceSnapshot:
        return SourceSnapshot(
            canonical_russian_url("std498"),
            "2026-07-22T00:00:00+00:00",
            "fetched",
            "a" * 64,
            "Журнал",
            clauses,
            None,
        )

    def clause(
        self,
        number: str,
        text: str,
        normative: tuple[str, ...] = (),
        numeric: tuple[str, ...] = (),
    ) -> Clause:
        return Clause(number, "", "", text, normative, numeric)

    def test_exact_numbering_and_signals_have_no_findings(self):
        clauses = (self.clause("1", "Правило", ("следует",), ("10",)),)
        self.assertEqual(compare_structure(self.local(clauses), self.source(clauses)), [])

    def test_reports_missing_extra_and_reordered_numbers(self):
        local = (self.clause("1", "A"), self.clause("3", "C"), self.clause("2", "B"))
        source = (self.clause("1", "A"), self.clause("2", "B"), self.clause("4", "D"))
        kinds = {item.kind for item in compare_structure(self.local(local), self.source(source))}
        self.assertEqual(kinds, {"numbering_sequence", "missing_clause", "extra_clause"})

    def test_reports_officially_unnumbered_article_as_changed_numbering(self):
        local = (self.clause("1", "Правило"),)
        source = (self.clause("", "Правило"),)
        findings = compare_structure(self.local(local), self.source(source))
        self.assertEqual([item.kind for item in findings], ["source_unnumbered_local_numbered"])
        self.assertEqual(findings[0].confidence, "high")

    def test_signal_losses_are_candidates_not_confirmed_semantic_defects(self):
        local = (self.clause("1", "Используйте значение"),)
        source = (self.clause("1", "Не следует превышать 10 Кб", ("Не следует",), ("10 Кб",)),)
        findings = compare_structure(self.local(local), self.source(source))
        self.assertEqual(
            {item.kind for item in findings},
            {"normative_signal_changed", "numeric_term_missing"},
        )
        self.assertEqual({item.confidence for item in findings}, {"needs_review"})

    def test_structural_payload_contains_one_record_per_standard(self):
        local = self.local((self.clause("1", "Правило"),))
        source = self.source((self.clause("1", "Правило"),))
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            sources = cache / "sources"
            sources.mkdir()
            (sources / "ru-498.json").write_text(
                json.dumps(asdict(source), ensure_ascii=False), encoding="utf-8"
            )
            payload = generate_structural_findings([local], cache)

        self.assertEqual(payload["version"], 1)
        self.assertEqual(len(payload["standards"]), 1)
        self.assertEqual(payload["standards"][0]["standard"], "std498")
        self.assertEqual(payload["standards"][0]["numbering_status"], "совпадает")

    def test_review_ledger_separates_confirmed_numbering_from_semantic_candidates(self):
        numbered_local = self.local((self.clause("1", "Локально"),))
        unnumbered_source = self.source((self.clause("", "Официально"),))
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp)
            sources = cache / "sources"
            sources.mkdir()
            (sources / "ru-498.json").write_text(
                json.dumps(asdict(unnumbered_source), ensure_ascii=False),
                encoding="utf-8",
            )
            manifest = {
                "version": 1,
                "audit_at": "2026-07-22T00:00:00+00:00",
                "counts": {"russian": {"fetched": 1}, "english": {"not_mapped": 1}},
                "standards": [
                    {
                        "standard": "std498",
                        "title": "Журнал",
                        "local_path": "docs/std/498.md",
                        "russian": {"status": "fetched", "url": unnumbered_source.url, "snapshot": str(sources / "ru-498.json"), "error": None},
                        "english": {"status": "not_mapped", "url": None, "snapshot": None, "error": None},
                    }
                ],
            }
            structural = generate_structural_findings([numbered_local], cache)
            ledger = build_review_ledger([numbered_local], cache, manifest, structural)

        review = ledger["reviews"][0]
        self.assertEqual(review["status"], "изменена нумерация")
        self.assertEqual(review["confidence"], "high")
        self.assertEqual(review["english_status"], "not_mapped")
        self.assertTrue(review["observations"][0]["confirmed"])

        validate_review_ledger([numbered_local], ledger)
        ledger["reviews"] = []
        with self.assertRaisesRegex(ValueError, "review ids do not match"):
            validate_review_ledger([numbered_local], ledger)


class SemanticComparisonTests(unittest.TestCase):
    def clause(self, number: str, text: str) -> Clause:
        return Clause(number, "", "", text, (), ())

    def test_extracts_requirements_but_drops_scope_labels_and_code_examples(self):
        clauses = (
            self.clause(
                "",
                "Область применения: управляемое приложение, обычное приложение.",
            ),
            self.clause(
                "1",
                "Размер файла не должен превышать 10 Мб.\n"
                "Неправильно:\n"
                "Если Размер > 10 Тогда\n"
                "Сообщить(\"Ошибка\");\n"
                "КонецЕсли;\n"
                "Это ограничение защищает обмен от переполнения.",
            ),
        )

        units = extract_semantic_units(clauses, markup="source")

        self.assertEqual([unit.clause for unit in units], ["1", "1"])
        self.assertIn("10 Мб", units[0].text)
        self.assertNotIn("КонецЕсли", " ".join(unit.text for unit in units))

    def test_leading_outline_number_is_not_a_numeric_constraint(self):
        units = extract_semantic_units(
            (self.clause("1", "4 Если длина не задана, выберите разумный лимит."),),
            markup="source",
        )

        self.assertEqual(units[0].text, "Если длина не задана, выберите разумный лимит.")
        self.assertEqual(units[0].numeric_terms, ())

    def test_source_sentence_starting_with_inache_is_not_treated_as_code(self):
        units = extract_semantic_units(
            (
                self.clause(
                    "1",
                    "Иначе при количестве записей 10 млн и более возможно переполнение.",
                ),
            ),
            markup="source",
        )

        self.assertEqual(len(units), 1)
        self.assertIn("10 млн", units[0].text)

    def test_strips_markdown_code_but_keeps_information_style_paraphrase(self):
        clauses = (
            self.clause(
                "1",
                "Не делайте запросы внутри цикла.\n\n"
                "!!! example \"Пример\"\n\n"
                "```bsl\nДля Каждого Элемент Из Список Цикл\n"
                "Запрос.Выполнить();\nКонецЦикла;\n```",
            ),
        )

        units = extract_semantic_units(clauses, markup="markdown")

        self.assertEqual(
            [unit.text for unit in units],
            ["Не делайте запросы внутри цикла."],
        )

    def test_markdown_bullets_with_parentheses_are_separate_semantic_units(self):
        clauses = (
            self.clause(
                "1",
                """Подменю подходит, если:

- в журнале немного видов документов (до `6`);
- журнал часто используется в работе.
""",
            ),
        )

        units = extract_semantic_units(clauses, markup="markdown")

        self.assertEqual(
            [unit.text for unit in units],
            [
                "Подменю подходит, если:",
                "в журнале немного видов документов (до 6);",
                "журнал часто используется в работе.",
            ],
        )
        self.assertEqual(units[1].numeric_terms, ("6",))

    def test_markdown_html_decorations_do_not_hide_numeric_requirement(self):
        clauses = (
            self.clause(
                "1",
                'Используйте цвет RGB: 255,232,179 <span style="color:red"></span>.',
            ),
        )

        units = extract_semantic_units(clauses, markup="markdown")

        self.assertEqual(len(units), 1)
        self.assertIn("255,232,179", units[0].text)

    def test_inline_property_assignment_is_prose_not_code(self):
        clauses = (
            self.clause(
                "1",
                "Если значение не помещается (например, длинное имя), "
                "устанавливайте Размещение = Обрезать.",
            ),
        )

        units = extract_semantic_units(clauses, markup="markdown")

        self.assertEqual(len(units), 1)
        self.assertIn("Размещение = Обрезать", units[0].text)

    def test_keeps_numeric_example_that_explains_a_constraint(self):
        units = extract_semantic_units(
            (
                self.clause(
                    "2",
                    "Например, если знаменатель не может быть меньше 0.00001, "
                    "для результата достаточно 20 разрядов целой части.",
                ),
            ),
            markup="markdown",
        )

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].numeric_terms, ("1e-05", "20"))
        self.assertTrue(units[0].has_condition)

    def test_changed_number_and_modality_require_review_despite_high_similarity(self):
        source = extract_semantic_units(
            (self.clause("1", "Размер файла не должен превышать 10 Мб."),),
            markup="source",
        )
        local = extract_semantic_units(
            (self.clause("1", "Размер файла рекомендуется ограничить 20 Мб."),),
            markup="markdown",
        )

        comparison = compare_semantic_units(source, local, [[0.94]])

        self.assertEqual(comparison[0]["status"], "needs_review")
        self.assertEqual(
            set(comparison[0]["reasons"]),
            {"numeric_constraint_changed", "modality_changed"},
        )

    def test_extra_local_number_does_not_hide_preserved_source_constraint(self):
        source = extract_semantic_units(
            (self.clause("1", "Высота панели — 40 пикселей."),),
            markup="source",
        )
        local = extract_semantic_units(
            (self.clause("1", "Высота панели — 40 пикселей, браузера — 60 пикселей."),),
            markup="markdown",
        )

        comparison = compare_semantic_units(source, local, [[0.90]])

        self.assertNotIn("numeric_constraint_changed", comparison[0]["reasons"])

    def test_prefers_candidate_that_preserves_numeric_anchor(self):
        source = extract_semantic_units(
            (self.clause("1", "Точность результата может отличаться от 8."),),
            markup="source",
        )
        local = extract_semantic_units(
            (
                self.clause("1", "Точность результата может отличаться."),
                self.clause("2", "Поддерживается точность до 8 знаков."),
            ),
            markup="markdown",
        )

        comparison = compare_semantic_units(source, local, [[0.82, 0.72]])

        self.assertEqual(comparison[0]["local_unit"]["clause"], "2")
        self.assertNotIn("numeric_constraint_changed", comparison[0]["reasons"])

    def test_equivalent_paraphrase_is_preserved_when_anchors_match(self):
        source = extract_semantic_units(
            (self.clause("1", "Не следует выполнять запрос в цикле."),),
            markup="source",
        )
        local = extract_semantic_units(
            (self.clause("1", "Не делайте запросы внутри цикла."),),
            markup="markdown",
        )

        comparison = compare_semantic_units(source, local, [[0.78]])

        self.assertEqual(comparison[0]["status"], "preserved")
        self.assertEqual(comparison[0]["reasons"], [])

    def test_prefers_stronger_global_match_despite_different_clause_number(self):
        source = extract_semantic_units(
            (self.clause("1", "Используйте безопасный режим запуска."),),
            markup="source",
        )
        local = extract_semantic_units(
            (
                self.clause("1", "Включайте безопасный режим."),
                self.clause("2", "Используйте безопасный режим запуска."),
            ),
            markup="markdown",
        )

        comparison = compare_semantic_units(source, local, [[0.78, 1.0]])

        self.assertEqual(comparison[0]["local_unit"]["clause"], "2")
        self.assertEqual(comparison[0]["status"], "preserved")

    def test_difference_percentage_uses_weighted_confirmed_units(self):
        comparisons = [
            {"weight": 3, "decision": "changed"},
            {"weight": 7, "decision": "preserved"},
        ]

        self.assertEqual(semantic_difference_percent(comparisons), 30.0)

    def test_nli_confirms_numeric_contradiction_as_changed(self):
        comparison = {
            "similarity": 0.90,
            "reasons": ["numeric_constraint_changed"],
            "decision": None,
        }

        decided = decide_semantic_comparison(
            comparison,
            {"entailment": 0.12, "neutral": 0.08, "contradiction": 0.80},
        )

        self.assertEqual(decided["decision"], "changed")
        self.assertEqual(decided["decision_confidence"], "high")

    def test_nli_can_clear_lexical_false_positive(self):
        comparison = {
            "similarity": 0.62,
            "reasons": ["low_semantic_similarity", "modality_changed"],
            "decision": None,
        }

        decided = decide_semantic_comparison(
            comparison,
            {"entailment": 0.97, "neutral": 0.02, "contradiction": 0.01},
        )

        self.assertEqual(decided["decision"], "preserved")
        self.assertEqual(decided["decision_basis"], "nli_entailment")

    def test_nli_contradiction_alone_does_not_confirm_changed_meaning(self):
        comparison = {
            "similarity": 0.30,
            "reasons": ["low_semantic_similarity"],
            "source_unit": {
                "modality": "neutral",
                "has_condition": False,
                "has_exception": False,
            },
            "decision": None,
        }

        decided = decide_semantic_comparison(
            comparison,
            {"entailment": 0.01, "neutral": 0.01, "contradiction": 0.98},
        )

        self.assertIsNone(decided["decision"])
        self.assertEqual(decided["decision_basis"], "ambiguous")

    def test_uses_unnumbered_local_body_for_semantic_comparison(self):
        source = """###### #std498

# Заголовок

Не запускайте задание чаще одной минуты.

###### Источник

https://its.1c.ru/db/v8std#content:498
"""
        with tempfile.TemporaryDirectory() as temp:
            page = Path(temp) / "498.md"
            page.write_text(source, encoding="utf-8")
            standard = parse_local_standard(page, {})

            clauses = semantic_local_clauses(standard)

        self.assertEqual([clause.number for clause in clauses], [""])
        self.assertIn("одной минуты", clauses[0].text)
        self.assertNotIn("its.1c.ru", clauses[0].text)


class ManualSemanticReviewTests(unittest.TestCase):
    def semantic_payload(self):
        return {
            "version": 1,
            "audit_at": "2026-07-22T00:00:00+00:00",
            "threshold_percent": 5,
            "metric": {"name": "test"},
            "models": {},
            "standards": [
                {
                    "standard": "std498",
                    "title": "Пример",
                    "total_weight": 20,
                    "difference_lower_bound_percent": 10.0,
                    "unresolved_percent": 5.0,
                    "status": "смысл отличается >5%",
                    "changed_units": [
                        {"unit_id": "1:1", "weight": 2, "source_text": "A"},
                    ],
                }
            ],
        }

    def test_applies_confirmed_manual_decision_and_recomputes_percentage(self):
        reviewed = apply_manual_semantic_review(
            self.semantic_payload(),
            {
                "version": 1,
                "standards": {
                    "std498": {
                        "decision": "confirmed_gt_5",
                        "confirmed_unit_ids": ["1:1"],
                        "evidence_overrides": {
                            "1:1": {"local_text": "Локальная формулировка"}
                        },
                        "conclusion": "Требование отсутствует.",
                    }
                },
            },
        )

        item = reviewed["standards"][0]
        self.assertEqual(item["manual_difference_percent"], 10.0)
        self.assertEqual(item["semantic_status"], "смысл отличается >5%")
        self.assertEqual(item["confirmed_units"][0]["unit_id"], "1:1")
        self.assertEqual(
            item["confirmed_units"][0]["local_text"], "Локальная формулировка"
        )

    def test_requires_manual_decision_for_every_automatic_gt_5_candidate(self):
        with self.assertRaisesRegex(ValueError, "missing manual decisions"):
            apply_manual_semantic_review(
                self.semantic_payload(), {"version": 1, "standards": {}}
            )


class ReportRenderingTests(unittest.TestCase):
    def fixtures(self):
        manifest = {
            "audit_at": "2026-07-22T00:00:00+00:00",
            "counts": {
                "russian": {"fetched": 2},
                "english": {"fetched": 1, "not_mapped": 1},
            },
            "standards": [
                {
                    "standard": "std498",
                    "title": "Журнал <script>",
                    "local_path": "docs/std/498.md",
                    "russian": {"status": "fetched", "url": "https://its.1c.ru/498", "snapshot": "ru-498.json", "error": None},
                    "english": {"status": "fetched", "url": ENGLISH_URL, "snapshot": "en-498.json", "error": None},
                },
                {
                    "standard": "std499",
                    "title": "Исключения",
                    "local_path": "docs/std/499.md",
                    "russian": {"status": "fetched", "url": "https://its.1c.ru/499", "snapshot": "ru-499.json", "error": None},
                    "english": {"status": "not_mapped", "url": None, "snapshot": None, "error": None},
                },
            ],
        }
        reviews = {
            "audit_at": manifest["audit_at"],
            "reviews": [
                {
                    "standard": "std498",
                    "title": "Журнал <script>",
                    "status": "смысл отличается >5%",
                    "confidence": "high",
                    "numbering_status": "изменена нумерация",
                    "semantic_status": "смысл отличается >5%",
                    "semantic_difference_percent": 10.0,
                    "semantic_unresolved_percent": 2.0,
                    "semantic_conclusion": "Утрачено обязательное ограничение.",
                    "russian_status": "fetched",
                    "english_status": "fetched",
                    "checked_clauses": ["1"],
                    "observations": [
                        {
                            "kind": "extra_clause",
                            "clause": "1",
                            "russian_evidence": "[пункт отсутствует]",
                            "local_evidence": "Добавленный пункт",
                            "english_evidence": None,
                            "explanation": "Локальный номер отсутствует в русской ИТС.",
                            "confidence": "high",
                            "confirmed": True,
                        }
                    ],
                },
                {
                    "standard": "std499",
                    "title": "Исключения",
                    "status": "нужна ручная проверка",
                    "confidence": "needs_review",
                    "numbering_status": "совпадает",
                    "semantic_status": "смысл не проверен",
                    "semantic_difference_percent": None,
                    "semantic_unresolved_percent": None,
                    "semantic_conclusion": None,
                    "russian_status": "fetched",
                    "english_status": "not_mapped",
                    "checked_clauses": ["1"],
                    "observations": [],
                },
            ],
        }
        return manifest, reviews

    def test_markdown_contains_summary_rows_and_evidence(self):
        manifest, reviews = self.fixtures()
        report = render_markdown_report(manifest, reviews)
        self.assertIn("# Аудит всех стандартов", report)
        self.assertIn("Проверено стандартов: **2**", report)
        self.assertEqual(report.count("| std49"), 2)
        self.assertIn("нет английского источника", report)
        self.assertIn("Локальный номер отсутствует", report)
        self.assertIn("смысл отличается &gt;5%", render_html_report(manifest, reviews))

    def test_html_is_standalone_filterable_and_escapes_source_values(self):
        manifest, reviews = self.fixtures()
        report = render_html_report(manifest, reviews)
        self.assertEqual(report.count('class="audit-row"'), 2)
        self.assertIn('id="status-filter"', report)
        self.assertIn('id="text-filter"', report)
        self.assertIn("&lt;script&gt;", report)
        self.assertNotIn("<script src=", report)
        self.assertIn('<link rel="icon" href="data:,">', report)
        self.assertIn("нет английского источника", report)


if __name__ == "__main__":
    unittest.main()
