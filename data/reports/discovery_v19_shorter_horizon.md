# Discovery v19 — is 4h the right hold length?

Generated 2026-07-27T05:17:10.911738+00:00.

`decision_rule_v1`'s 4h target was frozen in Phase B because that was the horizon the LPL hypothesis was validated on, and has never been revisited. Same Option A logic, same signals, same fee/slippage assumptions; only hold length varies. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched.

---

## Hold length vs. realized outcome (Option A, same signals)

Round-trip cost is fixed at **0.2200%** (fees + the stated 5bps/side slippage assumption) regardless of hold length, so a shorter hold must produce proportionally more gross move to break even. `Gross median` is shown alongside the net figures to make that trade-off visible.

Trade count changes by design: a shorter hold frees the position sooner, so more signals become trades (Option A). These are therefore different trade sequences, not subsets — the same caveat discovery_v16 raised.

| Hold | n trades | Win rate | Gross median | Net median | Mean | P05 | Profit factor | Final equity | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| 15m | 3,276 | 36.3% | +0.0341% | -0.1859% | -0.1979% | -1.26% | 0.445 | 0.0014 | -99.86% |
| 30m | 3,276 | 40.6% | +0.0850% | -0.1350% | -0.1860% | -1.64% | 0.552 | 0.0019 | -99.81% |
| 60m | 3,276 | 44.1% | +0.0949% | -0.1251% | -0.1922% | -2.21% | 0.639 | 0.0013 | -99.87% |
| 120m | 1,832 | 47.8% | +0.1601% | -0.0599% | -0.1853% | -2.97% | 0.729 | 0.0243 | -97.59% |
| 240m (frozen baseline) | 1,064 | 51.4% | +0.2673% | +0.0473% | -0.1306% | -4.19% | 0.853 | 0.1731 | -82.94% |
| 480m | 674 | 54.0% | +0.4044% | +0.1844% | -0.0390% | -4.99% | 0.964 | 0.5139 | -67.70% |
| 720m | 526 | 52.3% | +0.3625% | +0.1425% | -0.0022% | -5.79% | 0.998 | 0.6374 | -65.16% |
| 1440m | 365 | 56.4% | +0.7379% | +0.5179% | +0.3718% | -6.76% | 1.255 | 2.2701 | -49.62% |
