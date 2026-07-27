# Discovery v26 — key results re-run WITH funding costs

Generated 2026-07-27T06:15:28.867166+00:00.

Every simulation in v1-v25 ignored funding because the data did not exist. It now does (7,119 8-hourly intervals from 2020-01). A long pays the rate at each interval it holds through; a short receives it. **Source caveat:** rates are Binance, prices are Bitget — measured proxy error 0.284 bps per 8h interval (see funding_backfill.md). Discovery 2020-2025 plus the 2026 OOS figures for the 24h candidate, since funding changes those too.

---

## 1. The 24h candidate, with and without funding (Discovery)

| Config | n | Win rate | Median | Mean | PF | Equity |
|---|---|---|---|---|---|---|
| 240m — excl. funding (as published) | 1,064 | 51.4% | +0.0473% | -0.1306% | 0.853 | 0.1731 |
| **240m — incl. funding** | 1,064 | 51.4% | +0.0467% | -0.1371% | 0.846 | 0.1614 |
| ↳ mean funding per trade | | | | -0.0064% | | |
| 1440m — excl. funding (as published) | 365 | 56.4% | +0.5179% | +0.3718% | 1.255 | 2.2701 |
| **1440m — incl. funding** | 365 | 54.8% | +0.4983% | +0.3286% | 1.222 | 1.9399 |
| ↳ mean funding per trade | | | | -0.0432% | | |

---

## 2. The 24h candidate on 2026 OOS, with funding

| Config | n | Win rate | Median | Mean | PF | Equity |
|---|---|---|---|---|---|---|
| 240m — excl. funding (as published) | 39 | 51.3% | +0.1787% | -0.0893% | 0.868 | 0.9609 |
| **240m — incl. funding** | 39 | 51.3% | +0.1819% | -0.0895% | 0.867 | 0.9608 |
| 1440m — excl. funding (as published) | 16 | 56.2% | +1.3137% | +0.7982% | 1.575 | 1.1189 |
| **1440m — incl. funding** | 16 | 56.2% | +1.3176% | +0.8007% | 1.577 | 1.1193 |

---

## 3. The short side, which RECEIVES funding (Discovery)

discovery_v20 concluded the short side loses at every hold. Funding is overwhelmingly positive, so a short receives it — the one cost component that works in the short's favour.

| Config | n | Win rate | Median | Mean | PF | Equity |
|---|---|---|---|---|---|---|
| 240m short — excl. funding (as published) | 945 | 45.2% | -0.1056% | -0.1903% | 0.760 | 0.1372 |
| **240m short — incl. funding** | 945 | 45.5% | -0.0927% | -0.1779% | 0.773 | 0.1543 |
| ↳ mean funding received per trade | | | | +0.0124% | | |
| 1440m short — excl. funding (as published) | 315 | 47.6% | -0.0944% | -0.2221% | 0.869 | 0.3539 |
| **1440m short — incl. funding** | 315 | 48.9% | -0.0735% | -0.1597% | 0.904 | 0.4321 |
| ↳ mean funding received per trade | | | | +0.0623% | | |
