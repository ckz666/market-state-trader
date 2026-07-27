# Discovery v14 — gap decay and volatility conditioning of micro_return_5m

Generated 2026-07-27T04:46:13.791728+00:00.

Two follow-ups to discovery_v13: (A) how the effect decays as the signal window is moved further from the entry price, and (B) whether it strengthens with volatility the way LPL does. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched. Cells with n < 30 are marked instead of reported.

---

## A. Gap decay — how fast does the effect fade as the signal ages?

Q1-vs-Q5 median spread for the same 5-minute window ending `gap` minutes before the state candle. gap=0 is the original `micro_return_5m` (shares P_t with the outcome); every gap >= 1 shares no price point with it.

| Gap (min) | 15m | 1h | 4h |
|---|---|---|---|
| 0 (original) | +0.0921% | +0.0940% | +0.0693% |
| 1 | +0.0754% | +0.0827% | +0.0546% |
| 2 | +0.0653% | +0.0697% | +0.0575% |
| 3 | +0.0628% | +0.0637% | +0.0539% |
| 5 | +0.0494% | +0.0635% | +0.0835% |
| 10 | +0.0191% | +0.0166% | +0.0154% |
| 15 | +0.0154% | +0.0121% | +0.0014% |

A smooth monotone decline is consistent with a real, decaying short-horizon effect. A cliff right after gap=0 would instead point to the shared-price artifact still dominating.


---

## B1. Conditioned on `volatility_atr_norm` (1h ATR — the same variable LPL uses)

If `micro_return_5m`'s spread widens with volatility the way LPL's does, both factors want the same high-volatility regime — which would matter for whether they can be combined or compete for the same trades.


**Horizon 15m**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 785 | +0.0444% | 768 | -0.0145% | +0.0589% |
| Q2 | 1,571 | +0.0422% | 1,536 | -0.0273% | +0.0695% |
| Q3 | 2,110 | +0.0499% | 2,111 | -0.0335% | +0.0834% |
| Q4 | 2,612 | +0.0567% | 2,606 | -0.0512% | +0.1079% |
| Q5 | 3,453 | +0.0824% | 3,498 | -0.0421% | +0.1246% |

**Horizon 1h**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 785 | +0.0665% | 768 | -0.0204% | +0.0869% |
| Q2 | 1,571 | +0.0442% | 1,536 | -0.0225% | +0.0667% |
| Q3 | 2,110 | +0.0459% | 2,111 | -0.0444% | +0.0903% |
| Q4 | 2,612 | +0.0808% | 2,606 | -0.0249% | +0.1057% |
| Q5 | 3,453 | +0.1090% | 3,498 | -0.0119% | +0.1208% |

**Horizon 4h**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 785 | +0.0907% | 768 | +0.0406% | +0.0501% |
| Q2 | 1,571 | +0.0017% | 1,536 | -0.0134% | +0.0151% |
| Q3 | 2,110 | +0.0650% | 2,111 | -0.0283% | +0.0933% |
| Q4 | 2,612 | +0.0679% | 2,606 | -0.0002% | +0.0681% |
| Q5 | 3,453 | +0.1593% | 3,498 | +0.0559% | +0.1034% |

---

## B2. Conditioned on `micro_volatility_1m` (1m realized vol — timeframe-matched)

The timeframe-matched analogue. Weak on its own in discovery_v10, but LPL's volatility conditioning was also only visible as an interaction, not a standalone effect.


**Horizon 15m**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 497 | +0.0183% | 506 | -0.0249% | +0.0432% |
| Q2 | 1,405 | +0.0307% | 1,346 | -0.0394% | +0.0701% |
| Q3 | 2,103 | +0.0420% | 2,070 | -0.0401% | +0.0822% |
| Q4 | 2,773 | +0.0653% | 2,812 | -0.0297% | +0.0950% |
| Q5 | 3,753 | +0.0925% | 3,785 | -0.0420% | +0.1345% |

**Horizon 1h**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 497 | +0.0167% | 506 | -0.0445% | +0.0612% |
| Q2 | 1,405 | +0.0455% | 1,346 | -0.0365% | +0.0821% |
| Q3 | 2,103 | +0.0473% | 2,070 | -0.0166% | +0.0639% |
| Q4 | 2,773 | +0.0753% | 2,812 | -0.0313% | +0.1066% |
| Q5 | 3,753 | +0.1116% | 3,785 | -0.0155% | +0.1271% |

**Horizon 4h**

| Volatility | n (Q1) | Q1 median | n (Q5) | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|
| Q1 | 497 | +0.0344% | 506 | -0.0111% | +0.0455% |
| Q2 | 1,405 | +0.0269% | 1,346 | -0.0285% | +0.0554% |
| Q3 | 2,103 | +0.0399% | 2,070 | -0.0092% | +0.0491% |
| Q4 | 2,773 | +0.1021% | 2,812 | +0.0240% | +0.0780% |
| Q5 | 3,753 | +0.1481% | 3,785 | +0.0290% | +0.1191% |
