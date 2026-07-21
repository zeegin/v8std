import tempfile
import unittest
from pathlib import Path

from scripts.atomic_files import atomic_write_text


class AtomicWriteTests(unittest.TestCase):
    def test_replaces_complete_utf8_file_without_leaving_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "pages.jsonl"
            target.write_text("old\n", encoding="utf-8")
            expected = "проверка\n" * 10_000

            atomic_write_text(target, expected)

            self.assertEqual(target.read_text(encoding="utf-8"), expected)
            self.assertEqual(list(target.parent.glob(".pages.jsonl.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
