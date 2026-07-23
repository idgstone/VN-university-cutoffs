# Source reliability reconciliation

tuyensinh247 is an **aggregator**, so a sample of its published values is checked against other
sources. Two axes of honesty are kept explicit and **never blended**:

1. **By era** — verification is far easier for recent years; older primary sources have largely
   disappeared, so no claim is made where nothing could be checked.
2. **By verification strength** — matching an *independent aggregator* is weaker than matching a
   *primary source*: two aggregators can share an upstream feed or copy each other, so agreement does
   not establish correctness. These are reported as separate strata, not summed.

Samples drawn by seeded scripts (`seed=42` anomaly follow-up, `seed=2025` representative) over
`data/processed/cutoffs_cs.csv`; each record's **as-published tuyensinh247 `mark`** (bronze) is
compared to the source.

## Random sample, 2021–2025 — 0 discrepancies / 16 checked

Broken out by verification strength (this is the honest structure — do not read "16" as 16 primary
confirmations):

| Stratum | records | result | source |
|---|---|---|---|
| **Primary / official-announcement** | 4 | 4/4 match | PTIT 2024 CNTT 26.4 & KHMT 26.31 (govt portal / news reporting PTIT's official announcement); HUMG 2022 CNTT 23.0 & CLC 23.5 (news citing the school's announcement) |
| **Independent-aggregator-corroborated only** | 12 | 12/12 match | vietjack (a *separate* aggregator): UET 2023 (7 majors) + the other 5 PTIT 2024 majors. Agreement ⇒ corroboration, **not** proof — possible shared upstream. |
| **Unverifiable this pass** | 10 | — | HUST 2021 (8), HANU 2023 (2): source behind lazy-load |

**Claim, scoped:** in the random 2021–2025 sample, **4/4 records checked against a primary source
matched**, and **12/12 more matched an independent aggregator**. 0 discrepancies found — but only 4
rest on primary confirmation.

## Targeted anomaly sample, HUS 2023–24 — 1 error / 4 (NOT extrapolable)

Non-random (deliberately selected the 40-scale outliers), so its error rate **cannot be pooled** with
the random sample. QHT93 2023 34.85 ✓ · QHT93 2024 35 ✓ · QHT98 2023 34.7 ✓ · **QHT98 2024 34.0 ✗ →
34.7** (corrected in silver via `config/mark_corrections.csv`). This proves recent years are **not**
assumed error-free — but it is a targeted finding, not a rate. (Earlier `~5% / 1-in-20` was an invalid
pooling of a targeted sample with a random one; withdrawn.)

## 2019–2020 — not verifiable (time-boxed best-effort)

Primary sources are **offline, 403-blocked, DNS-dead (government portal), image-based, or paginated
behind JS**; even the independent aggregator hides pre-2021 years behind "Xem thêm" lazy-load.
Attempted: EPU 2020, HANU 2019, HUMG 2020, UET 2019 → none machine-verifiable within the effort
ceiling. **No reliability claim is made for 2019–2020.** (One false alarm resolved: a "HANU 2019 =
20.6" figure is **ĐH Mở Hà Nội**, a different school; HANU's IT program is 30-scale — IT is exempt from
HANU's foreign-language ×2 — consistent with our 22.15.) The disappearance of historical primary
sources is itself a finding motivating a maintained structured dataset.

## Still worth doing if sources surface

Primary confirmation for the 12 aggregator-only records; HUST 2021 / HANU 2023; any recoverable
2019–2020. The reliability claim is deliberately scoped to what was actually checked, at the strength
it was checked.
