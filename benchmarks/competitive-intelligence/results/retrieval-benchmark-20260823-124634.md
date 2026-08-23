# Retrieval Benchmark — brave

- run_at: 2026-08-23T12:46:34+00:00
- backend: brave
- verdict: FAIL

## Aggregate

| Layer | Share | Threshold | Pass |
| --- | --- | --- | --- |
| DISCOVERY (official seed) | 91% | >= 80% | yes |
| READ | 83% | >= 90% | no |
| KEY FACT | 0% | >= 80% | no |

## Per case

| id | discovery | rank | snippet | date | fetch | type | chars | key fact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rm-official-product-index | yes | 1 | yes | no | success | text/html | 7610 | fail |
| rm-charger5 | yes | 1 | yes | no | success | text/html | 51009 | fail |
| rm-nevo5 | yes | 1 | yes | no | success | text/html | 61755 | fail |
| rm-delite5 | yes | 1 | yes | no | success | text/html | 32494 | fail |
| rm-superdelite5 | yes | 1 | yes | no | success | text/html | 23480 | fail |
| rm-load5-75 | yes | 1 | yes | no | success | text/html | 33648 | fail |
| rm-multitinker2 | yes | 1 | yes | no | success | text/html | 22217 | fail |
| rm-packster2-70-ct | yes | 1 | yes | no | success | text/html | 20266 | fail |
| rm-my2027 | no | unknown | yes | yes | not_attempted | - | - | not_measured |
| rm-veya-release | yes | 1 | yes | yes | success | text/html | 9909 | fail |
| rm-cargo-updates | yes | 1 | yes | yes | success | text/html | 10501 | fail |
| ziv-market-pdf | yes | 1 | yes | yes | failure | - | - | not_measured |

## Failures

- rm-official-product-index: fetch=success reason=- key=fail
- rm-charger5: fetch=success reason=- key=fail
- rm-nevo5: fetch=success reason=- key=fail
- rm-delite5: fetch=success reason=- key=fail
- rm-superdelite5: fetch=success reason=- key=fail
- rm-load5-75: fetch=success reason=- key=fail
- rm-multitinker2: fetch=success reason=- key=fail
- rm-packster2-70-ct: fetch=success reason=- key=fail
- rm-veya-release: fetch=success reason=- key=fail
- rm-cargo-updates: fetch=success reason=- key=fail
- ziv-market-pdf: fetch=failure reason=DOWNLOAD_TOO_LARGE: response from 'https://www.ziv-zweirad.de/wp-content/uploads/2026/03/Market-Data-Bicycle-Industry-2025.pdf' is 5269152 bytes, over the 5000000-byte cap key=not_measured
