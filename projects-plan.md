# Project Brief — Vietnamese University Admission-Cutoff Dataset

**What this is:** a project for you to build. It gives you the goal, why it's worth doing, and the bar
it has to clear — but **not** a step-by-step. The design and the build are yours to figure out, and
that's on purpose. The choices you make — how you structure the data, what tools you use, how you solve
the messy parts — are exactly what an interviewer will ask you to explain and defend. If someone hands
you those answers, you can't own them in the room. So make the decisions yourself, and **write down
*why* you made each one** as you go.

---

## The objective

Build and publish a **machine-readable dataset of Vietnamese university admission cutoff scores
("điểm chuẩn") covering multiple years** — structured so anyone can look up, for a given year, the
cutoff for a given major at a given university — together with the **public, reproducible code**
that produces it.

## Why this project is worth your time

- **It fills a real gap** (see below), so it's genuinely your own work — not a tutorial you followed.
- **It plays to your advantage.** The data is in Vietnamese, buried in PDFs and web pages with messy,
  inconsistent formatting. You can read and reason about it in ways most candidates can't.
- **It's memorable.** "I built the Vietnamese college-admissions dataset that didn't exist" is the kind
  of line an interviewer remembers.
- **It strengthens more than one job target.** From this single build you can pull a
  software-engineering story (the pipeline), a data-engineering story (collecting and cleaning messy
  real-world data), and an AI/machine-learning story (whatever model you add). One project, three angles.

## Why it's a real gap (so you can trust the idea)

Raw *individual-student* exam scores are all over Kaggle and GitHub — but only one year at a time, in
inconsistent formats, with no continuity between years. The thing people actually want — **cutoffs by
university × major × year, cleaned and unified across years** — exists nowhere as a downloadable dataset.
It's only available through lookup-only web portals and unstructured school announcement PDFs. Nobody has
assembled it into one clean, machine-readable set. (This has been confirmed by checking the existing
attempts — they all stop at raw single-year student scores.)

---

## Requirements — the must-haves

**What it must produce**
- A **published, versioned dataset** (on a public platform such as Hugging Face and/or Kaggle) covering
  **multiple years**.
- The **pipeline code, public on GitHub**, that another person could **download, run, and reproduce**.
- A **README that explains your decisions** — *why* you built it the way you did, not just what it does.

**The quality bar** — this is what separates a real project from a forgettable scraped spreadsheet.
Take it seriously:
- **Real technical depth.** The genuinely hard parts of this data must be *solved*, not glossed over.
  You *will* hit them: the formats change across years, the same school or major is written many
  different ways, the source documents are messy. How you solve these is the heart of your interview story.
- **Depth over breadth.** A smaller set done *cleanly, correctly, and documented* beats a big messy dump.
  Don't try to cover every school — cover a meaningful set *well*.
- **Honest numbers only.** Every figure you put in the README or on your résumé, you must be able to
  explain and reproduce on demand. If you can't defend a number, don't claim it.
- **You can talk about it for 20 minutes** — every major design choice, and what you'd do differently
  with more time.

**Constraints**
- **Work solo, roughly 8–10 weeks, part-time** — build it *alongside* your job applications, not before
  you start applying.
- **No paid computing and no always-on servers.** Use only free tools/tiers. This is a pipeline that
  produces a file — not a live service you have to keep running and paying for.
- **You don't need real users.** Don't spend time on launches or promotion. The published dataset and the
  code are the deliverables.

## It has to work as a software-engineering, data-engineering, AND AI project

So the build needs to genuinely contain all three of these — *how* you do each is your call:
- a real **engineering / pipeline** aspect (software engineering),
- a real **data collection, cleaning, and structuring** aspect (data engineering),
- at least one genuine **machine-learning** aspect (AI).

## Non-negotiable guardrails

- **Respect the law and each site's terms.** Check a site's `robots.txt` and terms of use *before*
  scraping it. Do **not** scrape sites that forbid it (for example Shopee, Lazada, Facebook, Zalo,
  LinkedIn). Prefer official and primary sources, and credit the sources you use.
- **No personal data.** Individual students' scores are personal information — do not collect or
  republish them. Work at the aggregate / cutoff level only.

---

## What's left to you (your decisions = your interview stories)

Don't expect these to be spelled out. They're your job, and they're what you'll be asked about:
- how you structure the data (the schema),
- where you get it, and which sources you decide to trust,
- how you handle the messy, changing formats across different years,
- how you decide that two differently-written names are the same school or major — and how you *check*
  that you got it right,
- what tools and pipeline design you use,
- what machine-learning piece you add, and how you measure whether it works,
- how you keep the project from sprawling so that you actually finish it.

## Definition of done

A **published, versioned dataset** + a **public repository anyone can reproduce** + a **README that tells
the story of your decisions** + **one real machine-learning component** + **you can confidently defend the
whole thing in an interview.**

---

## Questions to answer before you start (these are prompts, not steps)

1. **What's the smallest genuinely useful version you could publish first?** Ship *something* real early,
   then grow it — don't disappear for eight weeks and hope it comes together at the end.
2. **Which sources are trustworthy, and what are you actually allowed to publish from them?**
3. **When two records look like the same school or major spelled differently — how will you decide, and
   how will you *prove* your matching is correct?**
4. **Which of the hard parts do you want to make your signature story, and go deepest on?**
