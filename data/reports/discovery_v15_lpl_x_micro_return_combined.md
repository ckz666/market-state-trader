# Discovery v15 — LPL x micro_return_5m inside Vol=Q5

Generated 2026-07-27T04:50:36.544242+00:00.

discovery_v14 showed both factors strengthen with volatility, and decision_rule_v1 already trades only Vol==Q5 -- so they operate in the same subpopulation and may be additive, redundant, or conflicting there. This tests that directly. Purely descriptive; does not change decision_rule_v1. Discovery only (2020-2025); 2026 untouched. Cells with n < 30 are marked instead of reported.

---

## A. Full interaction matrix (Vol=Q5)

**Median 15m return — rows: LPL quintile, columns: micro_return_5m quintile (Vol=Q5)**

| LPL \ ret5m | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| Q1 | +0.1294% (n=1313) | +0.0299% (n=369) | -0.0032% (n=241) | +0.0055% (n=327) | -0.0147% (n=1026) |
| Q2 | +0.0970% (n=512) | +0.0224% (n=192) | +0.0132% (n=152) | +0.0483% (n=205) | +0.0217% (n=428) |
| Q3 | +0.0561% (n=453) | -0.0264% (n=213) | -0.0297% (n=151) | +0.0200% (n=201) | -0.0387% (n=457) |
| Q4 | +0.0518% (n=373) | +0.0035% (n=201) | -0.0488% (n=144) | -0.0593% (n=217) | -0.0628% (n=455) |
| Q5 | +0.0403% (n=802) | -0.0271% (n=342) | -0.0172% (n=244) | -0.0263% (n=362) | -0.0785% (n=1132) |

**Median 1h return — rows: LPL quintile, columns: micro_return_5m quintile (Vol=Q5)**

| LPL \ ret5m | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| Q1 | +0.1654% (n=1313) | +0.0834% (n=369) | +0.0473% (n=241) | +0.0637% (n=327) | +0.0153% (n=1026) |
| Q2 | +0.1548% (n=512) | +0.1487% (n=192) | +0.0741% (n=152) | +0.0505% (n=205) | +0.0803% (n=428) |
| Q3 | +0.0955% (n=453) | -0.0371% (n=213) | -0.0174% (n=151) | -0.0458% (n=201) | -0.0184% (n=457) |
| Q4 | -0.0478% (n=373) | +0.0347% (n=201) | -0.0556% (n=144) | -0.0651% (n=217) | +0.0027% (n=455) |
| Q5 | +0.0551% (n=802) | -0.0447% (n=342) | -0.0218% (n=244) | -0.0620% (n=362) | -0.0664% (n=1132) |

**Median 4h return — rows: LPL quintile, columns: micro_return_5m quintile (Vol=Q5)**

| LPL \ ret5m | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| Q1 | +0.3118% (n=1313) | +0.2239% (n=369) | +0.2203% (n=241) | +0.1464% (n=327) | +0.1464% (n=1026) |
| Q2 | +0.2577% (n=512) | +0.3132% (n=192) | +0.1021% (n=152) | +0.2865% (n=205) | +0.2987% (n=428) |
| Q3 | +0.1786% (n=453) | -0.0691% (n=213) | +0.1869% (n=151) | +0.1470% (n=201) | +0.0196% (n=457) |
| Q4 | -0.0927% (n=373) | -0.0170% (n=201) | -0.0132% (n=144) | +0.0899% (n=217) | +0.0285% (n=455) |
| Q5 | -0.0417% (n=802) | -0.0898% (n=342) | -0.2773% (n=244) | -0.0352% (n=362) | -0.0922% (n=1132) |


---

## B/C. Inside `decision_rule_v1`'s actual entry cell (LPL==Q1 & Vol==Q5)

Does the micro_return_5m gradient survive within the exact population the live rule already selects? This is the decision-relevant question -- a factor can look strong marginally and still add nothing where it would actually be applied.


**Horizon 15m**

| micro_return_5m | n | Win rate | Median | Mean |
|---|---|---|---|---|
| Q1 | 1,313 | 58.3% | +0.1294% | +0.0901% |
| Q2 | 369 | 53.7% | +0.0299% | -0.0108% |
| Q3 | 241 | 49.8% | -0.0032% | -0.0240% |
| Q4 | 327 | 50.8% | +0.0055% | +0.0208% |
| Q5 | 1,026 | 49.3% | -0.0147% | -0.0523% |

Q1-Q5 spread within LPL==Q1: **+0.1441%**


**Horizon 1h**

| micro_return_5m | n | Win rate | Median | Mean |
|---|---|---|---|---|
| Q1 | 1,313 | 56.4% | +0.1654% | +0.0794% |
| Q2 | 369 | 54.2% | +0.0834% | +0.0004% |
| Q3 | 241 | 51.5% | +0.0473% | +0.0069% |
| Q4 | 327 | 54.1% | +0.0637% | +0.0975% |
| Q5 | 1,026 | 50.6% | +0.0153% | -0.0566% |

Q1-Q5 spread within LPL==Q1: **+0.1501%**


**Horizon 4h**

| micro_return_5m | n | Win rate | Median | Mean |
|---|---|---|---|---|
| Q1 | 1,313 | 58.2% | +0.3118% | +0.1106% |
| Q2 | 369 | 57.2% | +0.2239% | +0.0796% |
| Q3 | 241 | 59.8% | +0.2203% | +0.2703% |
| Q4 | 327 | 56.0% | +0.1464% | +0.0102% |
| Q5 | 1,026 | 54.5% | +0.1464% | +0.0159% |

Q1-Q5 spread within LPL==Q1: **+0.1654%**

