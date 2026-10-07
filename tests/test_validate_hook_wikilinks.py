"""Check 5 bans substitution Unicode in prose, and a wikilink target is not
prose: it is a filename, and the link only resolves when it is spelled the way
the file is. A vault whose dated notes put an em-dash after the date got a
warning on every write that linked one, and the suggested rewrite to ` - `
would have broken the link. These pin the exemption and its edges.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from _bash import BASH

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks/validate-ai-first.sh"

# Built with chr() so this file stays ASCII, for test_no_banned_chars_in_instructions.py.
EM_DASH = chr(0x2014)
NBSP = chr(0xA0)
DATED = f"Dev Logs/2026-08-09 {EM_DASH} Harness pass"


def frontmatter(extra: str = "") -> str:
    return (
        f"---\ndate: 2026-10-07\ntype: concept\ntags:\n  - concept\nai-first: true\n{extra}---\n\n"
        "## For future agent\n"
    )


def run(vault: Path, note: Path):
    return subprocess.run(
        [BASH, str(HOOK)],
        input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(note)}}),
        env=dict(os.environ, OBSIDIAN_VAULT_PATH=str(vault)),
        capture_output=True, text=True,
    )


def message(result) -> str:
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["systemMessage"]


@pytest.fixture()
def vault(tmp_path):
    v = tmp_path / "vault"
    v.mkdir()
    return v


def check(vault: Path, body: str, extra_frontmatter: str = "") -> str:
    note = vault / "note.md"
    note.write_text(frontmatter(extra_frontmatter) + body, encoding="utf-8")
    return message(run(vault, note))


@pytest.mark.parametrize("link", [
    f"[[{DATED}]]",
    f"![[{DATED}]]",
    f"[[{DATED}#Findings]]",
    f"[[raw/2026-08-10 - [WIP] Release {EM_DASH} notes]]",
])
def test_a_dash_in_a_link_target_is_the_filename(vault, link):
    assert check(vault, f"See {link} for detail.\n") == ""


def test_a_link_in_frontmatter_is_a_filename(vault):
    assert check(vault, "Body.\n", f'relates_to:\n  - "[[{DATED}]]"\n') == ""


def test_the_alias_is_display_text_and_still_flagged(vault):
    assert "U+2014 em-dash" in check(vault, f"See [[{DATED}|the pass {EM_DASH} August]].\n")


def test_prose_next_to_a_link_is_still_flagged(vault):
    msg = check(vault, f"Read [[{DATED}]] first {EM_DASH} it has the counts.\n")
    assert "U+2014 em-dash" in msg


@pytest.mark.parametrize("line", [
    f"Type [[ then a name {EM_DASH} it autocompletes.",
    f"| Type [[ then a name {EM_DASH} pick | x |",
    f"Use `[[` to link {EM_DASH} see [[Home]].",
])
def test_a_bracket_pair_that_never_closes_is_prose(vault, line):
    assert "U+2014 em-dash" in check(vault, line + "\n")


def test_nbsp_in_a_link_target_is_still_flagged(vault):
    assert "U+00A0" in check(vault, f"See [[Dev Logs/2026-08-09{NBSP}Pass]].\n")
