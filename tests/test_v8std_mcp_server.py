from __future__ import annotations

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

EXPECTED_TOOL_GUIDANCE = {
    "v8std_search": [
        "Use this when",
        "arbitrary phrase",
        "Do not use this first for code snippets",
        "diagnostic-code lists",
    ],
    "v8std_get_page": [
        "Use this when",
        "clean Markdown",
        "exact id",
        "After v8std_search",
    ],
    "v8std_get_related": [
        "Use this when",
        "from a known standard or diagnostic",
        "related standards",
        "diagnostics",
    ],
    "v8std_explain_snippet": [
        "Use this when",
        "short BSL or SDBL code fragment",
        "applicable standards",
        "Do not use it for ordinary prose",
    ],
    "v8std_explain_diagnostics": [
        "Use this when",
        "ACC",
        "BSLLS",
        "EDT",
        "standard clauses",
    ],
}

OPENAI_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
LOWER_SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def _constant_string(value: ast.AST) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def registered_tools() -> dict[str, str]:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    tools: dict[str, str] = {}

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

            name = None
            description = None
            for keyword in decorator.keywords:
                if keyword.arg == "name":
                    name = _constant_string(keyword.value)
                if keyword.arg == "description":
                    description = _constant_string(keyword.value)

            if name is not None and description is not None:
                tools[name] = description

    return tools


def registered_tool_names() -> list[str]:
    return list(registered_tools())


def server_instructions() -> str:
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "FastMCP":
            continue
        for keyword in node.keywords:
            if keyword.arg == "instructions":
                instructions = _constant_string(keyword.value)
                if instructions is not None:
                    return instructions

    return ""


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

    def test_server_instructions_teach_tool_selection(self):
        instructions = server_instructions()

        for expected in [
            "read-only",
            "does not run analyzers",
            "short BSL/SDBL snippet",
            "diagnostic codes",
            "clean Markdown",
            "arbitrary prose search",
        ]:
            self.assertIn(expected, instructions)

    def test_tool_descriptions_explain_when_to_use_them(self):
        tools = registered_tools()

        self.assertEqual(list(tools), EXPECTED_TOOL_NAMES)
        for tool_name, expected_phrases in EXPECTED_TOOL_GUIDANCE.items():
            description = tools[tool_name]
            for expected in expected_phrases:
                self.assertIn(expected, description)


if __name__ == "__main__":
    unittest.main()
