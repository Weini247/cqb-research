"""Analysis plan of the E1 preregistration (PREREG_E1_draft.md, sections 4 and 5) as code.

Reads the result files of `killhouse-bench --optimizer cem cmaes --seeds 5`, either
`results.json` or `rooms.partial.jsonl`, and computes reliability measures and H1 and H2, the
whole test family of E1. It runs no simulation.
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
MAX_DRAWS = 20  # bootstrap gives up after MAX_DRAWS * n_boot resamples


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


def risk(d: dict) -> float:
    """Unrounded held-out risk; older result files hold only the rounded value."""
    return d.get("risk_exact", d["risk_multi"])


def gap_pairs(rows: list[dict]) -> list[tuple[dict, dict]]:
    """Valid pairs with a defined gap (it is undefined if the technique has risk 0)."""
    return [(r, d) for r, d in valid_pairs(rows) if d["gap_selected"] is not None]


def no_improvement(r: dict, d: dict) -> bool:
    """No run found an improvement and the playbook has the fastest time of the pooled front.

    This does not show a structural limit: search failure is not excluded."""
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

    p is the share of resamples with a coefficient <= 0 (one-sided). Resamples that cannot
    estimate the coefficient are drawn again, up to a limit. If the data or too many resamples
    cannot estimate it, the result is not estimable and p is 1."""
    gap, corner, width = (np.asarray(v, float) for v in (gap, corner, width))
    X = np.c_[np.ones(len(gap)), corner, width]
    fail = {"estimable": False, "coef_corner": None, "coef_width": None, "ci": None, "p": 1.0}
    if len(gap) < 4 or np.linalg.matrix_rank(X) < 3:
        return fail
    beta = np.linalg.lstsq(X, gap, rcond=None)[0]
    rng = np.random.default_rng(seed)
    boot: list[float] = []
    for _ in range(MAX_DRAWS * n_boot):
        i = rng.integers(0, len(gap), len(gap))
        if np.linalg.matrix_rank(X[i]) == 3:
            boot.append(float(np.linalg.lstsq(X[i], gap[i], rcond=None)[0][1]))
            if len(boot) == n_boot:
                break
    else:
        return fail
    return {
        "estimable": True,
        "coef_corner": float(beta[1]),
        "coef_width": float(beta[2]),
        "ci": _ci(boot),
        "p": float(np.mean(np.array(boot) <= 0)),
    }


def median_difference(a, b, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    if not a or not b:
        return {"n": [len(a), len(b)], "medians": None, "difference": None, "ci": None}
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
    pts = [(r, d) for r, d in gap_pairs(rows) if family(d["name"]) == "crisscross"]
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

    def span(flag: bool) -> list[float] | None:
        w = [v for v, c in zip(width, corner, strict=True) if c == flag]
        return [min(w), max(w)] if w else None

    return {
        "n_rooms": len(pts),
        "n_corner_fed": sum(corner),
        "width_range": {"corner_fed": span(True), "centre_fed": span(False)},
        "primary": fit(pooled),
        "by_method": {m: fit([d["gap_by_method"][m] for _, d in pts]) for m in METHODS},
        "unadjusted": split(corner),
        "outer_third": split(outer),
    }


def h2(rows: list[dict]) -> dict:
    """Crisscross vs. buttonhook per room, only in rooms where both are valid.

    The sign test excludes ties; the share uses all rooms where both are valid."""

    def count(sel: list[dict]) -> dict:
        wins = losses = ties = invalid = 0
        for r in sel:
            x = {family(d["name"]): d for d in r["doctrines"] if d["feasible"]}
            if "crisscross" in x and "buttonhook" in x:
                a, b = risk(x["crisscross"]), risk(x["buttonhook"])
                wins += a < b
                losses += a > b
                ties += a == b
            else:
                invalid += 1
        both = wins + losses + ties
        return {
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "both_valid": both,
            "not_both_valid": invalid,
            "share": wins / both if both else None,
            "p": sign_test(wins, wins + losses),
        }

    return {
        **count(rows),
        "corner_fed": count([r for r in rows if is_corner(r["room"])]),
        "centre_fed": count([r for r in rows if not is_corner(r["room"])]),
    }


def reliability(rows: list[dict]) -> dict:
    """Descriptive reliability measures of section 4; none of them filters anything."""
    pairs = gap_pairs(rows)
    active = [d for _, d in pairs if d["seeds_leaving"] > 0]
    runs = [g for d in active for g in d["gap_per_seed"]]

    def stable(sel: list[dict]) -> list[int]:
        return [sum(bool(d["method_stable"]) for d in sel), len(sel)]

    def best_of(k: int) -> float:
        per = [np.mean([max(c) for c in combinations(d["gap_per_seed"], k)]) for d in active]
        return float(np.mean(per))

    with_valid = [[d for d in r["doctrines"] if d["feasible"]] for r in rows]
    with_valid = [x for x in with_valid if x]
    n_runs = len(active[0]["gap_per_seed"]) if active else 0
    spread = [max(d["gap_per_seed"]) - min(d["gap_per_seed"]) for d in active]
    return {
        "method_stable": stable([d for _, d in pairs]),
        "method_stable_by_family": {
            f: stable([d for _, d in pairs if family(d["name"]) == f]) for f in FAMILIES
        },
        "method_stable_corner_fed": stable([d for r, d in pairs if is_corner(r["room"])]),
        "method_stable_centre_fed": stable([d for r, d in pairs if not is_corner(r["room"])]),
        "rooms_all_stable": [
            sum(all(d["method_stable"] for d in x) for x in with_valid),
            len(with_valid),
        ],
        "no_improvement": [
            [r["room"]["name"], d["name"]] for r, d in pairs if no_improvement(r, d)
        ],
        "runs_at_playbook": [sum(g < 0.005 for g in runs), len(runs)],
        "median_run_spread": float(np.median(spread)) if spread else None,
        "best_of_k": {k: best_of(k) for k in (1, 5, n_runs) if 0 < k <= n_runs},
    }


def gaps(rows: list[dict]) -> dict:
    pairs = gap_pairs(rows)

    def summary(sel: list[dict]) -> dict:
        x = [d["gap_selected"] for d in sel]
        fr = sum(d["fratricide"] > 0 for d in sel)
        if not x:  # a family can be invalid in every room of a small set
            return {"n": 0}
        return {
            "n": len(x),
            "median": float(np.median(x)),
            "mean": float(np.mean(x)),
            "min": min(x),
            "max": max(x),
            "with_fratricide": fr,
        }

    return {
        "all": summary([d for _, d in pairs]),
        **{f: summary([d for _, d in pairs if family(d["name"]) == f]) for f in FAMILIES},
    }


def analyze(rows: list[dict], n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """All results of the plan. H1 and H2 are the whole test family of the Holm step."""
    r1, r2 = h1(rows, n_boot, seed), h2(rows)
    adj = holm({"H1": r1["primary"]["p"], "H2": r2["p"]})
    pairs = [(r, d) for r in rows for d in r["doctrines"]]
    return {
        "n_rooms": len(rows),
        "pairs": len(pairs),
        "valid_pairs": len(valid_pairs(rows)),
        "undefined_gaps": len(valid_pairs(rows)) - len(gap_pairs(rows)),
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
    }


def text(a: dict) -> str:
    """Short readable summary of `analyze`."""
    r, p, q = a["reliability"], a["H1"]["primary"], a["H2"]
    stable, rooms = r["method_stable"], r["rooms_all_stable"]
    h1_line = (
        f"H1 corner-fed {p['coef_corner'] * 100:+.1f} points, CI "
        f"[{p['ci'][0] * 100:.1f}, {p['ci'][1] * 100:.1f}], p {p['p']:.4f}, "
        if p["estimable"]
        else "H1 not estimable, "
    )
    return "\n".join(
        [
            f"rooms {a['n_rooms']}, valid pairs {a['valid_pairs']}/{a['pairs']}, "
            f"with dead-space step {a['rooms_with_step']}",
            f"gap: median {a['gaps']['all'].get('median', 0) * 100:.1f} %",
            f"method-stable {stable[0]}/{stable[1]}, rooms all stable {rooms[0]}/{rooms[1]}, "
            f"no improvement at the fastest time {len(r['no_improvement'])}",
            h1_line + f"Holm {a['H1']['p_holm']:.4f}, supported {a['H1']['supported']}",
            f"H2 {q['wins']}/{q['both_valid']} ({q['share']}), ties {q['ties']}, "
            f"not both valid {q['not_both_valid']}, p {q['p']:.4f}, Holm {q['p_holm']:.4f}, "
            f"supported {q['supported']}",
        ]
    )


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
    ap.add_argument("--out", type=Path, help="write the full result as JSON")
    a = ap.parse_args(argv)
    rows = load_rooms(a.files)
    out = analyze(rows)
    if a.generated:
        out["rooms_digest"] = check_rooms(rows, *a.generated)
    print(text(out))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
