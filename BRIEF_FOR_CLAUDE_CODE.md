# Brief for Claude Code — Vietnamese University Admission-Cutoff Dataset

> **Read the "How to work with me" section before writing any code.**
> This is a portfolio project that I (Nguyen) have to defend in interviews. The design decisions are
> mine and I must be able to explain them. Your role (Claude Code) is to **help me test and execute my
> decisions, NOT to make the big decisions for me.**

---

## How to work with me (most important)

1. **Don't make big design decisions for me.** When something is ambiguous (schema, matching approach,
   data source, thresholds...), **stop and ask me**, lay out the options with their trade-offs, and let
   me choose. Do not "fill in" gaps with guesses and just code them.
2. **MVP first, expand later.** Finish one industry group *properly* before we discuss a second one.
   Do not scaffold for multiple groups while the first one is unfinished.
3. **Explain "why", not just "what".** When you propose an approach, state why you chose it and its
   weaknesses, so I can put it in the README and defend it.
4. **Prioritize me understanding over me getting output.** If I've misunderstood something, correct me —
   I prefer direct feedback.
5. **Honest numbers only.** Never produce a figure the pipeline can't reproduce. Every figure must trace
   back to the code that generated it.

---

## Objective

Build and publish a **machine-readable dataset of Vietnamese university admission cutoff scores
("điểm chuẩn") across multiple years**, structured so that for a given year, a given major, at a given
university, you can look up the cutoff. Ship it with **public pipeline code on GitHub** that another
person can download and reproduce, plus a **README that tells the story of the decisions.**

## Scope (locked) — MVP

- **Industry group:** **Computing & Information Technology only** (an official field group per the
  Ministry of Education & Training's classification). This is the MVP. Other groups (Health/Medicine,
  Business & Management, Education) are **later phases, only if the first group is properly done** —
  NOT committed to up front.
- **Region:** universities in **Hanoi**.
- **Time dimension:** multiple years (exact number depends on data availability — must survey first).
- **Analytical story:** compare the **cutoff scores of the same major across universities and across
  years**. Note: call it "cutoff score", NOT "popularity/hotness" — a high cutoff can come from many
  causes (small quota, school prestige...), not just demand.

## Data sources

- Intended aggregator source: **tuyensinh247** (and/or similar). **Must check `robots.txt` and terms of
  use BEFORE crawling.** If forbidden → do not crawl, find another source.
- Because this is an aggregator (not a primary source), accuracy isn't guaranteed →
  **cross-validate a random sample (~5-10% of records)** against a primary source (the university's own
  site or the Ministry's announcements) to demonstrate reliability. Record this reconciliation result.
- Prefer tracing back to the **primary source** when possible; credit every source used.

## The hardest part = signature story (go deepest here)

**Entity matching / name normalization:** the same major or university is written many different ways
across years and schools (e.g. "Công nghệ thông tin" / "Khoa học máy tính" / "Kỹ thuật phần mềm" /
"CNTT - Chất lượng cao"). We need to:
- Build a normalize + matching step that collapses variants onto the same canonical entity.
- **Measure accuracy:** hand-label a sample (e.g. 50 pairs) as "same / different", compare against the
  matcher's output to compute **precision / recall**. This is the evidence that "I matched correctly".
- This is also the project's **AI/ML component** (could use embedding similarity, fuzzy match, or a
  rule-based + ML hybrid — discuss the choice with me).

## The three aspects the project must contain (per the brief)

- **Software engineering:** a reproducible pipeline (collect → clean → normalize → export a file).
- **Data engineering:** real collection, cleaning, and structuring of messy real-world data.
- **AI/ML:** at least one genuine ML component, with measurement (the entity matching above).

## Guardrails (never violate)

- **Respect the law & each site's terms.** Check robots.txt/ToS before scraping. Do NOT scrape sites
  that forbid it (Shopee, Lazada, Facebook, Zalo, LinkedIn...).
- **No personal data.** Work only at the aggregate / cutoff level. Do NOT collect or publish individual
  students' scores.
- **No paid compute / no always-on servers.** Free tiers only. This is a pipeline that produces a file,
  NOT a background service.

## Constraints

- Deliverable = a published, versioned dataset (Hugging Face and/or Kaggle) + a reproducible GitHub repo
  + a README telling the story of the decisions + one real ML component + I can defend the whole thing
  in an interview.

## Do this NOW (before coding)

1. **Survey the sources:** check robots.txt/ToS of the intended source; confirm that CS cutoff scores
   for Hanoi universities are available and consistent across how many years. Report back to me before
   building.
2. **Propose a schema** (with trade-offs) for me to approve — don't lock it yourself.
3. **Propose an entity-matching approach** (with weaknesses and how to measure precision/recall) for me
   to approve.

---

**Reminder:** anything ambiguous → ASK me, don't decide on your own. Get the one CS group done properly
first.
