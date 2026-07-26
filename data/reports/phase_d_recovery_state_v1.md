# Phase D v1 — Recovery-state (Class D'), frozen definition on the real trade set

Generated 2026-07-26T16:13:00.915235+00:00.

Confirmatory descriptive step, not a position-management rule. Applies the definition frozen in phase_d_path_state_hypothesis.md SS11 -- Def 1 recovery, deep threshold -0.75% (midpoint of the frozen -0.5%/-1.0% band, not re-fit here), checkpoints 1h/2h/3h -- to `decision_rule_v1`'s actual Discovery (2020-2025) trades (LPL==Q1 & Vol==Q5), not the widened diagnostic population used to derive the definition. 2026 untouched (SS12: an execution-mechanic hypothesis has to exist before validation is looked at again). Cells with n < 15 are marked instead of reported.

---

## Outcome distribution by recovery state

| Time | State | n | P(Winner) | Median net return | Mean net return | P05 |
|---|---|---|---|---|---|---|
| 1h | 1: never deep | 637 | 60.4% | +0.3650% | +0.2802% | -2.51% |
| 1h | 2: deep, recovered | 218 | 50.9% | +0.0294% | +0.1315% | -4.48% |
| 1h | 3: deep, still impaired | 209 | 24.4% | -1.1844% | -1.6563% | -6.16% |
| 2h | 1: never deep | 519 | 67.1% | +0.5164% | +0.5930% | -1.79% |
| 2h | 2: deep, recovered | 286 | 57.7% | +0.1937% | +0.4713% | -2.76% |
| 2h | 3: deep, still impaired | 259 | 13.1% | -1.8885% | -2.2454% | -6.09% |
| 3h | 1: never deep | 450 | 74.0% | +0.7306% | +0.8413% | -1.02% |
| 3h | 2: deep, recovered | 354 | 57.1% | +0.1559% | +0.5623% | -1.87% |
| 3h | 3: deep, still impaired | 260 | 4.6% | -2.1207% | -2.7562% | -6.61% |
