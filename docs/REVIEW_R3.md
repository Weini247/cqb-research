# Review R3 (big picture): response

**Type:** AI-assisted methodological and strategic review (ChatGPT), static reading of the
full repository, no runs. Not an instructor review.

**Verdict:** viable as a methodological simulation study and research software. Novelty and
readiness for publication are not shown yet. "How close is doctrine to the optimum?" claims
too much. A stronger question: *How much do comparisons of coordinated search methods depend
on model assumptions, information access and evaluation protocol?*

## Reference spot check

All seven references are well-known, existing works (Guibas et al. 1999 IJCGA; Chvátal 1975
JCTB; Chin & Ntafos 1986 SoCG; Burgard et al. 2005 IEEE T-RO; Ilachinski 1997 CNA/ISAAC;
Sargent 2013 J. Simulation; Agarwal et al. 2021 NeurIPS). Bibliographic details are
plausible; page numbers and DOIs not checked individually.

## Done

| point | response |
|---|---|
| **Further selection bias:** best of the re-scored front = winner's curse | Fixed: **one** candidate per technique is chosen on planning scenarios, only that one is scored on held-out scenarios (`gap_selected`); best-of-front kept as optimistic secondary value |
| Rerun with an adequate budget and 2 seeds | Result: gaps 1-54 %, but seeds differ by up to 20 points. Claim "0 % for centre-fed doors" **retracted** (budget artefact) |
| ±0.04 claim contradicted by the table | Corrected (median 0.02, max 0.09) |
| "valid" ≠ "contact-free" | Wording fixed in E5 and BIG_PICTURE |
| Ranking chained with different denominators | Now reported as separate pairwise comparisons with denominators |
| Trade-off on different data bases | Now labelled a hypothesis |
| Price of predictability is partly structural | Effect size vs. structural property separated; grid = upper bound |
| Apartment reversal | Labelled a hypothesis (3 apartments, APT1 not fully cleared) |
| Regression test fixes an outcome direction | Docstring: protects the implementation, no evidence for H4 |
| R2 "all fixed" too strong | Corrected |
| Prereg ambiguous (median vs. mean, scope) | E1 = single rooms only, median over 5 seeds, single candidate per technique |
| Provenance per run | `results.json` now records `commit` (+dirty flag) and `backend` |
| Claims register | [CLAIMS.md](CLAIMS.md) |

## Strategic recommendations: decision pending

1. Change the main question to the methodological one above, with "doctrine vs. optimum" as
   the case study.
2. Defer stage 9 (discovering new tactics) for the first publication because of the dual-use
   risk; reframe stage 8 as civilian multi-robot search; stage 7 only after a stable evaluator.
3. A neutral repository name (e.g. `visibility-search-lab`).
4. Order: M1 consistent state of claims -> M2 domain-neutral reference cases and method
   check -> M3 a narrowly scoped reproducible study and release.
