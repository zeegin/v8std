import json
import tomllib
import unittest
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]


def png_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG":
            raise AssertionError(f"not a PNG file: {path}")
        return image.size


class SiteInstallabilityTests(unittest.TestCase):
    def test_site_declares_web_app_manifest_and_touch_icon(self):
        template = (REPO_ROOT / "overrides/main.html").read_text(encoding="utf-8")
        self.assertIn('rel="manifest"', template)
        self.assertIn('href="{{ \'manifest.webmanifest\' | url | e }}"', template)
        self.assertIn('rel="apple-touch-icon"', template)
        self.assertIn('name="theme-color"', template)

    def test_manifest_defines_android_home_screen_icons(self):
        manifest_path = REPO_ROOT / "docs/manifest.webmanifest"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertTrue(manifest.get("name") or manifest.get("short_name"))
        self.assertEqual("/", manifest["id"])
        self.assertEqual("/", manifest["start_url"])
        self.assertEqual("/", manifest["scope"])
        self.assertEqual("standalone", manifest["display"])

        icons = {(icon["sizes"], icon.get("purpose", "any")): icon for icon in manifest["icons"]}
        for size in ("192x192", "512x512"):
            self.assertIn((size, "any"), icons)
        self.assertIn(("512x512", "maskable"), icons)

        for icon in manifest["icons"]:
            path = REPO_ROOT / "docs" / icon["src"].lstrip("/")
            expected = tuple(map(int, icon["sizes"].split("x")))
            self.assertEqual(expected, png_size(path), path)

    def test_config_uses_installable_icon_as_favicon(self):
        config = tomllib.loads(
            (REPO_ROOT / "zensical.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "assets/images/icon-192.png",
            config["project"]["theme"]["favicon"],
        )
        self.assertEqual(
            (192, 192),
            png_size(REPO_ROOT / "docs/assets/images/icon-192.png"),
        )


if __name__ == "__main__":
    unittest.main()
