# Discovery Analysis Report v4 — Local Price Location x orthogonal state groups

Generated 2026-07-26T13:52:58.653880+00:00 from data/historical_candidates.json.

local_price_location = average of z-scored bb_position and z-scored vwap_distance (v2/v3 showed these two carry the shared "local price location" signal; plain average, not a fitted score). Three separate pairwise tests, not one combined 4-way grid (sparse data + multiple testing) — v4A vs. Volatility, v4B vs. Exhaustion, v4C vs. Structure, asking which of these changes what Local Price Location means the most.

---

## v4A. Local Price Location x Volatility (ATR norm)

Cell sample sizes (n=57,389 total, MIN_CELL_N=100):

| \ | low | mid | high |
|---|---|---|---|
| **low** | 5229 | 6386 | 7515 |
| **mid** | 8432 | 6019 | 4678 |
| **high** | 5424 | 6717 | 6989 |


### 2D grid (all horizons)

**15m**

| LPL | Volatility | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 5,229 | -0.0033% | +0.0133% | 53.9% | 0.201% |
| low | mid | 6,386 | +0.0046% | +0.0221% | 53.6% | 0.281% |
| low | high | 7,515 | +0.0160% | +0.0259% | 52.7% | 0.605% |
| mid | low | 8,432 | +0.0077% | -0.0029% | 48.9% | 0.206% |
| mid | mid | 6,019 | +0.0007% | -0.0010% | 49.4% | 0.253% |
| mid | high | 4,678 | +0.0089% | +0.0128% | 51.2% | 0.433% |
| high | low | 5,424 | +0.0073% | -0.0073% | 47.6% | 0.196% |
| high | mid | 6,717 | +0.0067% | -0.0117% | 48.0% | 0.293% |
| high | high | 6,989 | -0.0014% | -0.0206% | 47.5% | 0.484% |

**30m**

| LPL | Volatility | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 5,229 | -0.0031% | +0.0208% | 54.8% | 0.274% |
| low | mid | 6,386 | +0.0059% | +0.0364% | 54.9% | 0.384% |
| low | high | 7,515 | +0.0188% | +0.0521% | 54.5% | 0.803% |
| mid | low | 8,431 | +0.0099% | +0.0000% | 49.9% | 0.263% |
| mid | mid | 6,019 | -0.0026% | -0.0004% | 49.7% | 0.342% |
| mid | high | 4,678 | +0.0150% | +0.0282% | 52.3% | 0.565% |
| high | low | 5,424 | +0.0079% | -0.0164% | 45.9% | 0.300% |
| high | mid | 6,717 | +0.0100% | -0.0149% | 47.8% | 0.402% |
| high | high | 6,989 | +0.0025% | -0.0246% | 47.6% | 0.635% |

**1h**

| LPL | Volatility | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 5,229 | -0.0159% | +0.0196% | 53.0% | 0.390% |
| low | mid | 6,386 | -0.0058% | +0.0365% | 53.6% | 0.533% |
| low | high | 7,515 | +0.0201% | +0.0727% | 53.9% | 1.087% |
| mid | low | 8,431 | +0.0120% | +0.0025% | 50.3% | 0.353% |
| mid | mid | 6,019 | -0.0058% | +0.0059% | 50.5% | 0.512% |
| mid | high | 4,678 | +0.0227% | +0.0193% | 51.4% | 0.806% |
| high | low | 5,424 | +0.0168% | -0.0200% | 46.6% | 0.398% |
| high | mid | 6,717 | +0.0176% | -0.0217% | 47.5% | 0.584% |
| high | high | 6,989 | +0.0213% | -0.0220% | 48.6% | 0.881% |

**4h**

| LPL | Volatility | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 5,229 | -0.0386% | +0.0422% | 53.7% | 0.773% |
| low | mid | 6,386 | -0.0032% | +0.0743% | 54.1% | 1.047% |
| low | high | 7,515 | +0.0659% | +0.1676% | 56.3% | 2.025% |
| mid | low | 8,429 | +0.0221% | +0.0121% | 51.4% | 0.742% |
| mid | mid | 6,019 | +0.0012% | +0.0157% | 50.9% | 1.052% |
| mid | high | 4,678 | +0.0849% | +0.0710% | 52.7% | 1.587% |
| high | low | 5,423 | +0.0412% | -0.0404% | 46.0% | 0.805% |
| high | mid | 6,717 | +0.0391% | -0.0543% | 46.9% | 1.169% |
| high | high | 6,989 | +0.0243% | -0.0646% | 47.4% | 1.683% |


### Additive vs. interaction (4h, median)

Grand median (reliable cells only): +0.0249%

**LPL effects:**

| LPL | effect |
|---|---|
| low | +0.0699% |
| mid | +0.0081% |
| high | -0.0779% |

**Volatility effects:**

| Volatility | effect |
|---|---|
| low | -0.0202% |
| mid | -0.0129% |
| high | +0.0332% |

**Actual median:**

| \ | low | mid | high |
|---|---|---|---|
| **low** | +0.0422% | +0.0743% | +0.1676% |
| **mid** | +0.0121% | +0.0157% | +0.0710% |
| **high** | -0.0404% | -0.0543% | -0.0646% |


**Predicted (additive model):**

| \ | low | mid | high |
|---|---|---|---|
| **low** | +0.0745% | +0.0818% | +0.1279% |
| **mid** | +0.0127% | +0.0200% | +0.0661% |
| **high** | -0.0733% | -0.0660% | -0.0199% |


**Residual (interaction signal):**

| \ | low | mid | high |
|---|---|---|---|
| **low** | -0.0323% | -0.0074% | +0.0397% |
| **mid** | -0.0006% | -0.0043% | +0.0049% |
| **high** | +0.0329% | +0.0117% | -0.0447% |


**Verdict:** 9 reliable cells. Largest residual -0.0447% at LPL=high/Volatility=high. Row spread 0.1478%, col spread 0.0534%. Residual/spread ratio 30% — a real interaction, Volatility changes what LPL means.


### Time stability (4h) of reliable cells

- **LPL=low, Volatility=low**: 4/6 years same sign (aggregate median +0.0446%)
- **LPL=low, Volatility=mid**: 6/7 years same sign (aggregate median +0.0762%)
- **LPL=low, Volatility=high**: 7/7 years same sign (aggregate median +0.1895%)
- **LPL=mid, Volatility=low**: 5/6 years same sign (aggregate median +0.0051%)
- **LPL=mid, Volatility=mid**: 4/7 years same sign (aggregate median +0.0094%)
- **LPL=mid, Volatility=high**: 5/7 years same sign (aggregate median +0.0553%)
- **LPL=high, Volatility=low**: 5/6 years same sign (aggregate median -0.0398%)
- **LPL=high, Volatility=mid**: 7/7 years same sign (aggregate median -0.0651%)
- **LPL=high, Volatility=high**: 7/7 years same sign (aggregate median -0.0621%)


---

## v4B. Local Price Location x Exhaustion (cycle strength)

Cell sample sizes (n=57,389 total, MIN_CELL_N=100):

| \ | low | mid | high |
|---|---|---|---|
| **low** | 6221 | 6438 | 6471 |
| **mid** | 6533 | 6387 | 6209 |
| **high** | 6431 | 6316 | 6383 |


### 2D grid (all horizons)

**15m**

| LPL | Exhaustion | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 6,221 | +0.0084% | +0.0207% | 53.3% | 0.448% |
| low | mid | 6,438 | +0.0080% | +0.0207% | 53.4% | 0.407% |
| low | high | 6,471 | +0.0044% | +0.0181% | 53.3% | 0.423% |
| mid | low | 6,533 | +0.0002% | +0.0000% | 49.8% | 0.272% |
| mid | mid | 6,387 | +0.0127% | -0.0041% | 48.8% | 0.324% |
| mid | high | 6,209 | +0.0045% | +0.0016% | 50.3% | 0.275% |
| high | low | 6,431 | -0.0055% | -0.0203% | 46.2% | 0.375% |
| high | mid | 6,316 | +0.0047% | -0.0103% | 48.0% | 0.350% |
| high | high | 6,383 | +0.0126% | -0.0047% | 48.9% | 0.340% |

**30m**

| LPL | Exhaustion | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 6,221 | +0.0109% | +0.0352% | 54.8% | 0.591% |
| low | mid | 6,438 | +0.0112% | +0.0392% | 54.9% | 0.536% |
| low | high | 6,471 | +0.0035% | +0.0285% | 54.4% | 0.578% |
| mid | low | 6,532 | +0.0045% | +0.0051% | 50.9% | 0.365% |
| mid | mid | 6,387 | +0.0129% | +0.0000% | 49.7% | 0.414% |
| mid | high | 6,209 | +0.0042% | +0.0043% | 50.6% | 0.363% |
| high | low | 6,431 | -0.0058% | -0.0212% | 46.5% | 0.503% |
| high | mid | 6,316 | +0.0106% | -0.0163% | 47.4% | 0.465% |
| high | high | 6,383 | +0.0154% | -0.0146% | 47.6% | 0.469% |

**1h**

| LPL | Exhaustion | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 6,221 | -0.0013% | +0.0388% | 53.6% | 0.784% |
| low | mid | 6,438 | +0.0113% | +0.0467% | 54.5% | 0.764% |
| low | high | 6,471 | -0.0052% | +0.0254% | 52.6% | 0.777% |
| mid | low | 6,532 | +0.0102% | +0.0081% | 51.2% | 0.524% |
| mid | mid | 6,387 | +0.0092% | -0.0011% | 49.7% | 0.591% |
| mid | high | 6,209 | +0.0076% | +0.0081% | 51.1% | 0.515% |
| high | low | 6,431 | +0.0152% | -0.0226% | 47.2% | 0.706% |
| high | mid | 6,316 | +0.0154% | -0.0244% | 47.7% | 0.664% |
| high | high | 6,383 | +0.0256% | -0.0159% | 48.0% | 0.635% |

**4h**

| LPL | Exhaustion | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | low | 6,221 | -0.0117% | +0.0835% | 54.5% | 1.470% |
| low | mid | 6,438 | +0.0647% | +0.1149% | 56.4% | 1.453% |
| low | high | 6,471 | -0.0110% | +0.0597% | 53.6% | 1.467% |
| mid | low | 6,530 | +0.0434% | +0.0238% | 52.1% | 1.101% |
| mid | mid | 6,387 | +0.0210% | +0.0128% | 51.0% | 1.107% |
| mid | high | 6,209 | +0.0279% | +0.0204% | 51.6% | 1.088% |
| high | low | 6,430 | +0.0387% | -0.0632% | 46.3% | 1.341% |
| high | mid | 6,316 | +0.0019% | -0.0579% | 46.1% | 1.298% |
| high | high | 6,383 | +0.0619% | -0.0323% | 48.0% | 1.270% |


### Additive vs. interaction (4h, median)

Grand median (reliable cells only): +0.0180%

**LPL effects:**

| LPL | effect |
|---|---|
| low | +0.0681% |
| mid | +0.0010% |
| high | -0.0691% |

**Exhaustion effects:**

| Exhaustion | effect |
|---|---|
| low | -0.0033% |
| mid | +0.0053% |
| high | -0.0020% |

**Actual median:**

| \ | low | mid | high |
|---|---|---|---|
| **low** | +0.0835% | +0.1149% | +0.0597% |
| **mid** | +0.0238% | +0.0128% | +0.0204% |
| **high** | -0.0632% | -0.0579% | -0.0323% |


**Predicted (additive model):**

| \ | low | mid | high |
|---|---|---|---|
| **low** | +0.0828% | +0.0913% | +0.0840% |
| **mid** | +0.0157% | +0.0243% | +0.0170% |
| **high** | -0.0544% | -0.0458% | -0.0532% |


**Residual (interaction signal):**

| \ | low | mid | high |
|---|---|---|---|
| **low** | +0.0007% | +0.0236% | -0.0243% |
| **mid** | +0.0081% | -0.0115% | +0.0034% |
| **high** | -0.0088% | -0.0121% | +0.0209% |


**Verdict:** 9 reliable cells. Largest residual -0.0243% at LPL=low/Exhaustion=high. Row spread 0.1372%, col spread 0.0086%. Residual/spread ratio 18% — mostly ADDITIVE.


### Time stability (4h) of reliable cells

- **LPL=low, Exhaustion=low**: 7/7 years same sign (aggregate median +0.0817%)
- **LPL=low, Exhaustion=mid**: 7/7 years same sign (aggregate median +0.1066%)
- **LPL=low, Exhaustion=high**: 6/7 years same sign (aggregate median +0.0387%)
- **LPL=mid, Exhaustion=low**: 5/7 years same sign (aggregate median +0.0371%)
- **LPL=mid, Exhaustion=mid**: 5/7 years same sign (aggregate median +0.0224%)
- **LPL=mid, Exhaustion=high**: 6/7 years same sign (aggregate median +0.0263%)
- **LPL=high, Exhaustion=low**: 7/7 years same sign (aggregate median -0.0548%)
- **LPL=high, Exhaustion=mid**: 7/7 years same sign (aggregate median -0.0531%)
- **LPL=high, Exhaustion=high**: 2/7 years same sign (aggregate median -0.0384%)


---

## v4C. Local Price Location x Structure (4h trend)

Cell sample sizes (n=57,389 total, MIN_CELL_N=100):

| \ | contracting | downtrend | expanding | sideways | uptrend |
|---|---|---|---|---|---|
| **low** | 1993 | 2371 | 1503 | 9700 | 3563 |
| **mid** | 1794 | 2620 | 1858 | 9399 | 3458 |
| **high** | 1869 | 2969 | 1423 | 9838 | 3031 |


### 2D grid (all horizons)

**15m**

| LPL | Structure | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | contracting | 1,993 | +0.0023% | +0.0127% | 51.9% | 0.378% |
| low | downtrend | 2,371 | +0.0009% | +0.0182% | 52.4% | 0.477% |
| low | expanding | 1,503 | +0.0266% | +0.0288% | 56.4% | 0.354% |
| low | sideways | 9,700 | +0.0073% | +0.0169% | 52.9% | 0.450% |
| low | uptrend | 3,563 | +0.0040% | +0.0247% | 54.6% | 0.373% |
| mid | contracting | 1,794 | +0.0071% | -0.0029% | 48.7% | 0.241% |
| mid | downtrend | 2,620 | +0.0072% | +0.0017% | 50.3% | 0.303% |
| mid | expanding | 1,858 | +0.0024% | -0.0031% | 48.8% | 0.239% |
| mid | sideways | 9,399 | +0.0087% | +0.0000% | 49.8% | 0.314% |
| mid | uptrend | 3,458 | -0.0021% | +0.0000% | 49.6% | 0.267% |
| high | contracting | 1,869 | -0.0047% | -0.0204% | 45.6% | 0.390% |
| high | downtrend | 2,969 | +0.0087% | -0.0129% | 47.7% | 0.353% |
| high | expanding | 1,423 | +0.0007% | -0.0146% | 47.3% | 0.357% |
| high | sideways | 9,838 | +0.0034% | -0.0106% | 48.0% | 0.359% |
| high | uptrend | 3,031 | +0.0078% | -0.0069% | 48.3% | 0.324% |

**30m**

| LPL | Structure | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | contracting | 1,993 | +0.0055% | +0.0190% | 52.7% | 0.481% |
| low | downtrend | 2,371 | +0.0018% | +0.0336% | 54.2% | 0.585% |
| low | expanding | 1,503 | +0.0165% | +0.0341% | 55.6% | 0.500% |
| low | sideways | 9,700 | +0.0103% | +0.0384% | 55.2% | 0.620% |
| low | uptrend | 3,563 | +0.0064% | +0.0314% | 54.5% | 0.478% |
| mid | contracting | 1,794 | +0.0061% | -0.0001% | 49.3% | 0.319% |
| mid | downtrend | 2,620 | +0.0071% | +0.0052% | 50.8% | 0.385% |
| mid | expanding | 1,858 | +0.0039% | -0.0030% | 49.4% | 0.306% |
| mid | sideways | 9,398 | +0.0114% | +0.0058% | 51.0% | 0.412% |
| mid | uptrend | 3,458 | -0.0019% | +0.0000% | 49.7% | 0.357% |
| high | contracting | 1,869 | +0.0008% | -0.0269% | 45.5% | 0.566% |
| high | downtrend | 2,969 | +0.0183% | -0.0099% | 48.2% | 0.485% |
| high | expanding | 1,423 | +0.0039% | -0.0198% | 46.0% | 0.450% |
| high | sideways | 9,838 | +0.0036% | -0.0193% | 47.1% | 0.474% |
| high | uptrend | 3,031 | +0.0102% | -0.0121% | 47.9% | 0.444% |

**1h**

| LPL | Structure | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | contracting | 1,993 | -0.0088% | +0.0268% | 53.1% | 0.657% |
| low | downtrend | 2,371 | +0.0177% | +0.0433% | 54.3% | 0.814% |
| low | expanding | 1,503 | +0.0003% | +0.0380% | 54.8% | 0.668% |
| low | sideways | 9,700 | +0.0032% | +0.0381% | 53.6% | 0.840% |
| low | uptrend | 3,563 | -0.0069% | +0.0350% | 52.8% | 0.659% |
| mid | contracting | 1,794 | +0.0144% | -0.0044% | 49.2% | 0.471% |
| mid | downtrend | 2,620 | +0.0263% | +0.0167% | 52.6% | 0.641% |
| mid | expanding | 1,858 | +0.0218% | +0.0094% | 51.2% | 0.446% |
| mid | sideways | 9,398 | +0.0090% | +0.0076% | 50.9% | 0.556% |
| mid | uptrend | 3,458 | -0.0136% | -0.0053% | 49.0% | 0.516% |
| high | contracting | 1,869 | +0.0215% | -0.0206% | 47.7% | 0.684% |
| high | downtrend | 2,969 | +0.0337% | -0.0141% | 48.5% | 0.663% |
| high | expanding | 1,423 | -0.0086% | -0.0334% | 44.8% | 0.599% |
| high | sideways | 9,838 | +0.0191% | -0.0213% | 47.8% | 0.689% |
| high | uptrend | 3,031 | +0.0139% | -0.0195% | 47.6% | 0.633% |

**4h**

| LPL | Structure | n | Mean | Median | Win Rate | Std |
|---|---|---|---|---|---|---|
| low | contracting | 1,993 | +0.0453% | +0.0858% | 55.4% | 1.254% |
| low | downtrend | 2,371 | +0.0720% | +0.1100% | 55.5% | 1.593% |
| low | expanding | 1,503 | -0.0014% | +0.0814% | 54.8% | 1.327% |
| low | sideways | 9,700 | +0.0130% | +0.0937% | 55.4% | 1.576% |
| low | uptrend | 3,563 | -0.0315% | +0.0383% | 52.6% | 1.193% |
| mid | contracting | 1,794 | -0.0098% | -0.0238% | 47.7% | 0.986% |
| mid | downtrend | 2,620 | +0.0759% | +0.0546% | 54.2% | 1.200% |
| mid | expanding | 1,858 | +0.0443% | +0.0225% | 52.5% | 0.875% |
| mid | sideways | 9,396 | +0.0352% | +0.0266% | 52.1% | 1.141% |
| mid | uptrend | 3,458 | -0.0011% | -0.0022% | 49.6% | 1.064% |
| high | contracting | 1,869 | +0.0474% | -0.0562% | 46.7% | 1.295% |
| high | downtrend | 2,969 | +0.0927% | -0.0110% | 49.0% | 1.383% |
| high | expanding | 1,423 | -0.0090% | -0.0896% | 43.6% | 1.137% |
| high | sideways | 9,837 | +0.0337% | -0.0495% | 47.0% | 1.323% |
| high | uptrend | 3,031 | -0.0090% | -0.0665% | 45.5% | 1.234% |


### Additive vs. interaction (4h, median)

Grand median (reliable cells only): +0.0143%

**LPL effects:**

| LPL | effect |
|---|---|
| low | +0.0676% |
| mid | +0.0013% |
| high | -0.0688% |

**Structure effects:**

| Structure | effect |
|---|---|
| contracting | -0.0123% |
| downtrend | +0.0369% |
| expanding | -0.0095% |
| sideways | +0.0093% |
| uptrend | -0.0244% |

**Actual median:**

| \ | contracting | downtrend | expanding | sideways | uptrend |
|---|---|---|---|---|---|
| **low** | +0.0858% | +0.1100% | +0.0814% | +0.0937% | +0.0383% |
| **mid** | -0.0238% | +0.0546% | +0.0225% | +0.0266% | -0.0022% |
| **high** | -0.0562% | -0.0110% | -0.0896% | -0.0495% | -0.0665% |


**Predicted (additive model):**

| \ | contracting | downtrend | expanding | sideways | uptrend |
|---|---|---|---|---|---|
| **low** | +0.0695% | +0.1188% | +0.0723% | +0.0912% | +0.0574% |
| **mid** | +0.0032% | +0.0525% | +0.0061% | +0.0249% | -0.0088% |
| **high** | -0.0669% | -0.0176% | -0.0641% | -0.0452% | -0.0790% |


**Residual (interaction signal):**

| \ | contracting | downtrend | expanding | sideways | uptrend |
|---|---|---|---|---|---|
| **low** | +0.0163% | -0.0088% | +0.0091% | +0.0025% | -0.0191% |
| **mid** | -0.0270% | +0.0021% | +0.0164% | +0.0017% | +0.0067% |
| **high** | +0.0107% | +0.0066% | -0.0255% | -0.0043% | +0.0125% |


**Verdict:** 15 reliable cells. Largest residual -0.0270% at LPL=mid/Structure=contracting. Row spread 0.1364%, col spread 0.0613%. Residual/spread ratio 20% — mostly ADDITIVE.


### Time stability (4h) of reliable cells

- **LPL=low, Structure=contracting**: 6/7 years same sign (aggregate median +0.0758%)
- **LPL=low, Structure=downtrend**: 7/7 years same sign (aggregate median +0.0970%)
- **LPL=low, Structure=expanding**: 6/7 years same sign (aggregate median +0.0715%)
- **LPL=low, Structure=sideways**: 6/7 years same sign (aggregate median +0.0783%)
- **LPL=low, Structure=uptrend**: 7/7 years same sign (aggregate median +0.0238%)
- **LPL=mid, Structure=contracting**: 6/7 years same sign (aggregate median -0.0248%)
- **LPL=mid, Structure=downtrend**: 7/7 years same sign (aggregate median +0.0636%)
- **LPL=mid, Structure=expanding**: 4/7 years same sign (aggregate median +0.0324%)
- **LPL=mid, Structure=sideways**: 6/7 years same sign (aggregate median +0.0194%)
- **LPL=mid, Structure=uptrend**: 2/7 years same sign (aggregate median -0.0275%)
- **LPL=high, Structure=contracting**: 6/7 years same sign (aggregate median -0.0572%)
- **LPL=high, Structure=downtrend**: 3/7 years same sign (aggregate median -0.0173%)
- **LPL=high, Structure=expanding**: 6/7 years same sign (aggregate median -0.0654%)
- **LPL=high, Structure=sideways**: 6/7 years same sign (aggregate median -0.0691%)
- **LPL=high, Structure=uptrend**: 7/7 years same sign (aggregate median -0.0592%)

