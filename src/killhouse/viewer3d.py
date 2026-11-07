"""`killhouse-3d`: results.json -> standalone three.js viewer, fed with a replay document."""

from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path

from .replay import from_results, validate


def to_html(results: dict, source: str = "results.json") -> str:
    doc = from_results(results, source)
    problems = validate(doc)
    if problems:
        raise ValueError("invalid replay: " + "; ".join(problems[:3]))
    tpl = resources.files("killhouse").joinpath("viewer3d.html").read_text(encoding="utf-8")
    payload = json.dumps(doc, separators=(",", ":")).replace("</", "<\\/")
    return tpl.replace("/*__DATA__*/null", payload)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-3d")
    ap.add_argument("results", type=Path, help="results.json from killhouse-bench")
    ap.add_argument("--out", type=Path, help="default: viewer3d.html next to results.json")
    a = ap.parse_args(argv)
    out = a.out or a.results.with_name("viewer3d.html")
    data = json.loads(a.results.read_text(encoding="utf-8"))
    out.write_text(to_html(data, a.results.name), encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
