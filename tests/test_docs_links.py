import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_RELATIVE_MARKDOWN_LINK_RE = re.compile(r"\]\(/[^)\s]+\.md(?:#[^)]+)?\)")


class DocsLinksTests(unittest.TestCase):
    def test_docs_do_not_link_to_generated_markdown_artifacts_as_internal_pages(self):
        offenders = []
        for source in sorted((REPO_ROOT / "docs").rglob("*.md")):
            relative = source.relative_to(REPO_ROOT)
            for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
                if ROOT_RELATIVE_MARKDOWN_LINK_RE.search(line):
                    offenders.append(f"{relative}:{line_number}: {line.strip()}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
