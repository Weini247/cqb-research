"""Analysis plan of the E1 preregistration (PREREG_E1_draft.md, sections 4 and 5) as code.

Reads the result files of `killhouse-bench --optimizer cem cmaes --seeds 5`, either
`results.json` or `rooms.partial.jsonl`, and computes reliability measures and H1 and H2. It runs
no simulation. H3 and H4 need other data; a p-value for H4 can be passed in for the Holm step.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np

from .room import generated_rooms, rooms_digest

FAMILIES = ("crisscross", "buttonhook", "pie+crisscross", "limited-penetration")
METHODS = ("cem", "cmaes")
CORNER_DIST = 1.6  # door centre at most this far from a side wall = corner-fed (H1)
H2_MIN_SHARE = 0.7
ALPHA = 0.05
N_BOOT = 10_000


def family(name: str) -> str:
    return name.replace("+dead-space", "")


def load_rooms(paths: list[Path]) -> list[dict]:
    """Rooms from result files, sorted by name. A room found twice must have equal results, so
    a repeated control room is accepted and a mismatch stops the analysis."""
    rooms: dict[str, dict] = {}
    for p in paths:
        text = Path(p).read_text(encoding="utf-8")
        if str(p).endswith(".jsonl"):
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            rows = json.loads(text)["rooms"]
        for r in rows:
            name = r["room"]["name"]
            if name in rooms and rooms[name]["doctrines"] != r["doctrines"]:
                raise ValueError(f"{name}: results differ between files")
            rooms[name] = r
    return [rooms[n] for n in sorted(rooms)]


def check_rooms(rows: list[dict], seed: int, n: int) -> str:
    """The loaded rooms must be exactly generated_rooms(seed, n); returns their digest."""
    want = generated_rooms(seed, n)
    a = [json.dumps(r["room"], sort_keys=True) for r in rows]
    b = [json.dumps(json.loads(json.dumps(r.to_dict())), sort_keys=True) for r in want]
    if a != b:
        missing = sorted({r.name for r in want} - {r["room"]["name"] for r in rows})
        raise ValueError(f"rooms differ from generated_rooms({seed}, {n}); missing: {missing}")
    return rooms_digest(want)


def door_side(room: dict) -> float:
    """Distance of the door centre from the nearer side wall."""
    c = sum(room["door"]) / 2
    return min(c, room["w"] - c)


def is_corner(room: dict) -> bool:
    return door_side(room) <= CORNER_DIST


def valid_pairs(rows: list[dict]) -> list[tuple[dict, dict]]:
    return [(r, d) for r in rows for d in r["doctrines"] if d["feasible"]]


def at_time_floor(r: dict, d: dict) -> bool:
    """No run left the playbook and it already has the fastest time of the pooled front."""
    return d["seeds_leaving"] == 0 and d["t_clear"] <= min(f[1] for f in r["front"]) + 1e-9


def sign_test(wins: int, n: int) -> float:
    """One-sided exact sign test: P(X >= wins) for X ~ Bin(n, 1/2)."""
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / 2**n if n else 1.0


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values."""
    out, run = {}, 0.0
    order = sorted(pvals, key=pvals.get)
    for i, k in enumerate(order):
        run = max(run, (len(order) - i) * pvals[k])
        out[k] = min(1.0, run)
    return out


def _ci(x: list[float]) -> list[float]:
    return [round(float(v), 4) for v in np.percentile(x, [2.5, 97.5])]


def corner_coefficient(gap, corner, width, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Least squares gap ~ corner-fed + room width, bootstrap over rooms.

    p is the share of resamples with a coefficient <= 0 (one-sided). Resamples containing only
    one door class cannot estimate the coefficient and are drawn again."""
    gap, corner, width = (np.asarray(v, float) for v in (gap, corner, width))
    X = np.c_[np.ones(len(gap)), corner, width]
    beta = np.linalg.lstsq(X, gap, rcond=None)[0]
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    while len(boot) < n_boot:
        i = rng.integers(0, len(gap), len(gap))
        if 0 < corner[i].sum() < len(i):
            boot.append(float(np.linalg.lstsq(X[i], gap[i], rcond=None)[0][1]))
    return {
        "coef_corner": round(float(beta[1]), 4),
        "coef_width": round(float(beta[2]), 4),
        "ci": _ci(boot),
        "p": float(np.mean(np.array(boot) <= 0)),
    }


def median_difference(a, b, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    boot = [
        float(np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))))
        for _ in range(n_boot)
    ]
    return {
        "n": [len(a), len(b)],
        "medians": [round(float(np.median(a)), 4), round(float(np.median(b)), 4)],
        "difference": round(float(np.median(a) - np.median(b)), 4),
        "ci": _ci(boot),
    }


def h1(rows: list[dict], n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Crisscross gap vs. door class: primary (pooled, adjusted for width) and secondary."""
    pts = [(r, d) for r, d in valid_pairs(rows) if family(d["name"]) == "crisscross"]
    corner = [is_corner(r["room"]) for r, _ in pts]
    width = [r["room"]["w"] for r, _ in pts]

    def fit(gap: list[float]) -> dict:
        return corner_coefficient(gap, corner, width, n_boot, seed)

    pooled = [d["gap_selected"] for _, d in pts]
    outer = [door_side(r["room"]) / r["room"]["w"] <= 1 / 3 for r, _ in pts]

    def split(flag: list[bool]) -> dict:
        a = [g for g, f in zip(pooled, flag, strict=True) if f]
        b = [g for g, f in zip(pooled, flag, strict=True) if not f]
        return median_difference(a, b, n_boot, seed)

    return {
        "n_rooms": len(pts),
        "primary": fit(pooled),
        "by_method": {m: fit([d["gap_by_method"][m] for _, d in pts]) for m in METHODS},
        "unadjusted": split(corner),
        "outer_third": split(outer),
    }


def h2(rows: list[dict]) -> dict:
    """Crisscross vs. buttonhook per room, within families, over rooms where both are valid."""

    def count(sel: list[dict]) -> dict:
        wins = losses = 0
        for r in sel:
            x = {family(d["name"]): d for d in r["doctrines"] if d["feasible"]}
            if "crisscross" in x and "buttonhook" in x:
                a, b = x["crisscross"]["risk_multi"], x["buttonhook"]["risk_multi"]
                wins += a < b
                losses += a > b
        n = wins + losses
        return {
            "wins": wins,
            "n": n,
            "share": round(wins / n, 4) if n else None,
            "p": sign_test(wins, n),
        }

    return {
        **count(rows),
        "corner_fed": count([r for r in rows if is_corner(r["room"])]),
        "centre_fed": count([r for r in rows if not is_corner(r["room"])]),
    }


def reliability(rows: list[dict], seed: int = 1) -> dict:
    """Descriptive reliability measures of section 4; none of them filters anything."""
    pairs = valid_pairs(rows)
    floor = [(r, d) for r, d in pairs if at_time_floor(r, d)]
    active = [d for _, d in pairs if d["seeds_leaving"] > 0]
    runs = [g for d in active for g in d["gap_per_seed"]]
    rng = np.random.default_rng(seed)
    within = []
    for d in active:  # proxy: how often would two halves of interchangeable runs agree?
        g = np.array(d["gap_per_seed"])
        h = len(g) // 2
        cuts = [rng.permutation(len(g)) for _ in range(200)]
        within.append(np.mean([abs(g[i[:h]].max() - g[i[h:]].max()) <= 0.05 for i in cuts]))

    def stable(sel: list[dict]) -> list[int]:
        return [sum(d["method_stable"] for d in sel), len(sel)]

    def best_of(k: int) -> float:
        per = [np.mean([max(c) for c in combinations(d["gap_per_seed"], k)]) for d in active]
        return round(float(np.mean(per)), 4)

    n_runs = len(active[0]["gap_per_seed"]) if active else 0
    return {
        "method_stable": stable([d for _, d in pairs]),
        "method_stable_by_family": {
            f: stable([d for _, d in pairs if family(d["name"]) == f]) for f in FAMILIES
        },
        "method_stable_corner_fed": stable([d for r, d in pairs if is_corner(r["room"])]),
        "method_stable_centre_fed": stable([d for r, d in pairs if not is_corner(r["room"])]),
        "rooms_all_stable": sum(
            all(d["method_stable"] for d in r["doctrines"] if d["feasible"]) for r in rows
        ),
        "interchangeable_proxy": round(float(np.mean(within)), 2) if within else None,
        "time_floor": [[r["room"]["name"], d["name"]] for r, d in floor],
        "runs_at_playbook": [sum(g < 0.005 for g in runs), len(runs)],
        "median_run_spread": round(
            float(np.median([max(d["gap_per_seed"]) - min(d["gap_per_seed"]) for d in active])), 4
        )
        if active
        else None,
        "best_of_k": {k: best_of(k) for k in (1, 5, n_runs) if 0 < k <= n_runs},
    }


def gaps(rows: list[dict]) -> dict:
    pairs = valid_pairs(rows)

    def summary(sel: list[dict]) -> dict:
        x = [d["gap_selected"] for d in sel]
        fr = sum(d["fratricide"] > 0 for d in sel)
        if not x:  # a family can be invalid in every room of a small set
            return {"n": 0}
        return {
            "n": len(x),
            "median": round(float(np.median(x)), 4),
            "mean": round(float(np.mean(x)), 4),
            "min": min(x),
            "max": max(x),
            "with_fratricide": fr,
        }

    return {
        "all": summary([d for _, d in pairs]),
        **{f: summary([d for _, d in pairs if family(d["name"]) == f]) for f in FAMILIES},
    }


def analyze(
    rows: list[dict], n_boot: int = N_BOOT, seed: int = 0, h4_p: float | None = None
) -> dict:
    """All results of the plan. Holm runs over H1, H2 and H4; without H4 it is provisional."""
    r1, r2 = h1(rows, n_boot, seed), h2(rows)
    pvals = {"H1": r1["primary"]["p"], "H2": r2["p"]}
    if h4_p is not None:
        pvals["H4"] = h4_p
    adj = holm(pvals)
    pairs = [(r, d) for r in rows for d in r["doctrines"]]
    return {
        "n_rooms": len(rows),
        "pairs": len(pairs),
        "valid_pairs": len(valid_pairs(rows)),
        "rooms_with_step": sum(
            any("dead-space" in d["name"] for d in r["doctrines"]) for r in rows
        ),
        "rooms_without_valid_technique": [
            r["room"]["name"] for r in rows if not any(d["feasible"] for d in r["doctrines"])
        ],
        "gaps": gaps(rows),
        "reliability": reliability(rows),
        "H1": {**r1, "p_holm": adj["H1"], "supported": adj["H1"] < ALPHA},
        "H2": {
            **r2,
            "p_holm": adj["H2"],
            "supported": adj["H2"] < ALPHA and (r2["share"] or 0) >= H2_MIN_SHARE,
        },
        "holm_final": h4_p is not None,
    }


def text(a: dict) -> str:
    """Short readable summary of `analyze`."""
    r, p, q = a["reliability"], a["H1"]["primary"], a["H2"]
    stable = r["method_stable"]
    lines = [
        f"rooms {a['n_rooms']}, valid pairs {a['valid_pairs']}/{a['pairs']}, "
        f"with dead-space step {a['rooms_with_step']}",
        f"gap: median {a['gaps']['all']['median'] * 100:.1f} %",
        f"method-stable {stable[0]}/{stable[1]}, rooms all stable {r['rooms_all_stable']}, "
        f"proxy {r['interchangeable_proxy']}, time floor {len(r['time_floor'])}",
        f"H1 corner-fed {p['coef_corner'] * 100:+.1f} points, CI "
        f"[{p['ci'][0] * 100:.1f}, {p['ci'][1] * 100:.1f}], p {p['p']:.4f}, "
        f"Holm {a['H1']['p_holm']:.4f}, supported {a['H1']['supported']}",
        f"H2 {q['wins']}/{q['n']} ({q['share']}), p {q['p']:.4f}, Holm {q['p_holm']:.4f}, "
        f"supported {q['supported']}",
    ]
    if not a["holm_final"]:
        lines.append("Holm is provisional: H4 is missing")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="killhouse-analyze")
    ap.add_argument("files", nargs="+", type=Path, help="results.json or rooms.partial.jsonl")
    ap.add_argument(
        "--generated",
        nargs=2,
        type=int,
        metavar=("SEED", "N"),
        help="require exactly the rooms of generated_rooms(SEED, N)",
    )
    ap.add_argument("--h4-p", type=float, help="one-sided p of H4 for the Holm step")
    ap.add_argument("--out", type=Path, help="write the full result as JSON")
    a = ap.parse_args(argv)
    rows = load_rooms(a.files)
    out = analyze(rows, h4_p=a.h4_p)
    if a.generated:
        out["rooms_digest"] = check_rooms(rows, *a.generated)
    print(text(out))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
