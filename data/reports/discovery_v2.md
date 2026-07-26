# Discovery Analysis Report v2 — redundancy and independent information

Generated 2026-07-26T13:38:34.158756+00:00 from data/historical_candidates.json.

Follow-up to v1's headline finding: bb_position, range_position_20, range_position_50, and vwap_distance all showed a strong, time-stable relationship to forward returns. Open question: are these four independent information sources, or do they mostly measure the same latent "local price location" variable?

---

## 1. Correlation matrix

Pairwise correlation among the state dimensions themselves (not vs. forward return) — do they move together (redundant) or independently?

n = 57,389

**Pearson (linear):**

| | bb_position | range_position_20 | range_position_50 | vwap_distance | trend_ema_cross_norm | momentum_rsi |
|---|---|---|---|---|---|---|
| **bb_position** | +1.000 | +0.909 | +0.704 | +0.738 | +0.564 | +0.863 |
| **range_position_20** | +0.909 | +1.000 | +0.736 | +0.755 | +0.598 | +0.841 |
| **range_position_50** | +0.704 | +0.736 | +1.000 | +0.677 | +0.707 | +0.873 |
| **vwap_distance** | +0.738 | +0.755 | +0.677 | +1.000 | +0.871 | +0.825 |
| **trend_ema_cross_norm** | +0.564 | +0.598 | +0.707 | +0.871 | +1.000 | +0.790 |
| **momentum_rsi** | +0.863 | +0.841 | +0.873 | +0.825 | +0.790 | +1.000 |


**Spearman (monotonic — more appropriate given v1's linear/monotonic-but-not-necessarily-straight-line shapes):**

| | bb_position | range_position_20 | range_position_50 | vwap_distance | trend_ema_cross_norm | momentum_rsi |
|---|---|---|---|---|---|---|
| **bb_position** | +1.000 | +0.926 | +0.714 | +0.902 | +0.710 | +0.895 |
| **range_position_20** | +0.926 | +1.000 | +0.737 | +0.910 | +0.716 | +0.868 |
| **range_position_50** | +0.714 | +0.737 | +1.000 | +0.784 | +0.863 | +0.899 |
| **vwap_distance** | +0.902 | +0.910 | +0.784 | +1.000 | +0.853 | +0.922 |
| **trend_ema_cross_norm** | +0.710 | +0.716 | +0.863 | +0.853 | +1.000 | +0.892 |
| **momentum_rsi** | +0.895 | +0.868 | +0.899 | +0.922 | +0.892 | +1.000 |


---

## 2. Latent factor (PCA)

Principal-component decomposition of the four core dimensions (standardized). If PC1 alone explains most of the variance, that's direct evidence they're mostly one latent "local price location" factor, not four independent signals.

n = 57,389

| Component | Explained variance | Cumulative |
|---|---|---|
| PC1 | 81.6% | 81.6% |
| PC2 | 8.5% | 90.2% |
| PC3 | 7.6% | 97.8% |
| PC4 | 2.2% | 100.0% |

**PC1 loadings** (how much each dimension contributes, sign-normalized so bb_position loads positive):

| Dimension | PC1 loading |
|---|---|
| bb_position | +0.516 |
| range_position_20 | +0.523 |
| range_position_50 | +0.475 |
| vwap_distance | +0.485 |

**Verdict:** PC1 explains a large majority of the variance — strong evidence for a single shared latent factor.


---

## 3. Redundancy: incremental R²

Raw-sample-level OLS R² (NOT decile-aggregated like v1's shape classification, which inflates apparent correlation by averaging out noise — these numbers will look small; that's normal for single-sample return prediction and expected. What matters here is the RELATIVE, incremental change as dimensions are added, not the absolute size).

### Horizon: 1h

**Standalone (each dimension alone, for reference):**

| Dimension | n | R² |
|---|---|---|
| bb_position | 57,507 | 0.00009 |
| range_position_20 | 57,564 | 0.00001 |
| range_position_50 | 57,564 | 0.00000 |
| vwap_distance | 57,388 | 0.00008 |

**Incremental chain (each row adds one dimension to the row above):**

| Combination | n | R² | Δ from adding this dimension |
|---|---|---|---|
| bb_position alone | 57,507 | 0.00009 | — |
| + range_position_20 | 57,507 | 0.00015 | +0.00006 |
| + vwap_distance | 57,388 | 0.00126 | +0.00111 |
| + range_position_50 (= all four) | 57,388 | 0.00127 | +0.00001 |

### Horizon: 4h

**Standalone (each dimension alone, for reference):**

| Dimension | n | R² |
|---|---|---|
| bb_position | 57,504 | 0.00007 |
| range_position_20 | 57,561 | 0.00001 |
| range_position_50 | 57,561 | 0.00000 |
| vwap_distance | 57,385 | 0.00030 |

**Incremental chain (each row adds one dimension to the row above):**

| Combination | n | R² | Δ from adding this dimension |
|---|---|---|---|
| bb_position alone | 57,504 | 0.00007 | — |
| + range_position_20 | 57,504 | 0.00010 | +0.00003 |
| + vwap_distance | 57,385 | 0.00160 | +0.00150 |
| + range_position_50 (= all four) | 57,385 | 0.00166 | +0.00006 |


---

## 4. Residual analysis — independent information content

For each core dimension, the residual after regressing it on the OTHER three ("the part of X not explained by the others"), run through the same median-binned decile / shape / year-stability check v1 used on the raw dimensions. A residual that still shows a real, time-stable effect means that dimension carries information the other three don't; a flat/unstable residual means it's redundant with them.

### bb_position | residual after controlling for range_position_20, range_position_50, vwap_distance

- Raw dimension 4h median spread: +0.1836%
- **Residual** 4h median spread: +0.0265% (14% of raw, if raw != 0)
- Residual shape: irregular (r=-0.22, no clean pattern)
- Residual time stability: 7/7 years same sign

**bb_position residual — 4h**

| Bin | n | Mean | Median | Win Rate | Std | P25 | P75 | P05 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| [-0.8912, -0.162) | 5,739 | +0.0055% | +0.0183% | 50.9% | 1.385% | -0.56% | +0.52% | -2.04% | +2.07% |
| [-0.162, -0.1046) | 5,739 | +0.0070% | +0.0157% | 50.8% | 1.278% | -0.50% | +0.53% | -2.00% | +1.97% |
| [-0.1046, -0.06596) | 5,737 | +0.0097% | +0.0167% | 51.0% | 1.255% | -0.50% | +0.49% | -1.92% | +1.89% |
| [-0.06596, -0.03331) | 5,737 | +0.0180% | +0.0246% | 51.6% | 1.306% | -0.43% | +0.51% | -1.83% | +1.91% |
| [-0.03331, -0.003071) | 5,739 | +0.0062% | +0.0051% | 50.2% | 1.235% | -0.44% | +0.49% | -1.86% | +1.83% |
| [-0.003071, 0.02834) | 5,738 | +0.0689% | +0.0265% | 52.0% | 1.348% | -0.43% | +0.54% | -1.86% | +2.10% |
| [0.02834, 0.06276) | 5,739 | +0.0377% | +0.0300% | 52.0% | 1.226% | -0.42% | +0.49% | -1.77% | +1.83% |
| [0.06276, 0.1043) | 5,739 | +0.0468% | +0.0203% | 51.6% | 1.247% | -0.42% | +0.52% | -1.76% | +1.93% |
| [0.1043, 0.1671) | 5,739 | +0.0212% | +0.0035% | 50.3% | 1.190% | -0.42% | +0.45% | -1.81% | +1.85% |
| [0.1671, 1.055) | 5,739 | +0.0437% | +0.0096% | 50.5% | 1.476% | -0.43% | +0.49% | -1.86% | +2.02% |

### range_position_20 | residual after controlling for bb_position, range_position_50, vwap_distance

- Raw dimension 4h median spread: +0.2220%
- **Residual** 4h median spread: +0.0694% (31% of raw, if raw != 0)
- Residual shape: linear/monotonic (decreasing, r=-0.90)
- Residual time stability: 7/7 years same sign

**range_position_20 residual — 4h**

| Bin | n | Mean | Median | Win Rate | Std | P25 | P75 | P05 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| [-0.6221, -0.1296) | 5,739 | +0.0081% | +0.0391% | 52.6% | 1.148% | -0.42% | +0.46% | -1.76% | +1.66% |
| [-0.1296, -0.08655) | 5,739 | +0.0252% | +0.0510% | 53.3% | 1.159% | -0.41% | +0.49% | -1.83% | +1.70% |
| [-0.08655, -0.05367) | 5,739 | +0.0335% | +0.0359% | 52.2% | 1.204% | -0.41% | +0.51% | -1.84% | +1.82% |
| [-0.05367, -0.026) | 5,739 | +0.0258% | +0.0223% | 51.5% | 1.305% | -0.47% | +0.52% | -1.93% | +1.96% |
| [-0.026, 4.395e-05) | 5,739 | +0.0105% | +0.0123% | 50.7% | 1.274% | -0.44% | +0.50% | -1.95% | +1.90% |
| [4.395e-05, 0.02645) | 5,738 | +0.0356% | +0.0070% | 50.4% | 1.282% | -0.45% | +0.52% | -1.89% | +2.06% |
| [0.02645, 0.055) | 5,739 | +0.0439% | +0.0178% | 50.9% | 1.295% | -0.45% | +0.50% | -1.76% | +2.04% |
| [0.055, 0.0863) | 5,739 | +0.0175% | -0.0023% | 49.8% | 1.325% | -0.47% | +0.52% | -1.90% | +2.00% |
| [0.0863, 0.128) | 5,739 | +0.0484% | +0.0097% | 50.7% | 1.349% | -0.46% | +0.52% | -1.87% | +2.12% |
| [0.128, 0.9612) | 5,735 | +0.0162% | -0.0184% | 48.7% | 1.582% | -0.54% | +0.50% | -2.03% | +2.19% |

### range_position_50 | residual after controlling for bb_position, range_position_20, vwap_distance

- Raw dimension 4h median spread: +0.2136%
- **Residual** 4h median spread: +0.1024% (48% of raw, if raw != 0)
- Residual shape: irregular (r=-0.43, no clean pattern)
- Residual time stability: 7/7 years same sign

**range_position_50 residual — 4h**

| Bin | n | Mean | Median | Win Rate | Std | P25 | P75 | P05 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| [-0.6037, -0.2214) | 5,737 | -0.0045% | -0.0021% | 49.8% | 1.259% | -0.44% | +0.45% | -2.03% | +1.87% |
| [-0.2214, -0.1562) | 5,738 | +0.0305% | +0.0638% | 54.7% | 1.210% | -0.38% | +0.54% | -1.87% | +1.82% |
| [-0.1562, -0.1074) | 5,738 | +0.0360% | +0.0523% | 53.5% | 1.247% | -0.42% | +0.53% | -1.93% | +1.96% |
| [-0.1074, -0.05413) | 5,739 | +0.0243% | +0.0269% | 51.8% | 1.333% | -0.48% | +0.54% | -2.06% | +2.02% |
| [-0.05413, 0.006467) | 5,739 | +0.0447% | +0.0381% | 52.3% | 1.376% | -0.44% | +0.55% | -1.94% | +2.04% |
| [0.006467, 0.06249) | 5,738 | +0.0263% | +0.0190% | 51.0% | 1.355% | -0.49% | +0.53% | -1.91% | +2.05% |
| [0.06249, 0.1071) | 5,739 | +0.0512% | -0.0228% | 48.6% | 1.309% | -0.46% | +0.49% | -1.71% | +2.09% |
| [0.1071, 0.1512) | 5,739 | +0.0353% | -0.0116% | 49.2% | 1.192% | -0.46% | +0.49% | -1.69% | +1.86% |
| [0.1512, 0.2176) | 5,739 | +0.0029% | -0.0386% | 47.2% | 1.215% | -0.49% | +0.43% | -1.73% | +1.91% |
| [0.2176, 1.939) | 5,739 | +0.0180% | +0.0431% | 52.7% | 1.452% | -0.44% | +0.48% | -1.84% | +1.79% |

### vwap_distance | residual after controlling for bb_position, range_position_20, range_position_50

- Raw dimension 4h median spread: +0.2298%
- **Residual** 4h median spread: +0.0501% (22% of raw, if raw != 0)
- Residual shape: linear/monotonic (increasing, r=+0.77)
- Residual time stability: 7/7 years same sign

**vwap_distance residual — 4h**

| Bin | n | Mean | Median | Win Rate | Std | P25 | P75 | P05 | P95 |
|---|---|---|---|---|---|---|---|---|---|
| [-0.4811, -0.008464) | 5,739 | +0.0755% | +0.0092% | 50.4% | 1.921% | -0.48% | +0.69% | -2.48% | +2.79% |
| [-0.008464, -0.005153) | 5,736 | +0.0508% | -0.0040% | 49.6% | 1.205% | -0.42% | +0.49% | -1.70% | +1.95% |
| [-0.005153, -0.003106) | 5,738 | +0.0313% | -0.0027% | 49.6% | 1.172% | -0.44% | +0.47% | -1.68% | +1.89% |
| [-0.003106, -0.001459) | 5,739 | +0.0341% | +0.0170% | 51.2% | 1.192% | -0.43% | +0.49% | -1.76% | +1.87% |
| [-0.001459, 0.0001036) | 5,739 | +0.0216% | +0.0013% | 50.0% | 1.182% | -0.44% | +0.49% | -1.74% | +1.86% |
| [0.0001036, 0.001689) | 5,738 | +0.0379% | +0.0242% | 51.7% | 1.183% | -0.42% | +0.49% | -1.75% | +1.81% |
| [0.001689, 0.00334) | 5,739 | -0.0320% | +0.0122% | 50.7% | 1.174% | -0.49% | +0.47% | -1.89% | +1.75% |
| [0.00334, 0.005423) | 5,739 | +0.0175% | +0.0404% | 52.6% | 1.166% | -0.42% | +0.48% | -1.82% | +1.71% |
| [0.005423, 0.00881) | 5,739 | +0.0098% | +0.0461% | 53.3% | 1.092% | -0.41% | +0.47% | -1.76% | +1.58% |
| [0.00881, 0.08786) | 5,739 | +0.0182% | +0.0256% | 51.5% | 1.470% | -0.57% | +0.55% | -2.22% | +2.38% |

