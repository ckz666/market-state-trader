# Phase D discovery v1 — Recovery-state (Class D') definition exploration

Generated 2026-07-26T15:35:56.925093+00:00.

Still not a position-management rule. Discovery only (2020-2025) -- per phase_d_path_state_hypothesis.md SS7, mechanic definition work stays on Discovery data; 2026 is untouched here. Same widened LPL==Q1-across-all-volatility-quintiles diagnostic population as phase_c_trade_path_analysis_v3/v4 (decision_rule_v1 itself only fires at Volatility==Q5). Cells with n < 15 are marked instead of reported, per the same discipline used throughout this project.

Goal is NOT to find the single best deep-drawdown threshold. It is to see whether a RANGE of plausible thresholds/definitions shows the same qualitative structure (P(winner) falling from State 1 to State 2 to State 3) -- a stable range is a much stronger result than one threshold that happens to separate best.

---

## A. Recovery-state stability across deep-drawdown thresholds

Definition 1 recovery ('DD_current back above the deep threshold it dropped below'). For each volatility quintile, pre-terminal time checkpoint, and candidate deep-drawdown threshold: State 1 = never reached that depth by t, State 2 = reached it but has since recovered (by this definition), State 3 = reached it and is still there at t. 'Ordering' flags whether P(winner|S1) > P(winner|S2) > P(winner|S3) holds where all three cells clear the n >= 15 floor -- looking for a stable RANGE, not a single optimal threshold.


### Volatility Q1

| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |
|---|---|---|---|---|---|
| 15m | -0.25% | 35% (n=425) | 44% (n=16) | 16% (n=25) | no |
| 15m | -0.50% | 35% (n=458) | n=2 | n=6 | n/a |
| 15m | -0.75% | 35% (n=461) | n=1 | n=4 | n/a |
| 15m | -1.00% | 35% (n=461) | n=2 | n=3 | n/a |
| 15m | -1.25% | 35% (n=463) | n=2 | n=1 | n/a |
| 15m | -1.50% | 35% (n=464) | n=1 | n=1 | n/a |
| 15m | -2.00% | 35% (n=466) | n=0 | n=0 | n/a |
| 15m | -2.50% | 35% (n=466) | n=0 | n=0 | n/a |
| 15m | -3.00% | 35% (n=466) | n=0 | n=0 | n/a |
| 30m | -0.25% | 35% (n=387) | 39% (n=41) | 21% (n=38) | no |
| 30m | -0.50% | 36% (n=444) | n=10 | n=12 | n/a |
| 30m | -0.75% | 35% (n=456) | n=3 | n=7 | n/a |
| 30m | -1.00% | 35% (n=459) | n=3 | n=4 | n/a |
| 30m | -1.25% | 35% (n=462) | n=1 | n=3 | n/a |
| 30m | -1.50% | 35% (n=464) | n=1 | n=1 | n/a |
| 30m | -2.00% | 35% (n=465) | n=0 | n=1 | n/a |
| 30m | -2.50% | 35% (n=466) | n=0 | n=0 | n/a |
| 30m | -3.00% | 35% (n=466) | n=0 | n=0 | n/a |
| 1h | -0.25% | 38% (n=334) | 33% (n=69) | 16% (n=63) | yes |
| 1h | -0.50% | 37% (n=426) | n=13 | 7% (n=27) | n/a |
| 1h | -0.75% | 36% (n=444) | n=9 | n=13 | n/a |
| 1h | -1.00% | 35% (n=456) | n=6 | n=4 | n/a |
| 1h | -1.25% | 35% (n=460) | n=3 | n=3 | n/a |
| 1h | -1.50% | 35% (n=463) | n=0 | n=3 | n/a |
| 1h | -2.00% | 35% (n=464) | n=0 | n=2 | n/a |
| 1h | -2.50% | 35% (n=464) | n=0 | n=2 | n/a |
| 1h | -3.00% | 35% (n=464) | n=0 | n=2 | n/a |
| 2h | -0.25% | 45% (n=272) | 34% (n=106) | 3% (n=88) | yes |
| 2h | -0.50% | 39% (n=387) | 23% (n=35) | 2% (n=44) | yes |
| 2h | -0.75% | 38% (n=416) | 22% (n=18) | 0% (n=32) | yes |
| 2h | -1.00% | 37% (n=432) | n=12 | 0% (n=22) | n/a |
| 2h | -1.25% | 36% (n=446) | n=6 | n=14 | n/a |
| 2h | -1.50% | 36% (n=451) | n=6 | n=9 | n/a |
| 2h | -2.00% | 35% (n=459) | n=2 | n=5 | n/a |
| 2h | -2.50% | 35% (n=462) | n=0 | n=4 | n/a |
| 2h | -3.00% | 35% (n=462) | n=1 | n=3 | n/a |
| 3h | -0.25% | 49% (n=233) | 34% (n=133) | 1% (n=100) | yes |
| 3h | -0.50% | 42% (n=354) | 26% (n=46) | 0% (n=66) | yes |
| 3h | -0.75% | 40% (n=392) | 12% (n=32) | 0% (n=42) | yes |
| 3h | -1.00% | 38% (n=416) | 15% (n=20) | 0% (n=30) | yes |
| 3h | -1.25% | 37% (n=433) | n=13 | 0% (n=20) | n/a |
| 3h | -1.50% | 36% (n=442) | n=9 | 0% (n=15) | n/a |
| 3h | -2.00% | 35% (n=455) | n=3 | n=8 | n/a |
| 3h | -2.50% | 35% (n=458) | n=0 | n=8 | n/a |
| 3h | -3.00% | 35% (n=460) | n=2 | n=4 | n/a |

### Volatility Q2

| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |
|---|---|---|---|---|---|
| 15m | -0.25% | 49% (n=540) | 37% (n=68) | 14% (n=79) | yes |
| 15m | -0.50% | 46% (n=641) | 16% (n=19) | 7% (n=27) | yes |
| 15m | -0.75% | 45% (n=666) | n=7 | n=14 | n/a |
| 15m | -1.00% | 45% (n=675) | n=6 | n=6 | n/a |
| 15m | -1.25% | 44% (n=681) | n=4 | n=2 | n/a |
| 15m | -1.50% | 44% (n=683) | n=4 | n=0 | n/a |
| 15m | -2.00% | 44% (n=687) | n=0 | n=0 | n/a |
| 15m | -2.50% | 44% (n=687) | n=0 | n=0 | n/a |
| 15m | -3.00% | 44% (n=687) | n=0 | n=0 | n/a |
| 30m | -0.25% | 52% (n=480) | 37% (n=103) | 13% (n=104) | yes |
| 30m | -0.50% | 48% (n=603) | 26% (n=38) | 9% (n=46) | yes |
| 30m | -0.75% | 46% (n=646) | n=12 | 7% (n=29) | n/a |
| 30m | -1.00% | 46% (n=659) | n=11 | 0% (n=17) | n/a |
| 30m | -1.25% | 45% (n=669) | n=10 | n=8 | n/a |
| 30m | -1.50% | 45% (n=676) | n=7 | n=4 | n/a |
| 30m | -2.00% | 44% (n=686) | n=0 | n=1 | n/a |
| 30m | -2.50% | 44% (n=687) | n=0 | n=0 | n/a |
| 30m | -3.00% | 44% (n=687) | n=0 | n=0 | n/a |
| 1h | -0.25% | 55% (n=398) | 41% (n=138) | 19% (n=151) | yes |
| 1h | -0.50% | 51% (n=548) | 29% (n=65) | 9% (n=74) | yes |
| 1h | -0.75% | 48% (n=614) | 22% (n=27) | 7% (n=46) | yes |
| 1h | -1.00% | 47% (n=639) | 8% (n=25) | 0% (n=23) | yes |
| 1h | -1.25% | 46% (n=656) | n=13 | 0% (n=18) | n/a |
| 1h | -1.50% | 45% (n=668) | n=6 | n=13 | n/a |
| 1h | -2.00% | 45% (n=679) | n=5 | n=3 | n/a |
| 1h | -2.50% | 44% (n=684) | n=1 | n=2 | n/a |
| 1h | -3.00% | 44% (n=687) | n=0 | n=0 | n/a |
| 2h | -0.25% | 65% (n=310) | 45% (n=192) | 9% (n=185) | yes |
| 2h | -0.50% | 57% (n=463) | 32% (n=109) | 3% (n=115) | yes |
| 2h | -0.75% | 53% (n=548) | 18% (n=66) | 4% (n=73) | yes |
| 2h | -1.00% | 50% (n=593) | 9% (n=47) | 4% (n=47) | yes |
| 2h | -1.25% | 48% (n=631) | 8% (n=24) | 0% (n=32) | yes |
| 2h | -1.50% | 47% (n=647) | 0% (n=16) | 0% (n=24) | no |
| 2h | -2.00% | 45% (n=668) | n=8 | n=11 | n/a |
| 2h | -2.50% | 45% (n=676) | n=6 | n=5 | n/a |
| 2h | -3.00% | 44% (n=683) | n=2 | n=2 | n/a |
| 3h | -0.25% | 71% (n=277) | 48% (n=209) | 2% (n=201) | yes |
| 3h | -0.50% | 63% (n=412) | 30% (n=138) | 1% (n=137) | yes |
| 3h | -0.75% | 57% (n=503) | 18% (n=82) | 0% (n=102) | yes |
| 3h | -1.00% | 53% (n=557) | 9% (n=68) | 0% (n=62) | yes |
| 3h | -1.25% | 50% (n=601) | 5% (n=40) | 0% (n=46) | yes |
| 3h | -1.50% | 49% (n=621) | 0% (n=31) | 0% (n=35) | no |
| 3h | -2.00% | 46% (n=655) | n=14 | 0% (n=18) | n/a |
| 3h | -2.50% | 45% (n=666) | n=14 | n=7 | n/a |
| 3h | -3.00% | 45% (n=680) | n=3 | n=4 | n/a |

### Volatility Q3

| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |
|---|---|---|---|---|---|
| 15m | -0.25% | 50% (n=611) | 41% (n=100) | 24% (n=128) | yes |
| 15m | -0.50% | 47% (n=771) | 25% (n=28) | 25% (n=40) | no |
| 15m | -0.75% | 46% (n=807) | 53% (n=15) | 12% (n=17) | no |
| 15m | -1.00% | 46% (n=822) | n=11 | n=6 | n/a |
| 15m | -1.25% | 45% (n=833) | n=4 | n=2 | n/a |
| 15m | -1.50% | 45% (n=837) | n=1 | n=1 | n/a |
| 15m | -2.00% | 45% (n=838) | n=0 | n=1 | n/a |
| 15m | -2.50% | 45% (n=838) | n=0 | n=1 | n/a |
| 15m | -3.00% | 45% (n=838) | n=0 | n=1 | n/a |
| 30m | -0.25% | 55% (n=506) | 37% (n=187) | 23% (n=146) | yes |
| 30m | -0.50% | 50% (n=697) | 27% (n=63) | 18% (n=79) | yes |
| 30m | -0.75% | 47% (n=767) | 35% (n=40) | 6% (n=32) | yes |
| 30m | -1.00% | 47% (n=798) | 29% (n=21) | 10% (n=20) | yes |
| 30m | -1.25% | 46% (n=815) | n=11 | n=13 | n/a |
| 30m | -1.50% | 46% (n=829) | n=2 | n=8 | n/a |
| 30m | -2.00% | 45% (n=833) | n=2 | n=4 | n/a |
| 30m | -2.50% | 45% (n=836) | n=1 | n=2 | n/a |
| 30m | -3.00% | 45% (n=837) | n=0 | n=2 | n/a |
| 1h | -0.25% | 60% (n=403) | 44% (n=225) | 19% (n=211) | yes |
| 1h | -0.50% | 54% (n=602) | 33% (n=110) | 13% (n=127) | yes |
| 1h | -0.75% | 51% (n=697) | 30% (n=61) | 12% (n=81) | yes |
| 1h | -1.00% | 49% (n=750) | 19% (n=43) | 9% (n=46) | yes |
| 1h | -1.25% | 47% (n=794) | 12% (n=16) | 10% (n=29) | yes |
| 1h | -1.50% | 46% (n=816) | n=7 | 6% (n=16) | n/a |
| 1h | -2.00% | 46% (n=829) | n=4 | n=6 | n/a |
| 1h | -2.50% | 46% (n=835) | n=1 | n=3 | n/a |
| 1h | -3.00% | 45% (n=836) | n=1 | n=2 | n/a |
| 2h | -0.25% | 70% (n=305) | 47% (n=300) | 11% (n=234) | yes |
| 2h | -0.50% | 61% (n=516) | 35% (n=157) | 7% (n=166) | yes |
| 2h | -0.75% | 55% (n=621) | 26% (n=111) | 7% (n=107) | yes |
| 2h | -1.00% | 53% (n=690) | 20% (n=71) | 4% (n=78) | yes |
| 2h | -1.25% | 50% (n=739) | 15% (n=47) | 6% (n=53) | yes |
| 2h | -1.50% | 48% (n=776) | 7% (n=30) | 6% (n=33) | yes |
| 2h | -2.00% | 47% (n=808) | 7% (n=15) | 0% (n=16) | yes |
| 2h | -2.50% | 46% (n=826) | n=5 | n=8 | n/a |
| 2h | -3.00% | 46% (n=828) | n=4 | n=7 | n/a |
| 3h | -0.25% | 77% (n=263) | 53% (n=319) | 4% (n=257) | yes |
| 3h | -0.50% | 66% (n=463) | 36% (n=195) | 2% (n=181) | yes |
| 3h | -0.75% | 60% (n=570) | 27% (n=144) | 1% (n=125) | yes |
| 3h | -1.00% | 56% (n=651) | 18% (n=95) | 1% (n=93) | yes |
| 3h | -1.25% | 53% (n=700) | 13% (n=75) | 0% (n=64) | yes |
| 3h | -1.50% | 50% (n=745) | 10% (n=42) | 0% (n=52) | yes |
| 3h | -2.00% | 49% (n=780) | 3% (n=30) | 0% (n=29) | yes |
| 3h | -2.50% | 47% (n=807) | 0% (n=15) | 0% (n=17) | no |
| 3h | -3.00% | 47% (n=817) | n=14 | n=8 | n/a |

### Volatility Q4

| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |
|---|---|---|---|---|---|
| 15m | -0.25% | 52% (n=603) | 37% (n=178) | 28% (n=200) | yes |
| 15m | -0.50% | 47% (n=852) | 36% (n=59) | 23% (n=70) | yes |
| 15m | -0.75% | 45% (n=924) | 35% (n=26) | 19% (n=31) | yes |
| 15m | -1.00% | 45% (n=951) | n=12 | 11% (n=18) | n/a |
| 15m | -1.25% | 45% (n=964) | n=7 | n=10 | n/a |
| 15m | -1.50% | 45% (n=971) | n=3 | n=7 | n/a |
| 15m | -2.00% | 45% (n=975) | n=2 | n=4 | n/a |
| 15m | -2.50% | 44% (n=978) | n=0 | n=3 | n/a |
| 15m | -3.00% | 44% (n=978) | n=1 | n=2 | n/a |
| 30m | -0.25% | 56% (n=496) | 39% (n=256) | 24% (n=229) | yes |
| 30m | -0.50% | 49% (n=750) | 34% (n=116) | 22% (n=115) | yes |
| 30m | -0.75% | 47% (n=856) | 36% (n=58) | 15% (n=67) | yes |
| 30m | -1.00% | 46% (n=908) | 33% (n=33) | 10% (n=40) | yes |
| 30m | -1.25% | 46% (n=937) | 14% (n=22) | 9% (n=22) | yes |
| 30m | -1.50% | 45% (n=957) | n=11 | n=13 | n/a |
| 30m | -2.00% | 45% (n=971) | n=4 | n=6 | n/a |
| 30m | -2.50% | 44% (n=976) | n=3 | n=2 | n/a |
| 30m | -3.00% | 44% (n=978) | n=1 | n=2 | n/a |
| 1h | -0.25% | 61% (n=396) | 45% (n=317) | 19% (n=268) | yes |
| 1h | -0.50% | 54% (n=640) | 36% (n=182) | 16% (n=159) | yes |
| 1h | -0.75% | 51% (n=754) | 32% (n=114) | 12% (n=113) | yes |
| 1h | -1.00% | 48% (n=846) | 31% (n=61) | 11% (n=74) | yes |
| 1h | -1.25% | 47% (n=889) | 20% (n=50) | 7% (n=42) | yes |
| 1h | -1.50% | 46% (n=919) | 21% (n=34) | 7% (n=28) | yes |
| 1h | -2.00% | 46% (n=948) | 10% (n=20) | n=13 | n/a |
| 1h | -2.50% | 45% (n=969) | n=9 | n=3 | n/a |
| 1h | -3.00% | 45% (n=975) | n=4 | n=2 | n/a |
| 2h | -0.25% | 73% (n=290) | 47% (n=386) | 13% (n=305) | yes |
| 2h | -0.50% | 62% (n=509) | 37% (n=266) | 9% (n=206) | yes |
| 2h | -0.75% | 57% (n=648) | 31% (n=183) | 7% (n=150) | yes |
| 2h | -1.00% | 52% (n=755) | 29% (n=114) | 5% (n=112) | yes |
| 2h | -1.25% | 51% (n=813) | 24% (n=83) | 5% (n=85) | yes |
| 2h | -1.50% | 49% (n=860) | 22% (n=60) | 3% (n=61) | yes |
| 2h | -2.00% | 47% (n=910) | 15% (n=39) | 0% (n=32) | yes |
| 2h | -2.50% | 46% (n=937) | 15% (n=27) | 0% (n=17) | yes |
| 2h | -3.00% | 45% (n=957) | 6% (n=17) | n=7 | n/a |
| 3h | -0.25% | 80% (n=248) | 54% (n=410) | 4% (n=323) | yes |
| 3h | -0.50% | 69% (n=440) | 42% (n=299) | 3% (n=242) | yes |
| 3h | -0.75% | 62% (n=577) | 35% (n=214) | 1% (n=190) | yes |
| 3h | -1.00% | 58% (n=672) | 27% (n=162) | 1% (n=147) | yes |
| 3h | -1.25% | 55% (n=737) | 21% (n=125) | 0% (n=119) | yes |
| 3h | -1.50% | 53% (n=793) | 19% (n=95) | 0% (n=93) | yes |
| 3h | -2.00% | 49% (n=865) | 12% (n=69) | 0% (n=47) | yes |
| 3h | -2.50% | 47% (n=918) | 13% (n=38) | 0% (n=25) | yes |
| 3h | -3.00% | 46% (n=944) | 9% (n=22) | 0% (n=15) | yes |

### Volatility Q5

| Time | Deep <= | State 1: never deep | State 2: deep->recovered | State 3: deep->still impaired | Ordering S1>S2>S3 |
|---|---|---|---|---|---|
| 15m | -0.25% | 58% (n=494) | 56% (n=251) | 37% (n=319) | yes |
| 15m | -0.50% | 55% (n=743) | 54% (n=145) | 35% (n=176) | yes |
| 15m | -0.75% | 53% (n=876) | 49% (n=80) | 38% (n=108) | yes |
| 15m | -1.00% | 53% (n=945) | 43% (n=56) | 38% (n=63) | yes |
| 15m | -1.25% | 52% (n=990) | 39% (n=36) | 47% (n=38) | no |
| 15m | -1.50% | 52% (n=1020) | 56% (n=18) | 38% (n=26) | no |
| 15m | -2.00% | 51% (n=1042) | n=9 | n=13 | n/a |
| 15m | -2.50% | 51% (n=1054) | n=1 | n=9 | n/a |
| 15m | -3.00% | 51% (n=1055) | n=3 | n=6 | n/a |
| 30m | -0.25% | 62% (n=395) | 57% (n=319) | 34% (n=350) | yes |
| 30m | -0.50% | 59% (n=620) | 52% (n=219) | 31% (n=225) | yes |
| 30m | -0.75% | 57% (n=770) | 45% (n=152) | 29% (n=142) | yes |
| 30m | -1.00% | 55% (n=858) | 43% (n=114) | 30% (n=92) | yes |
| 30m | -1.25% | 53% (n=921) | 51% (n=76) | 30% (n=67) | yes |
| 30m | -1.50% | 53% (n=963) | 50% (n=58) | 23% (n=43) | yes |
| 30m | -2.00% | 52% (n=1012) | 48% (n=31) | 24% (n=21) | yes |
| 30m | -2.50% | 52% (n=1038) | n=13 | n=13 | n/a |
| 30m | -3.00% | 52% (n=1045) | n=8 | n=11 | n/a |
| 1h | -0.25% | 70% (n=293) | 59% (n=388) | 30% (n=383) | yes |
| 1h | -0.50% | 65% (n=489) | 52% (n=293) | 28% (n=282) | yes |
| 1h | -0.75% | 60% (n=637) | 51% (n=218) | 24% (n=209) | yes |
| 1h | -1.00% | 59% (n=733) | 44% (n=176) | 24% (n=155) | yes |
| 1h | -1.25% | 57% (n=806) | 42% (n=144) | 21% (n=114) | yes |
| 1h | -1.50% | 56% (n=859) | 40% (n=119) | 19% (n=86) | yes |
| 1h | -2.00% | 54% (n=957) | 44% (n=59) | 17% (n=48) | yes |
| 1h | -2.50% | 53% (n=998) | 56% (n=36) | 7% (n=30) | no |
| 1h | -3.00% | 52% (n=1020) | 46% (n=28) | 12% (n=16) | yes |
| 2h | -0.25% | 79% (n=225) | 65% (n=455) | 18% (n=384) | yes |
| 2h | -0.50% | 73% (n=382) | 59% (n=367) | 16% (n=315) | yes |
| 2h | -0.75% | 67% (n=519) | 58% (n=286) | 13% (n=259) | yes |
| 2h | -1.00% | 65% (n=616) | 53% (n=234) | 12% (n=214) | yes |
| 2h | -1.25% | 62% (n=695) | 48% (n=194) | 11% (n=175) | yes |
| 2h | -1.50% | 61% (n=751) | 43% (n=178) | 9% (n=135) | yes |
| 2h | -2.00% | 58% (n=861) | 36% (n=107) | 8% (n=96) | yes |
| 2h | -2.50% | 56% (n=924) | 35% (n=80) | 5% (n=60) | yes |
| 2h | -3.00% | 54% (n=971) | 33% (n=54) | 5% (n=39) | yes |
| 3h | -0.25% | 88% (n=190) | 70% (n=475) | 12% (n=399) | yes |
| 3h | -0.50% | 80% (n=329) | 63% (n=413) | 7% (n=322) | yes |
| 3h | -0.75% | 74% (n=450) | 57% (n=354) | 5% (n=260) | yes |
| 3h | -1.00% | 71% (n=545) | 52% (n=293) | 4% (n=226) | yes |
| 3h | -1.25% | 68% (n=624) | 48% (n=242) | 3% (n=198) | yes |
| 3h | -1.50% | 66% (n=676) | 44% (n=220) | 1% (n=168) | yes |
| 3h | -2.00% | 62% (n=805) | 33% (n=135) | 2% (n=124) | yes |
| 3h | -2.50% | 60% (n=856) | 27% (n=113) | 2% (n=95) | yes |
| 3h | -3.00% | 57% (n=918) | 23% (n=84) | 3% (n=62) | yes |

---

## B. Recovery-definition sensitivity

Fixed at deep-threshold <= -1.0%, times 1h, 2h. Among trades that reached this deep threshold by time t, how does the recovered/impaired split (and each side's win rate) change depending on which 'recovered' definition is used?

- **Def 1** -- `DD_current > threshold` (no longer as deep as the threshold itself).
- **Def 2 (margin X)** -- `DD_current >= MAE_so_far(t) + X` (recovered by at least X from the trade's own low point, regardless of the fixed threshold).
- **Def 3 (residual)** -- `DD_current >= residual` (back to within a small absolute distance of breakeven, a stricter bar than Def 1/2).


### Volatility Q1

| Time | Definition | n deep (total) | Recovered | Impaired |
|---|---|---|---|---|
| 1h | Def 1: back above threshold | 10 | n=6 | n=4 |
| 1h | Def 2: margin +0.25% from own low | 10 | n=6 | n=4 |
| 1h | Def 2: margin +0.50% from own low | 10 | n=3 | n=7 |
| 1h | Def 3: residual <= -0.25% of breakeven | 10 | n=1 | n=9 |
| 1h | Def 3: residual <= -0.50% of breakeven | 10 | n=1 | n=9 |
| 2h | Def 1: back above threshold | 34 | n=12 | 0% (n=22) |
| 2h | Def 2: margin +0.25% from own low | 34 | 19% (n=16) | 0% (n=18) |
| 2h | Def 2: margin +0.50% from own low | 34 | n=11 | 4% (n=23) |
| 2h | Def 3: residual <= -0.25% of breakeven | 34 | n=2 | 3% (n=32) |
| 2h | Def 3: residual <= -0.50% of breakeven | 34 | n=5 | 3% (n=29) |

### Volatility Q2

| Time | Definition | n deep (total) | Recovered | Impaired |
|---|---|---|---|---|
| 1h | Def 1: back above threshold | 48 | 8% (n=25) | 0% (n=23) |
| 1h | Def 2: margin +0.25% from own low | 48 | 3% (n=29) | 5% (n=19) |
| 1h | Def 2: margin +0.50% from own low | 48 | 7% (n=15) | 3% (n=33) |
| 1h | Def 3: residual <= -0.25% of breakeven | 48 | n=3 | 2% (n=45) |
| 1h | Def 3: residual <= -0.50% of breakeven | 48 | n=7 | 2% (n=41) |
| 2h | Def 1: back above threshold | 94 | 9% (n=47) | 4% (n=47) |
| 2h | Def 2: margin +0.25% from own low | 94 | 6% (n=62) | 6% (n=32) |
| 2h | Def 2: margin +0.50% from own low | 94 | 8% (n=38) | 5% (n=56) |
| 2h | Def 3: residual <= -0.25% of breakeven | 94 | n=4 | 4% (n=90) |
| 2h | Def 3: residual <= -0.50% of breakeven | 94 | n=12 | 5% (n=82) |

### Volatility Q3

| Time | Definition | n deep (total) | Recovered | Impaired |
|---|---|---|---|---|
| 1h | Def 1: back above threshold | 89 | 19% (n=43) | 9% (n=46) |
| 1h | Def 2: margin +0.25% from own low | 89 | 19% (n=43) | 9% (n=46) |
| 1h | Def 2: margin +0.50% from own low | 89 | 27% (n=22) | 9% (n=67) |
| 1h | Def 3: residual <= -0.25% of breakeven | 89 | n=6 | 12% (n=83) |
| 1h | Def 3: residual <= -0.50% of breakeven | 89 | n=11 | 10% (n=78) |
| 2h | Def 1: back above threshold | 149 | 20% (n=71) | 4% (n=78) |
| 2h | Def 2: margin +0.25% from own low | 149 | 15% (n=102) | 4% (n=47) |
| 2h | Def 2: margin +0.50% from own low | 149 | 15% (n=75) | 8% (n=74) |
| 2h | Def 3: residual <= -0.25% of breakeven | 149 | 33% (n=18) | 8% (n=131) |
| 2h | Def 3: residual <= -0.50% of breakeven | 149 | 30% (n=27) | 7% (n=122) |

### Volatility Q4

| Time | Definition | n deep (total) | Recovered | Impaired |
|---|---|---|---|---|
| 1h | Def 1: back above threshold | 135 | 31% (n=61) | 11% (n=74) |
| 1h | Def 2: margin +0.25% from own low | 135 | 26% (n=89) | 9% (n=46) |
| 1h | Def 2: margin +0.50% from own low | 135 | 32% (n=66) | 9% (n=69) |
| 1h | Def 3: residual <= -0.25% of breakeven | 135 | 60% (n=20) | 13% (n=115) |
| 1h | Def 3: residual <= -0.50% of breakeven | 135 | 48% (n=29) | 12% (n=106) |
| 2h | Def 1: back above threshold | 226 | 29% (n=114) | 5% (n=112) |
| 2h | Def 2: margin +0.25% from own low | 226 | 20% (n=173) | 9% (n=53) |
| 2h | Def 2: margin +0.50% from own low | 226 | 23% (n=140) | 8% (n=86) |
| 2h | Def 3: residual <= -0.25% of breakeven | 226 | 47% (n=45) | 10% (n=181) |
| 2h | Def 3: residual <= -0.50% of breakeven | 226 | 41% (n=64) | 8% (n=162) |

### Volatility Q5

| Time | Definition | n deep (total) | Recovered | Impaired |
|---|---|---|---|---|
| 1h | Def 1: back above threshold | 331 | 44% (n=176) | 24% (n=155) |
| 1h | Def 2: margin +0.25% from own low | 331 | 37% (n=259) | 25% (n=72) |
| 1h | Def 2: margin +0.50% from own low | 331 | 41% (n=205) | 25% (n=126) |
| 1h | Def 3: residual <= -0.25% of breakeven | 331 | 61% (n=74) | 27% (n=257) |
| 1h | Def 3: residual <= -0.50% of breakeven | 331 | 52% (n=99) | 28% (n=232) |
| 2h | Def 1: back above threshold | 448 | 53% (n=234) | 12% (n=214) |
| 2h | Def 2: margin +0.25% from own low | 448 | 35% (n=391) | 21% (n=57) |
| 2h | Def 2: margin +0.50% from own low | 448 | 40% (n=334) | 14% (n=114) |
| 2h | Def 3: residual <= -0.25% of breakeven | 448 | 69% (n=131) | 18% (n=317) |
| 2h | Def 3: residual <= -0.50% of breakeven | 448 | 63% (n=162) | 16% (n=286) |
