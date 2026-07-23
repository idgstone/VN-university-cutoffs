# Source reliability reconciliation

tuyensinh247 is an **aggregator**, so a sample of its published values is checked against primary /
independent-authoritative sources. Results are reported **separately by era** and never blended —
verification is far easier for recent years, and the one error found was itself recent, so the claim
must be scoped to what was actually checked (older records are plausibly *more* error-prone, not less).

## Method

- Samples drawn by seeded scripts (`seed=42` for the anomaly follow-up, `seed=2025` for the
  representative sample) over `data/processed/cutoffs_cs.csv`.
- Each sampled record's **as-published tuyensinh247 `mark`** (bronze) is compared to an independent
  source. Source type is labelled: *primary* (school/Ministry/government announcement) or
  *independent aggregator* (vietjack — a separate transcription of the official announcements).

## Era 1 — 2021–2025 (fetchable): 16 / 16 exact matches, 0 discrepancies (random sample)

| School·Year | records | result | source |
|---|---|---|---|
| UET 2023 | 7 | 7/7 exact | independent (vietjack); UET is VNU-published |
| PTIT 2024 | 7 | 7/7 exact | independent (vietjack) + **primary** (govt/news) for CNTT 26.4 & KHMT 26.31 |
| HUMG 2022 | 2 | 2/2 exact | primary-citing news (CNTT 23.0, CLC 23.5) |

Not verifiable this pass (source rendered behind lazy-load): HUST 2021 (8), HANU 2023 (2).

**Caveat — recent years are NOT assumed error-free:** a separate *targeted* check of the HUS 40-scale
anomaly (below) found a genuine 2024 error. So the random recent sample was clean, but the overall
observed error rate is **1 in 20 verified records (~5%)**, all in the verifiable (recent) era.

## Era 2 — 2019–2020 (time-boxed best-effort): 0 verified, ~13 unverifiable

Primary sources for 2019–2020 are **offline, 403-blocked, DNS-dead (government portal), image-based,
or paginated behind JS**; the independent aggregator hides pre-2021 years behind "Xem thêm" lazy-load.
Attempted: EPU 2020, HANU 2019, HUMG 2020, UET 2019 → none machine-verifiable within the effort ceiling.
**No reliability claim is made for 2019–2020.** (One false alarm resolved: a "HANU 2019 = 20.6" figure
was **ĐH Mở Hà Nội**, a different school; HANU's IT program is 30-scale — IT is exempt from HANU's
foreign-language ×2 — consistent with our 22.15.) The disappearance of historical primary sources is
itself a finding that motivates a maintained structured dataset.

## Anomaly cross-validation (sample #1, HUS 2023–24, targeted not random)

QHT93 2023 34.85 ✓ · QHT93 2024 35 ✓ · QHT98 2023 34.7 ✓ · **QHT98 2024 34.0 ✗ → 34.7** (corrected in
silver, see `config/mark_corrections.csv`). 3/4 match, 1 error — the error that sets the ~5% rate.

## Bottom line (scope-honest)

- **2021–2025:** 16/16 randomly-sampled records matched exactly; 1 error found by targeted check →
  observed error rate ~5% (1/20) in the verifiable era.
- **2019–2020:** not verifiable — primary sources no longer accessible; no claim made.
- Still worth doing if sources surface: verify HUST 2021 / HANU 2023 and any recoverable 2019–2020.
