from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEMPLATE = ROOT / "overrides" / "main.html"
CONFIG = ROOT / "zensical.toml"


class AnalyticsIntegrationTest(unittest.TestCase):
    def test_u_ingvar_scripts_replace_yandex_analytics(self):
        template = MAIN_TEMPLATE.read_text(encoding="utf-8")
        config = CONFIG.read_text(encoding="utf-8")

        extrahead = template.split("{% block extrahead %}", 1)[1].split("{% endblock %}", 1)[0]
        self.assertIn(
            '<script defer src="https://u.ingvar.pro/script.js" '
            'data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a"></script>',
            extrahead,
        )
        self.assertIn(
            '<script defer src="https://u.ingvar.pro/recorder.js" '
            'data-website-id="e6d9711e-3090-45e1-aa57-be1a9fe4567a" '
            'data-sample-rate="0.15" data-mask-level="moderate" '
            'data-max-duration="300000"></script>',
            extrahead,
        )
        combined = template + config
        self.assertNotIn("mc.yandex.ru", combined)
        self.assertNotIn("Yandex.Metrika", combined)
        self.assertNotIn("{% block analytics %}", template)


if __name__ == "__main__":
    unittest.main()
