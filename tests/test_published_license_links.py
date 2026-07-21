import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_license_texts import check_published_license_links, default_repo_root


REPO_ROOT = Path(__file__).resolve().parents[1]


class PublishedLicenseLinkTests(unittest.TestCase):
    def test_container_repo_root_comes_from_wrapper_environment(self):
        with patch.dict("os.environ", {"V8STD_REPO_ROOT": "/docs"}):
            self.assertEqual(default_repo_root(), Path("/docs"))

    def test_strict_build_publishes_every_local_third_party_license_link(self):
        checked = check_published_license_links(REPO_ROOT, REPO_ROOT / "site")

        self.assertEqual(
            checked,
            {
                "EPL-2.0.txt",
                "GPL-3.0.txt",
                "LGPL-3.0.txt",
            },
        )


if __name__ == "__main__":
    unittest.main()
