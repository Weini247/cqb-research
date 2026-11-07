"""Viewer smoke test in a headless browser (Chrome/Chromium/Edge, temporary profile).

Opens a generated viewer with ?selftest, which steps through every run, camera, figure style and
the split view and writes its findings into <pre id="selftest">. Skipped without a browser or
without network access to the three.js CDN.
"""

import json
import math
import os
import re
import shutil
import subprocess

import pytest

from killhouse.viewer3d import to_html

CANDIDATES = [
    "google-chrome",
    "chromium",
    "chromium-browser",
    "chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def browser() -> str | None:
    for c in CANDIDATES:
        path = shutil.which(c) or (c if os.path.isfile(c) else None)
        if path:
            return path
    return None


def results():
    steps, dt = 60, 0.1
    team = [
        {"name": n, "color": c, "height_m": 1.8, "radius_m": 0.25}
        for n, c in (("A", "#e5484d"), ("B", "#3e9fb0"))
    ]

    def run(name, speed):
        pos = [[[1.0 + speed * dt * k, 0.5], [3.0, 0.5 + 0.8 * dt * k]] for k in range(steps)]
        return {
            "name": name,
            "metrics": {"risk_multi": 0.5, "t_clear": 4.0, "feasible": True, "fratricide": 0.0},
            "pos": pos,
            "gaze": [[0.0, math.pi / 2]] * steps,
            "first_seen": [5, 30, steps],
        }

    return {
        "config": {"dt": dt, "half_fov_deg": 50.0, "objective": "risk_multi"},
        "team": team,
        "rooms": [
            {
                "room": {"name": "S", "w": 5.0, "d": 6.0, "door": [2.0, 3.0], "obstacles": []},
                "points": [[1.0, 1.0], [2.5, 3.0], [4.0, 5.0]],
                "replays": [run("walk", 1.2), run("fast", 1.9)],
            }
        ],
    }


@pytest.mark.skipif(browser() is None, reason="no Chrome/Chromium/Edge found")
def test_viewer_selftest_passes(tmp_path):
    page = tmp_path / "viewer.html"
    page.write_text(to_html(results()), encoding="utf-8")
    cmd = [
        browser(),
        "--headless=new",
        "--disable-gpu",
        "--enable-unsafe-swiftshader",
        "--use-angle=swiftshader",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={tmp_path / 'profile'}",
        "--virtual-time-budget=60000",
        "--dump-dom",
        page.as_uri() + "?selftest",
    ]
    dom = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180
    ).stdout
    found = re.findall(r'<pre id="selftest">(\{.*?)</pre>', dom, re.S)
    if not found:
        pytest.skip("no selftest output (three.js CDN unreachable or WebGL unavailable)")
    out = json.loads(found[-1].replace("&quot;", '"').replace("&amp;", "&"))
    assert out["ok"], out["errors"]
    assert len(out["runs"]) == 2 and not any(r["nonfinite"] for r in out["runs"])
    # the walk clip runs at the speed of the body (feet do not slide), within 10 %
    assert all(r["samples"] > 20 and r["footslide"] < 0.10 for r in out["runs"]), out["runs"]
    assert out["split_labels"] and out["png_bytes"] > 1000
