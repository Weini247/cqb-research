"""`killhouse-3d`: bench results.json -> standalone three.js greybox viewer."""

from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path

KEEP = ("room", "points", "replays")


def to_html(results: dict) -> str:
    data = {
        "config": results["config"],
        "team": results["team"],
        "rooms": [{k: r[k] for k in KEEP} for r in results["rooms"]],
    }
    tpl = resources.files("killhouse").joinpath("viewer3d.html").read_text(encoding="utf-8")
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return tpl.replace("/*__DATA__*/null", payload)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-3d")
    ap.add_argument("results", type=Path, help="results.json from killhouse-bench")
    ap.add_argument("--out", type=Path, help="default: viewer3d.html next to results.json")
    a = ap.parse_args(argv)
    out = a.out or a.results.with_name("viewer3d.html")
    out.write_text(to_html(json.loads(a.results.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
