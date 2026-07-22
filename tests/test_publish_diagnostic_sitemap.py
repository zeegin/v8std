import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from scripts.diagnostic_inventory import load_diagnostic_inventory


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/publish_diagnostic_sitemap.py"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def inventory_urls():
    source_catalog = json.loads(
        (REPO_ROOT / "data/diagnostic-sources.json").read_text(encoding="utf-8")
    )
    diagnostics = {
        family["family"]: [item["id"] for item in family["diagnostics"]]
        for family in source_catalog["families"]
    }
    diagnostics["acc"] = [
        item["code"]
        for item in json.loads(
            (REPO_ROOT / "data/acc-diagnostics.json").read_text(encoding="utf-8")
        )["diagnostics"]
    ]
    return {
        f"https://v8std.ru/diagnostics/{family}/{diagnostic_id}/"
        for family, diagnostic_ids in diagnostics.items()
        for diagnostic_id in diagnostic_ids
    }


def sitemap_locations(path):
    root = ElementTree.parse(path).getroot()
    return [
        node.text
        for node in root.findall(f"{{{SITEMAP_NAMESPACE}}}url/{{{SITEMAP_NAMESPACE}}}loc")
    ]


class PublishDiagnosticSitemapTests(unittest.TestCase):
    def test_inventory_rejects_non_string_diagnostic_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            data_dir = repo_root / "data"
            data_dir.mkdir()
            (data_dir / "diagnostic-sources.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "families": [
                            {
                                "family": "bslls",
                                "diagnostics": [{"id": None}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (data_dir / "acc-diagnostics.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "diagnostics": [{"code": "1"}],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "diagnostic id"):
                load_diagnostic_inventory(repo_root)

    def test_cli_preserves_existing_entries_and_adds_unique_inventory_urls_idempotently(self):
        expected_diagnostics = inventory_urls()

        with tempfile.TemporaryDirectory() as temp_dir:
            sitemap = Path(temp_dir) / "sitemap.xml"
            sitemap.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://v8std.ru/</loc>
    <lastmod>2026-07-22</lastmod>
  </url>
  <url><loc>https://v8std.ru/std/437/</loc></url>
  <url><loc>https://v8std.ru/</loc></url>
</urlset>
                """,
                encoding="utf-8",
            )
            sitemap.chmod(0o644)

            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--root",
                str(REPO_ROOT),
                "--sitemap",
                str(sitemap),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)

            first_payload = sitemap.read_bytes()
            self.assertEqual(stat.S_IMODE(sitemap.stat().st_mode), 0o644)
            locations = sitemap_locations(sitemap)
            location_set = set(locations)
            self.assertEqual(len(locations), len(location_set))
            self.assertEqual(
                location_set,
                expected_diagnostics
                | {"https://v8std.ru/", "https://v8std.ru/std/437/"},
            )

            root = ElementTree.parse(sitemap).getroot()
            home = next(
                node
                for node in root.findall(f"{{{SITEMAP_NAMESPACE}}}url")
                if node.findtext(f"{{{SITEMAP_NAMESPACE}}}loc")
                == "https://v8std.ru/"
            )
            self.assertEqual(
                home.findtext(f"{{{SITEMAP_NAMESPACE}}}lastmod"),
                "2026-07-22",
            )

            second = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(sitemap.read_bytes(), first_payload)


if __name__ == "__main__":
    unittest.main()
