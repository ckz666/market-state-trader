# Discovery Analysis Report v5 — Local Price Location x Volatility deep dive

Generated 2026-07-26T14:01:29.674437+00:00 from data/historical_candidates.json.

Focused follow-up to v4's strongest finding (LPL x volatility interaction, residual/spread ratio 30%). Deliberately not crossing more dimensions — per the project discussion, understanding this one relationship in depth first.

---

## 1. LPL x Volatility at quintile resolution, all horizons

For each volatility quintile: LPL Q1 (lowest) median return, LPL Q5 (highest) median return, and the spread between them — does the LPL effect grow linearly with volatility, threshold, or reverse at the extreme?

**15m**

| Volatility | n (LPL=Q1) | LPL=Q1 median | n (LPL=Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,166 | +0.0226% | 1,248 | -0.0066% | -0.0293% |
| Q2 | 1,772 | +0.0307% | 1,781 | -0.0131% | -0.0438% |
| Q3 | 2,163 | +0.0325% | 2,393 | -0.0165% | -0.0490% |
| Q4 | 2,809 | +0.0252% | 2,900 | -0.0258% | -0.0510% |
| Q5 | 3,568 | +0.0410% | 3,155 | -0.0239% | -0.0649% |

**30m**

| Volatility | n (LPL=Q1) | LPL=Q1 median | n (LPL=Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,166 | +0.0318% | 1,248 | -0.0182% | -0.0500% |
| Q2 | 1,772 | +0.0431% | 1,781 | -0.0300% | -0.0731% |
| Q3 | 2,163 | +0.0554% | 2,393 | -0.0186% | -0.0740% |
| Q4 | 2,809 | +0.0436% | 2,900 | -0.0245% | -0.0681% |
| Q5 | 3,568 | +0.0827% | 3,155 | -0.0329% | -0.1155% |

**1h**

| Volatility | n (LPL=Q1) | LPL=Q1 median | n (LPL=Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,166 | +0.0304% | 1,248 | -0.0274% | -0.0578% |
| Q2 | 1,772 | +0.0432% | 1,781 | -0.0314% | -0.0746% |
| Q3 | 2,163 | +0.0611% | 2,393 | -0.0308% | -0.0919% |
| Q4 | 2,809 | +0.0565% | 2,900 | -0.0316% | -0.0881% |
| Q5 | 3,568 | +0.0899% | 3,155 | -0.0272% | -0.1171% |

**4h**

| Volatility | n (LPL=Q1) | LPL=Q1 median | n (LPL=Q5) | LPL=Q5 median | Spread (Q5-Q1) |
|---|---|---|---|---|---|
| Q1 | 1,166 | +0.0584% | 1,248 | -0.0359% | -0.0943% |
| Q2 | 1,772 | +0.0633% | 1,781 | -0.0537% | -0.1170% |
| Q3 | 2,163 | +0.1137% | 2,393 | -0.0749% | -0.1886% |
| Q4 | 2,809 | +0.1319% | 2,900 | -0.0567% | -0.1886% |
| Q5 | 3,568 | +0.2221% | 3,155 | -0.0988% | -0.3209% |


---

## 2. Volatility LEVEL vs. CHANGE

Within the highest volatility quintile only (Q5 — where v4/section 1 show the strongest amplification): does it matter whether ATR got there by RISING over the prior 24h, or has just been sitting high? atr_change_24h = atr_norm - atr_norm 24h ago.

Within volatility=Q5: 6,841 rows with ATR rising over 24h, 4,640 rows with ATR flat/falling.

**15m**

| ATR 24h trend | LPL | n | Median | Win Rate |
|---|---|---|---|---|
| rising | Q1 | 2,675 | +0.0303% | 52.3% |
| rising | Q5 | 1,638 | -0.0248% | 47.3% |
| flat/falling | Q1 | 893 | +0.0802% | 56.4% |
| flat/falling | Q5 | 1,517 | -0.0208% | 47.9% |

**30m**

| ATR 24h trend | LPL | n | Median | Win Rate |
|---|---|---|---|---|
| rising | Q1 | 2,675 | +0.0717% | 55.1% |
| rising | Q5 | 1,638 | -0.0398% | 46.6% |
| flat/falling | Q1 | 893 | +0.1035% | 56.2% |
| flat/falling | Q5 | 1,517 | -0.0223% | 47.3% |

**1h**

| ATR 24h trend | LPL | n | Median | Win Rate |
|---|---|---|---|---|
| rising | Q1 | 2,675 | +0.0785% | 53.6% |
| rising | Q5 | 1,638 | -0.0017% | 49.9% |
| flat/falling | Q1 | 893 | +0.1255% | 54.9% |
| flat/falling | Q5 | 1,517 | -0.0589% | 46.7% |

**4h**

| ATR 24h trend | LPL | n | Median | Win Rate |
|---|---|---|---|---|
| rising | Q1 | 2,675 | +0.2436% | 57.4% |
| rising | Q5 | 1,638 | -0.0321% | 48.8% |
| flat/falling | Q1 | 893 | +0.1331% | 54.3% |
| flat/falling | Q5 | 1,517 | -0.1698% | 44.3% |

**4h LPL spread (Q5-Q1) by ATR trend:**

| ATR 24h trend | Spread | n(Q1) | n(Q5) |
|---|---|---|---|
| rising | -0.2757% | 2,675 | 1,638 |
| flat/falling | -0.3029% | 893 | 1,517 |

**Verdict:** ATR trend does not change the spread much — it looks like the LEVEL of volatility that matters, not whether it is currently rising.


---

## 3. Full outcome distribution — extreme cells (4h)

Is the median shift broad across many samples, or driven by a handful of extreme BTC moves? Full distribution, not just the median.

| Cell | n | Mean | Median | Win Rate | Std | P05 | P25 | P75 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| LPL=Q1 (lowest) + Volatility=Q5 (highest) | 3,568 | +0.0715% | +0.2221% | 56.6% | 2.482% | -3.84% | -0.93% | +1.21% | +3.43% |
| LPL=Q5 (highest) + Volatility=Q5 (highest) | 3,155 | +0.0194% | -0.0988% | 46.7% | 1.886% | -2.88% | -0.95% | +0.90% | +3.21% |

If mean and median are close and P25/P75 straddle the median symmetrically-ish, the shift is broad. A mean far from the median (as v1 found for one bb_position bin) would flag outlier-driven contamination instead.


---

## 4. Multi-horizon comparison — extreme cells

Does the effect already show at 15m and persist through 4h (a real, early-forming state effect), or does it only appear at longer horizons (could be something that only resolves slowly, or noise that coincidentally lines up at 4h)?

| Cell | Horizon | n | Median | Win Rate |
|---|---|---|---|---|
| LPL=Q1 + Vol=Q5 | 15m | 3,568 | +0.0410% | 53.3% |
| LPL=Q1 + Vol=Q5 | 30m | 3,568 | +0.0827% | 55.4% |
| LPL=Q1 + Vol=Q5 | 1h | 3,568 | +0.0899% | 53.9% |
| LPL=Q1 + Vol=Q5 | 4h | 3,568 | +0.2221% | 56.6% |
| LPL=Q5 + Vol=Q5 | 15m | 3,155 | -0.0239% | 47.5% |
| LPL=Q5 + Vol=Q5 | 30m | 3,155 | -0.0329% | 46.9% |
| LPL=Q5 + Vol=Q5 | 1h | 3,155 | -0.0272% | 48.4% |
| LPL=Q5 + Vol=Q5 | 4h | 3,155 | -0.0988% | 46.7% |


---

## 5. Time stability — extreme cells (4h)

### LPL=Q1 + Vol=Q5

| Year | n | Median | Win Rate |
|---|---|---|---|
| 2020 | 565 | +0.2994% | 58.1% |
| 2021 | 1,456 | +0.2601% | 56.8% |
| 2022 | 729 | +0.0702% | 52.8% |
| 2023 | 82 | +0.1103% | 53.7% |
| 2024 | 374 | +0.3243% | 61.2% |
| 2025 | 242 | +0.2878% | 57.0% |
| 2026 | 120 | +0.3100% | 58.3% |

Sign consistency: 7/7 years

### LPL=Q5 + Vol=Q5

| Year | n | Median | Win Rate |
|---|---|---|---|
| 2020 | 531 | -0.1027% | 47.5% |
| 2021 | 1,413 | -0.0216% | 49.2% |
| 2022 | 506 | -0.1649% | 43.5% |
| 2023 | 173 | -0.0426% | 48.6% |
| 2024 | 295 | -0.2625% | 42.7% |
| 2025 | 158 | -0.2496% | 38.0% |
| 2026 | 79 | -0.1105% | 44.3% |

Sign consistency: 7/7 years

