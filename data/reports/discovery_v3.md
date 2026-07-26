# Discovery Analysis Report v3 — bb_position x vwap_distance as a 2D state map

Generated 2026-07-26T13:46:55.308153+00:00 from data/historical_candidates.json.

Follow-up to v2: bb_position and vwap_distance together capture most of the "local price location" latent factor's information. This tests whether they combine additively or interact.

---

## 1. 2D grid: bb_position x vwap_distance

Tertiles (low/mid/high, ~1/3 of samples each) on both axes, full distribution per cell, every horizon.

**15m**

| bb_position | vwap_distance | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 16,383 | +0.0067% | +0.0220% | 53.5% | 0.442% |
| low | mid | 2,820 | +0.0052% | +0.0054% | 51.8% | 0.211% |
| low | high | 16 | -0.0487% | -0.1149% | 43.8% | 0.385% |
| mid | low | 2,886 | +0.0095% | +0.0000% | 49.7% | 0.379% |
| mid | mid | 12,717 | +0.0053% | -0.0004% | 49.6% | 0.287% |
| mid | high | 3,441 | +0.0084% | +0.0131% | 52.1% | 0.364% |
| high | low | 11 | -0.1456% | +0.0687% | 63.6% | 0.477% |
| high | mid | 3,606 | +0.0072% | -0.0037% | 48.4% | 0.181% |
| high | high | 15,509 | +0.0029% | -0.0167% | 47.1% | 0.372% |

**30m**

| bb_position | vwap_distance | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 16,383 | +0.0085% | +0.0400% | 55.0% | 0.588% |
| low | mid | 2,820 | +0.0025% | +0.0082% | 52.1% | 0.291% |
| low | high | 16 | -0.1102% | -0.1144% | 43.8% | 0.487% |
| mid | low | 2,886 | +0.0127% | +0.0041% | 50.3% | 0.523% |
| mid | mid | 12,717 | +0.0053% | +0.0025% | 50.3% | 0.368% |
| mid | high | 3,441 | +0.0156% | +0.0211% | 52.7% | 0.490% |
| high | low | 11 | -0.2367% | -0.0998% | 36.4% | 0.462% |
| high | mid | 3,605 | +0.0128% | -0.0069% | 47.7% | 0.258% |
| high | high | 15,509 | +0.0054% | -0.0222% | 46.7% | 0.501% |

**1h**

| bb_position | vwap_distance | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 16,383 | +0.0005% | +0.0444% | 53.9% | 0.810% |
| low | mid | 2,820 | +0.0016% | +0.0148% | 52.7% | 0.395% |
| low | high | 16 | -0.2848% | -0.1741% | 31.2% | 0.843% |
| mid | low | 2,886 | +0.0366% | +0.0195% | 51.8% | 0.715% |
| mid | mid | 12,717 | +0.0048% | +0.0045% | 50.5% | 0.515% |
| mid | high | 3,441 | -0.0033% | +0.0054% | 50.6% | 0.684% |
| high | low | 11 | -0.2341% | -0.1706% | 18.2% | 0.387% |
| high | mid | 3,605 | +0.0274% | -0.0057% | 48.3% | 0.388% |
| high | high | 15,509 | +0.0195% | -0.0267% | 47.3% | 0.696% |

**4h**

| bb_position | vwap_distance | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 16,383 | +0.0108% | +0.0901% | 54.8% | 1.514% |
| low | mid | 2,820 | +0.0166% | +0.0506% | 54.9% | 0.874% |
| low | high | 16 | -0.9576% | -0.4143% | 43.8% | 1.871% |
| mid | low | 2,886 | +0.0907% | +0.0689% | 54.4% | 1.384% |
| mid | mid | 12,717 | +0.0236% | +0.0160% | 51.4% | 1.059% |
| mid | high | 3,441 | +0.0271% | +0.0158% | 50.6% | 1.437% |
| high | low | 11 | -0.0754% | -0.0042% | 45.5% | 0.713% |
| high | mid | 3,602 | +0.0355% | -0.0256% | 47.4% | 0.858% |
| high | high | 15,509 | +0.0340% | -0.0578% | 46.5% | 1.326% |


---

## 2. Additive vs. interaction (4h, median)

predicted_cell = grand_median + row_effect + col_effect (what you'd expect if bb_position and vwap_distance acted purely independently/additively). residual = actual - predicted: far from zero means the specific COMBINATION carries information beyond each dimension's separate marginal effect.

**Caveat:** cells with n < 100 are excluded from this decomposition and marked n/a below — bb_position and vwap_distance are correlated enough (Spearman 0.90) that the two "disagreeing" corners (bb low + vwap high, bb high + vwap low) have only ~11-16 samples in this dataset and would otherwise dominate the residuals with noise, not signal.

Grand median (reliable cells only): +0.0226%

**Row effects (bb_position, averaged over vwap):**

| bb_position | effect |
|---|---|
| low | +0.0478% |
| mid | +0.0110% |
| high | -0.0643% |

**Column effects (vwap_distance, averaged over bb):**

| vwap_distance | effect |
|---|---|
| low | +0.0569% |
| mid | -0.0089% |
| high | -0.0436% |

**Cell sample sizes** (n < 100 excluded above):

| bb \ vwap | low | mid | high |
|---|---|---|---|
| **low** | 16383 | 2820 | 16 |
| **mid** | 2886 | 12717 | 3441 |
| **high** | 11 | 3602 | 15509 |


**Actual median return per cell:**

| bb \ vwap | low | mid | high |
|---|---|---|---|
| **low** | +0.0901% | +0.0506% | n/a (n=16, too few) |
| **mid** | +0.0689% | +0.0160% | +0.0158% |
| **high** | n/a (n=11, too few) | -0.0256% | -0.0578% |


**Predicted (additive model):**

| bb \ vwap | low | mid | high |
|---|---|---|---|
| **low** | +0.1273% | +0.0614% | +0.0268% |
| **mid** | +0.0905% | +0.0247% | -0.0100% |
| **high** | +0.0152% | -0.0506% | -0.0853% |


**Residual (actual − predicted — the interaction signal):**

| bb \ vwap | low | mid | high |
|---|---|---|---|
| **low** | -0.0372% | -0.0108% | n/a (n=16, too few) |
| **mid** | -0.0216% | -0.0087% | +0.0258% |
| **high** | n/a (n=11, too few) | +0.0250% | +0.0275% |


**Verdict:** Among the 7 reliable (n>=100) cells, largest residual: -0.0372% at bb=low/vwap=low. Row (bb) spread: 0.1120%, column (vwap) spread: 0.1005%. Residuals are large relative to the main effects — there IS a genuine interaction, not just additive. (Note: the two low-n corner cells — bb=low/vwap=high, bb=high/vwap=low — are excluded from this verdict entirely; they cannot be assessed reliably with only ~11-16 samples.)


---

## 3. Time stability of the key cells (4h)

Corners (both dimensions agree) and mixed cells (dimensions disagree) — if bb and vwap ever point in different directions, the mixed cells are where that would show up.

### both low (bb=low, vwap=low)

Sign consistency: 7/7 years

| Year | n | Median | Win Rate |
|---|---|---|---|
| 2020 | 2,156 | +0.1565% | 58.3% |
| 2021 | 2,829 | +0.1816% | 55.8% |
| 2022 | 2,920 | +0.0558% | 52.7% |
| 2023 | 2,096 | +0.0813% | 55.3% |
| 2024 | 2,436 | +0.0940% | 55.5% |
| 2025 | 2,417 | +0.0694% | 54.6% |
| 2026 | 1,529 | +0.0137% | 50.8% |

### both high (bb=high, vwap=high)

Sign consistency: 7/7 years

| Year | n | Median | Win Rate |
|---|---|---|---|
| 2020 | 2,647 | -0.0572% | 47.2% |
| 2021 | 2,881 | -0.0716% | 46.8% |
| 2022 | 2,133 | -0.0830% | 44.2% |
| 2023 | 1,901 | -0.0687% | 45.0% |
| 2024 | 2,482 | -0.0197% | 49.0% |
| 2025 | 2,247 | -0.0577% | 45.9% |
| 2026 | 1,218 | -0.0366% | 47.0% |

### bb high, vwap low (bb=high, vwap=low)

Skipped — this cell has too few total samples for any year to reach n>=20 (see Section 2's caveat: bb_position and vwap_distance are correlated enough that this "disagreeing" combination is rare).

### bb low, vwap high (bb=low, vwap=high)

Skipped — this cell has too few total samples for any year to reach n>=20 (see Section 2's caveat: bb_position and vwap_distance are correlated enough that this "disagreeing" combination is rare).

