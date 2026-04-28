import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "scripts" / "v8std_mcp_server.py"

EXPECTED_TOOL_NAMES = [
    "v8std_search",
    "v8std_get_page",
    "v8std_get_related",
    "v8std_explain_snippet",
    "v8std_explain_diagnostics",
]

OPENAI_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
LOWER_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def registered_tool_names() -> list[str]:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    names: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr != "tool":
                continue

            for keyword in decorator.keywords:
                if keyword.arg != "name":
                    continue
                if not isinstance(keyword.value, ast.Constant):
                    continue
                if isinstance(keyword.value.value, str):
                    names.append(keyword.value.value)

    return names


class V8StdMcpServerToolNameTests(unittest.TestCase):
    def test_tool_names_are_openai_style(self):
        tool_names = registered_tool_names()

        self.assertEqual(tool_names, EXPECTED_TOOL_NAMES)
        for name in tool_names:
            self.assertRegex(name, LOWER_SNAKE_RE)
            self.assertRegex(name, OPENAI_TOOL_NAME_RE)

    def test_antigravity_prefixed_tool_names_stay_valid(self):
        prefix = "mcp_ai-v8std-ru_"

        for name in registered_tool_names():
            prefixed_name = f"{prefix}{name}"
            self.assertLessEqual(len(prefixed_name), 64)
            self.assertRegex(prefixed_name, OPENAI_TOOL_NAME_RE)


if __name__ == "__main__":
    unittest.main()
