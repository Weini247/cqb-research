"""`killhouse-3d`: results.json -> standalone three.js viewer, fed with a replay document.

Furniture of residences and training houses is drawn with CC0 models (Kenney, see THIRD_PARTY.md)
where one fits; only the models a scene needs are embedded, so the page stays a single file.
"""

from __future__ import annotations

import argparse
import base64
import json
from importlib import resources
from pathlib import Path

from .replay import from_results, validate

# furniture kind -> model files (assets/); the viewer falls back to its own shapes otherwise
MODEL_FILES = {
    "bed": ["bedDouble.glb", "bedSingle.glb"],
    "sofa": ["loungeSofa.glb", "loungeSofaLong.glb"],
    "table": ["table.glb", "tableCoffee.glb"],
    "desk": ["desk.glb"],
    "counter": ["kitchenCabinet.glb", "kitchenSink.glb"],
    "island": ["kitchenBar.glb"],
    "fridge": ["kitchenFridgeLarge.glb"],
    "shelf": ["bookcaseOpen.glb"],
    "wardrobe": ["bookcaseClosedDoors.glb"],
    "bath": ["bathtub.glb"],
    "cabinet": ["bathroomCabinetDrawer.glb"],
    "car": ["sedan.glb", "suv.glb", "hatchback-sports.glb", "car-colormap.png"],
}


def models_for(doc: dict) -> dict[str, str]:
    """Base64 of the model files needed by the furniture kinds in the replay document."""
    kinds = {
        b[4] for scene in doc["scenes"] for b in scene["environment"].get("boxes", []) if len(b) > 5
    }
    folder = resources.files("killhouse").joinpath("assets")
    out = {}
    for kind in sorted(kinds):
        for name in MODEL_FILES.get(kind, []):
            out[name] = base64.b64encode(folder.joinpath(name).read_bytes()).decode("ascii")
    return out


def to_html(results: dict, source: str = "results.json") -> str:
    doc = from_results(results, source)
    problems = validate(doc)
    if problems:
        raise ValueError("invalid replay: " + "; ".join(problems[:3]))
    tpl = resources.files("killhouse").joinpath("viewer3d.html").read_text(encoding="utf-8")
    payload = json.dumps(doc, separators=(",", ":")).replace("</", "<\\/")
    models = json.dumps(models_for(doc), separators=(",", ":"))
    return tpl.replace("/*__DATA__*/null", payload).replace("/*__MODELS__*/null", models)


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
