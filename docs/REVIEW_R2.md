# Review R2: response and changes

**Type:** AI-assisted methodological review (ChatGPT), static code reading plus a check
against primary sources, received 2026-11-02. Not an instructor review; it confirms no
technique. The reviewer explicitly declined to propose tactical corrections. That is the
right boundary, and it is ours too.

**Verdict:** "revise". Source references are partly plausible; source-faithful
implementation and the optimization results are not proven by the package.

## Source spot check

| claim | check |
|---|---|
| MCWP 3-35.3 app. A describes buttonhook and pieing | confirmed (1998 edition, now MCRP 12-10B.1) |
| MCWP "Cross Method" §20f, p. A-34 | **not confirmed**; the name was not found in our search |
| FM 3-06.11 §3-22c-e, pp. 3-28-3-35, team sizes in table 3-1 | consistent with the table of contents; page level not checked |
| ATP 3-21.8 (2024, Change 1 2025) calls its techniques non-prescriptive | not checked |

## Points and responses

| point | response | status |
|---|---|---|
| "coded from source" contradicts the unvalidated notice | Status vocabulary changed: `adapted` / `model variant` / `unsourced`. No technique is "coded from source" any more. Limited penetration is `unsourced`; the combinations, pie + crisscross and deliberate are `model variant` (project names). | ✅ |
| ATP and MCWP missing from the source metadata | MCWP added in `tactics.py` and TACTICS.md, FM team-size passage cited for two-man; ATP not cited until checked | ✅ |
| Robustness mean mixes valid and invalid runs | `robust_eval` now reports `n`, `n_valid`, `mean` (all runs), `mean_valid` (valid runs only) | ✅ |
| Held-out separation is not auditable | [RUNLOG.md](RUNLOG.md): which results were known at which model state; all results so far marked exploratory; confirmatory rooms never evaluated | ✅ |
| Model changed after seeing results | stated explicitly in RUNLOG and the prereg: exploratory, not confirmatory | ✅ |
| H4 treats room x playbook as independent | H4 now tests on room level | ✅ |
| No multiple-testing rule | Holm correction over H1, H2, H4; H3 is descriptive | ✅ |
| "Best found" is not proven optimal | Already the wording everywhere; prereg requires a saturation check | ✅ (existing) |
| Incomplete reproduction package | Next package contains the full repo (code, tests, configuration) without `out/` | ✅ (`review_pkg_R3.zip`) |
| CONCEPT.md states an old model version | Note added; the current state is in RUNLOG | ✅ |
| Apartment report said "2 threats each" | Corrected: 2 threats per scenario over the whole apartment | ✅ |

**Assessment:** R2 found no new modelling error like the information leak in R1, but six
real inconsistencies in documentation and analysis plan. All of them are fixed.
