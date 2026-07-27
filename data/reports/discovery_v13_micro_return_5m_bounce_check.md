# Discovery v13 — bid-ask-bounce / shared-price-point check on micro_return_5m

Generated 2026-07-27T04:41:12.960249+00:00.

`micro_return_5m` and every forward return share the same price P_t (verified below). Transient noise in P_t alone would produce exactly the reported mean-reversion pattern with no economic effect. This compares the original against a one-minute-gapped variant that shares no price point with the outcome. Purely diagnostic; does not change decision_rule_v1.

---

## 0. Sanity check — is the shared price point real?

Reconstructed `micro_return_5m` from the raw 1m CSV as (P_t - P_t-5)/P_t-5 for 3,000 candidates: **100.0% match the stored value** (tolerance 1e-5; correlation 1.0000). This confirms the numerator price P_t is exactly the `state_price` that every forward return is measured from -- the shared-price-point concern is real, not a misreading of the code.

---

## 1. Discovery (2020-2025): original vs. gapped

Correlation between the two variants: **+0.7707** (they cover overlapping 5-minute windows offset by one minute, so they are expected to be highly correlated -- if the effect is economic, both should show it; if it comes from the shared price point, only the original will).

**Original `micro_return_5m` (shares P_t with forward return)**

| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|---|---|
| 15m | 10,531 | 57.3% | +0.0551% | 10,519 | 44.9% | -0.0371% | +0.0922% |
| 1h | 10,531 | 55.4% | +0.0689% | 10,519 | 47.6% | -0.0250% | +0.0939% |
| 4h | 10,531 | 53.5% | +0.0739% | 10,519 | 50.2% | +0.0049% | +0.0690% |

**Gapped `(P_t-1 - P_t-6)/P_t-6` (shares NO price point)**

| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|---|---|
| 15m | 10,522 | 56.1% | +0.0445% | 10,522 | 46.0% | -0.0309% | +0.0754% |
| 1h | 10,522 | 55.0% | +0.0610% | 10,522 | 48.0% | -0.0216% | +0.0827% |
| 4h | 10,522 | 53.4% | +0.0691% | 10,522 | 50.6% | +0.0144% | +0.0546% |

---

## 2. Validation (2026): original vs. gapped

**Original `micro_return_5m`**

| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|---|---|
| 15m | 720 | 54.2% | +0.0256% | 655 | 49.2% | -0.0049% | +0.0305% |
| 1h | 720 | 52.2% | +0.0140% | 655 | 46.3% | -0.0333% | +0.0473% |
| 4h | 720 | 50.7% | +0.0209% | 655 | 49.2% | -0.0176% | +0.0385% |

**Gapped variant**

| Horizon | n (Q1) | Q1 win% | Q1 median | n (Q5) | Q5 win% | Q5 median | Spread (Q1-Q5) |
|---|---|---|---|---|---|---|---|
| 15m | 779 | 54.4% | +0.0250% | 710 | 48.7% | -0.0059% | +0.0309% |
| 1h | 779 | 51.1% | +0.0070% | 710 | 46.8% | -0.0423% | +0.0494% |
| 4h | 779 | 51.2% | +0.0189% | 710 | 49.7% | -0.0042% | +0.0231% |
