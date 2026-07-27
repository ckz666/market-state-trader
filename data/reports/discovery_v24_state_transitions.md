# Discovery v24 — state transitions: does origin matter?

Generated 2026-07-27T06:00:38.834827+00:00.

`context` was tested by discovery_v1 as a static categorical dimension; its transitions never were. The question here is not "which transition predicts returns" (25 transitions x 3 horizons = 75 cells invites cherry-picking) but whether `previous_context x current_context` carries information beyond `current_context` alone — with a permutation test to say what counts as more than chance. Purely descriptive; proposes no rule. Discovery only (2020-2025); 2026 untouched. Cells below n=100 are marked instead of reported.

---

## A. Transition matrix

**Median 15m forward return — rows: previous state, columns: current state**

| from \ to | compressed | continuation | extended | mean_reversion | transition |
|---|---|---|---|---|---|
| compressed | +0.0005% (n=8,662) | n=85 | +0.0083% (n=818) | n=29 | -0.0184% (n=131) |
| continuation | -0.0051% (n=163) | +0.0032% (n=15,030) | +0.0401% (n=684) | +0.0030% (n=699) | -0.0115% (n=946) |
| extended | +0.0079% (n=608) | +0.0000% (n=922) | +0.0063% (n=3,339) | n=41 | +0.0049% (n=1,497) |
| mean_reversion | n=21 | -0.0315% (n=320) | +0.0784% (n=192) | -0.0043% (n=729) | -0.0092% (n=976) |
| transition | -0.0013% (n=271) | +0.0273% (n=1,165) | +0.0135% (n=1,374) | +0.0188% (n=740) | +0.0000% (n=13,165) |

**Median 1h forward return — rows: previous state, columns: current state**

| from \ to | compressed | continuation | extended | mean_reversion | transition |
|---|---|---|---|---|---|
| compressed | +0.0053% (n=8,662) | n=85 | -0.0024% (n=818) | n=29 | -0.0285% (n=131) |
| continuation | +0.0010% (n=163) | +0.0157% (n=15,030) | +0.0584% (n=684) | +0.0275% (n=699) | -0.0258% (n=946) |
| extended | +0.0000% (n=608) | -0.0046% (n=922) | +0.0058% (n=3,339) | n=41 | +0.0307% (n=1,497) |
| mean_reversion | n=21 | +0.0465% (n=320) | +0.0978% (n=192) | +0.0231% (n=729) | +0.0000% (n=976) |
| transition | -0.0027% (n=271) | +0.0031% (n=1,165) | +0.0216% (n=1,374) | +0.0264% (n=740) | +0.0051% (n=13,165) |

**Median 4h forward return — rows: previous state, columns: current state**

| from \ to | compressed | continuation | extended | mean_reversion | transition |
|---|---|---|---|---|---|
| compressed | +0.0152% (n=8,662) | n=85 | +0.0065% (n=818) | n=29 | +0.0277% (n=131) |
| continuation | +0.0275% (n=163) | +0.0324% (n=15,030) | +0.0834% (n=684) | +0.0620% (n=699) | -0.0881% (n=946) |
| extended | +0.0184% (n=608) | +0.0575% (n=922) | +0.0189% (n=3,339) | n=41 | +0.0000% (n=1,497) |
| mean_reversion | n=21 | +0.0253% (n=320) | +0.2789% (n=192) | +0.0371% (n=729) | +0.0398% (n=976) |
| transition | +0.0404% (n=271) | -0.0336% (n=1,165) | +0.0267% (n=1,374) | +0.0790% (n=740) | +0.0232% (n=13,165) |


---

## B. Model A vs. Model B — does origin add information?

For each current state: the median forward return of the state overall (Model A), and the range across the origins leading into it (Model B). A wide range means the same current state behaves differently depending on where it came from.


**Horizon 15m**

| Current state | n total | Model A median | Best origin | Worst origin | Range |
|---|---|---|---|---|---|
| compressed | 9,725 | +0.0015% | extended +0.0079% (n=608) | continuation -0.0051% (n=163) | **0.0130pp** |
| continuation | 17,522 | +0.0039% | transition +0.0273% (n=1,165) | mean_reversion -0.0315% (n=320) | **0.0588pp** |
| extended | 6,407 | +0.0132% | mean_reversion +0.0784% (n=192) | extended +0.0063% (n=3,339) | **0.0721pp** |
| mean_reversion | 2,238 | +0.0053% | transition +0.0188% (n=740) | mean_reversion -0.0043% (n=729) | **0.0232pp** |
| transition | 16,715 | +0.0000% | extended +0.0049% (n=1,497) | compressed -0.0184% (n=131) | **0.0233pp** |

**Horizon 1h**

| Current state | n total | Model A median | Best origin | Worst origin | Range |
|---|---|---|---|---|---|
| compressed | 9,725 | +0.0052% | compressed +0.0053% (n=8,662) | transition -0.0027% (n=271) | **0.0080pp** |
| continuation | 17,522 | +0.0134% | mean_reversion +0.0465% (n=320) | extended -0.0046% (n=922) | **0.0511pp** |
| extended | 6,407 | +0.0117% | mean_reversion +0.0978% (n=192) | compressed -0.0024% (n=818) | **0.1003pp** |
| mean_reversion | 2,238 | +0.0252% | continuation +0.0275% (n=699) | mean_reversion +0.0231% (n=729) | **0.0044pp** |
| transition | 16,715 | +0.0050% | extended +0.0307% (n=1,497) | compressed -0.0285% (n=131) | **0.0592pp** |

**Horizon 4h**

| Current state | n total | Model A median | Best origin | Worst origin | Range |
|---|---|---|---|---|---|
| compressed | 9,725 | +0.0164% | transition +0.0404% (n=271) | compressed +0.0152% (n=8,662) | **0.0253pp** |
| continuation | 17,522 | +0.0301% | extended +0.0575% (n=922) | transition -0.0336% (n=1,165) | **0.0911pp** |
| extended | 6,407 | +0.0248% | mean_reversion +0.2789% (n=192) | compressed +0.0065% (n=818) | **0.2724pp** |
| mean_reversion | 2,238 | +0.0620% | transition +0.0790% (n=740) | mean_reversion +0.0371% (n=729) | **0.0419pp** |
| transition | 16,715 | +0.0163% | mean_reversion +0.0398% (n=976) | continuation -0.0881% (n=946) | **0.1279pp** |

---

## C. Permutation test — is that spread more than chance?

`previous_context` is shuffled 200 times (destroying any real origin-outcome link while preserving both marginal distributions). The section-B spread statistic — mean across current states of (best origin median − worst origin median) — is recomputed each time. If the observed value sits inside the null distribution, the apparent structure in sections A/B is what 25 transitions produce by chance.

| Horizon | Observed spread | Null mean | Null 95th pct | Percentile of observed | Verdict |
|---|---|---|---|---|---|
| 15m | 0.0381pp | 0.0217pp | 0.0305pp | 100.0 | **exceeds chance (>95th pct)** |
| 1h | 0.0446pp | 0.0361pp | 0.0494pp | 88.5 | within chance |
| 4h | 0.1117pp | 0.0629pp | 0.0904pp | 100.0 | **exceeds chance (>95th pct)** |
