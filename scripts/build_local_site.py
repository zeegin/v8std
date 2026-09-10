#!/usr/bin/env python3
"""Build local HTML from prepared canonical inputs in an isolated staging tree.

Does not call zensical_docs.sh: that wrapper regenerates the canonical corpus.
The release builder must prepare docs/ai and llms files before this step.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

from generate_mcp_snapshot import publish_snapshot
from v8std_mcp_snapshot_format import normalize_site_url


def local_config(text: str, site_url: str) -> str:
    text = re.sub(r'^(repo_url|repo_name|edit_uri) = .*\n', '', text, flags=re.M)
    text = re.sub(r'^site_url = .*$', 'site_url = ' + json.dumps(site_url), text, count=1, flags=re.M)
    text = text.replace('[project.theme]\n', '[project.theme]\nfont = false\n')
    text = re.sub(r'\[project.theme.font\]\n.*?(?=\n\[|\Z)', '', text, flags=re.S)
    text = re.sub(r'\[project.extra.consent(?:\.[^\]]+)?\]\n.*?(?=\n\[|\Z)', '', text, flags=re.S)
    text = text.replace('[project.extra]\n', '[project.extra]\nlocal_publication = true\n')
    text = text.replace('[project.plugins.social]\nenabled = true',
                        '[project.plugins.social]\nenabled = false')
    config = tomllib.loads(text)["project"]
    assert config["theme"]["font"] is False
    assert config["extra"]["local_publication"] is True
    return text


def build_local_site(root: Path, output: Path, site_url: str, source_sha: str) -> Path:
    root, output = root.resolve(), output.resolve()
    # Never replace a checkout input, public output, ancestor, or existing result.
    if output == root or output in root.parents or any(
            output == root / name or root / name in output.parents
            for name in ("docs", "scripts", "overrides", "site", "spec", "LICENSES")):
        raise ValueError("local output overlaps source or canonical site")
    if output.exists():
        raise ValueError("local output must not exist")
    site_url = normalize_site_url(site_url)
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("source SHA must be 40 lowercase hexadecimal characters")
    # All producers/build hooks run against this copy; no symlink back to inputs.
    with tempfile.TemporaryDirectory(prefix="v8std-local-build-") as temporary:
        stage = Path(temporary)
        for name in ("docs", "scripts", "overrides", "LICENSES"):
            shutil.copytree(root / name, stage / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("zensical.toml", "retrieval-rules.yml", "LICENSE"):
            shutil.copy2(root / name, stage / name)
        env = {**os.environ, "V8STD_REPO_ROOT": str(stage), "PYTHONPATH": str(stage)}
        def run(*args: str):
            subprocess.run([sys.executable, *args], cwd=stage, env=env, check=True)

        # Generate Markdown sidecars against canonical config without overwriting
        # any AI inputs. Snapshot bytes are the unchanged canonical producer's.
        run("-c", "from pathlib import Path; from scripts.generate_ai_artifacts import "
            "build_site_ai_index, write_site_markdown_pages; "
            "write_site_markdown_pages(build_site_ai_index(Path.cwd()), Path('sidecars'))")
        canonical = tomllib.loads((stage / "zensical.toml").read_text())["project"]["site_url"]
        publish_snapshot(stage / "docs", stage / "snapshot", source_sha, canonical)
        (stage / "zensical.toml").write_text(local_config(
            (stage / "zensical.toml").read_text(), site_url), encoding="utf-8")
        run("-m", "zensical", "build", "--strict")
        # Do not run the unrelated article-HTML protection gate here; the final
        # public strict wrapper retains that gate. This task checks local egress.
        shutil.copytree(stage / "sidecars", stage / "site", dirs_exist_ok=True)
        shutil.copytree(stage / "snapshot", stage / "site/ai/mcp/v1", dirs_exist_ok=True)
        run("scripts/publish_license_texts.py", "--root", str(stage), "--site", str(stage / "site"))
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage / "site", output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    print(build_local_site(args.root, args.output, args.site_url, args.source_sha))


if __name__ == "__main__":
    main()
