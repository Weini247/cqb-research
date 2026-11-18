"""Licence register: every third-party file is listed in THIRD_PARTY.md with its checksum."""

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "killhouse" / "assets"


def register() -> dict[str, tuple[str, str]]:
    rows = {}
    for line in (ROOT / "THIRD_PARTY.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| `([^`]+)` \|.*\| (CC0 1\.0) \| `([0-9a-f]{64})` \|", line)
        if m:
            rows[m.group(1)] = (m.group(2), m.group(3))
    return rows


def test_every_asset_is_registered_cc0_with_matching_checksum():
    reg = register()
    files = sorted(p.name for p in ASSETS.iterdir() if p.is_file())
    assert files, "asset folder is empty"
    for name in files:
        assert name in reg, f"{name} is not in THIRD_PARTY.md"
        licence, sha = reg[name]
        assert licence == "CC0 1.0"
        assert hashlib.sha256((ASSETS / name).read_bytes()).hexdigest() == sha, name


def test_register_lists_no_missing_files_and_licence_texts_exist():
    reg = register()
    assert set(reg) == {p.name for p in ASSETS.iterdir() if p.is_file()}
    texts = list((ROOT / "licenses").glob("kenney-*-License.txt"))
    assert len(texts) == 2 and all(
        "CC0" in t.read_text(encoding="utf-8", errors="replace") for t in texts
    )
