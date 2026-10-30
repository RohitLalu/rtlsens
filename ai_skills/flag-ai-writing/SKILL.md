---
name: flag-ai-writing
description: >-
  Audit a piece of writing for signs that it was produced by a language model,
  and report the specific spans that read as AI-generated together with a
  suggested correction for each. Use this whenever the user wants to CHECK,
  DETECT, FLAG, SCREEN, or AUDIT text rather than rewrite it: "is this AI?",
  "does this read as AI?", "check this draft for AI tells / AI slop", "flag the
  AI-sounding parts", "how AI does my abstract sound before I submit?", or a
  reviewer/editor/instructor screening a submission. Built for academic and
  scholarly prose (papers, theses, abstracts, related-work sections, rebuttals,
  grant text) but usable on any prose. It only DIAGNOSES and produces a report;
  it does not rewrite. The companion skill `academic-writing` consumes the
  report's corrections and applies the rewrites. Trigger even when the user does
  not say the word "skill". Do NOT use it on code or code comments.
---

# Flag AI writing: diagnose, don't rewrite

This skill reads a passage and reports which parts read as language-model output,
why, and what to do about each one. It is the **detector** half of a pair. The
**reviser** half is the `academic-writing` skill, which takes this skill's report
and applies the fixes. Keep the two jobs separate: here you only diagnose and
record corrections; you do not edit the user's text.

## Read this first — detection is probabilistic, and false positives harm people

Stylometric AI detection is unreliable. The same features that mark machine prose
(even rhythm, low lexical variety, templated structure, cautious hedging) also
appear in careful non-native English writers, in heavily edited institutional
prose, and in students taught a rigid five-paragraph template. There is no feature
or tool that proves text was AI-generated.

So, always:

- Report **evidence and a calibrated likelihood**, never a verdict of "this is AI."
- Never recommend or support an academic-integrity accusation on the strength of
  this report alone. Say so explicitly if the user's goal is to accuse someone.
- Treat the output as "spans a human editor should look at," not "proof of
  authorship."

Load `references/ai-writing-taxonomy.md` for the full taxonomy of tells and the
contrasting properties of genuine human academic writing; load
`references/word-and-phrase-tells.md` (shared with the `academic-writing` skill,
at `../academic-writing/references/word-and-phrase-tells.md`) for the exhaustive
word and phrase lists.

## The mental model (why the tells exist)

A model, left to itself, writes to **cover a topic competently and inoffensively**.
A researcher writes to **win one specific, contestable argument against a reader
who might push back**. Almost every tell below is a symptom of the first posture.
When you are unsure whether something is a tell, ask: *is this sentence trying to
make the reader believe one specific, falsifiable thing, or is it just covering
the topic?* Even coverage, even hedging, and even emphasis are themselves tells.

## The eight categories of tell

Diagnose against these eight layers. Details and examples are in the taxonomy
reference; this is the index you classify findings under.

1. **lexical** — inflated vocabulary (*delve, intricate, pivotal, crucial, realm,
   landscape, tapestry, leverage, harness, robust, nuanced, multifaceted,
   underscore, showcase, testament, seamless, foster, garner*); transition-word
   overload (*moreover, furthermore, additionally, notably, importantly* opening
   sentence after sentence); relentlessly promotional, frictionless tone.
2. **syntactic** — uniform sentence length and shape; "Not only X but also Y";
   "It's not just X, it's Y"; participial-phrase pile-ups; subject–verb–object
   monotony with no short declaratives to break rhythm.
3. **structural** — the tricolon reflex (everything in threes); template
   paragraphs (topic sentence / three parallel supports / wrap-up) repeated
   identically; subsections of suspiciously equal length; restate-the-prompt
   openings; "In conclusion / In summary" closings that add nothing; bulletizing
   prose that should flow; stray bold **keyword:** labels from markdown drafting.
4. **rhetorical** — false balance ("while some argue X, others argue Y") with no
   position taken; empty significance ("plays a crucial role", "has the potential
   to revolutionize"); reflexive throat-clearing ("It is important to note that");
   uniform hedging regardless of how strong the evidence is.
5. **epistemic** — summary where an argument is needed; even encyclopedic coverage
   instead of foregrounding what matters; generic rather than field-situated
   examples; no acknowledgment of real mess (the result that did not replicate,
   the confound, the limitation that actually bites); a generic "so what"
   ("advances our understanding") not tied to a specific open problem.
6. **citation** — claims with no citation where the field demands one; vague
   attribution ("studies have shown", "recent work", "experts agree") instead of
   named work; citations that are plausible but unverifiable or malformed;
   "little research has been done in this area" (usually both false and a tell).
7. **formatting** — emoji in scholarly prose; markdown headers or bold runs inside
   what should be continuous text; curly-quote/straight-quote inconsistency; a
   suspiciously even em-dash cadence; title-case headings where the venue uses
   sentence case.
8. **stylometric** — low burstiness (little variation in sentence length and
   complexity); low lexical diversity with repeated favored phrases; near-constant
   paragraph length; an unusually flat, confident, error-free surface with no
   typos, no asides, no idiosyncrasy. Report these only as soft, corroborating
   signals, never as a standalone finding.

## How to work

1. **Read the whole passage once** before flagging anything, to judge the overall
   argument and register. A single word is rarely a tell in isolation; the
   *pattern* is.
2. **Establish the honest baseline.** Note the field/venue if knowable and the
   intended register. A convention of the field (dense hedging in experimental
   psychology, heavy nominalization in law) is not a tell. Do not penalize correct
   disciplinary voice.
3. **Walk the text and record findings**, one per distinct span, classified under
   one of the eight categories. For each, capture a short verbatim excerpt, why it
   reads as AI, a severity, and a concrete correction.
4. **Weigh, don't tally.** Three high-severity structural/epistemic findings matter
   more than twenty lexical nits. A passage can be full of the word "robust" and
   still be genuine human writing; a passage with none of the banned words can still
   be obviously templated. Base the likelihood on load-bearing patterns
   (categories 3–6), using 1, 2, 7, 8 as corroboration.
5. **Produce the report** in the exact format below.

## Output: the audit report (the handoff contract)

Emit two things, in this order.

First, a short human-readable summary: an overall **likelihood band** — one of
`low` / `mixed` / `elevated` / `high` — one sentence naming the two or three
load-bearing patterns that drove it, and the single most important caveat for this
text. Never state a certainty.

Second, a machine-readable findings block that the `academic-writing` skill (or
any other reviser) consumes. Use exactly this shape — a fenced `yaml` block whose
top-level key is `findings`, each finding carrying the fields shown:

```yaml
findings:
  - id: F1                      # stable within this report
    loc: "§2 ¶1, sentence 2"    # section / paragraph / line / page — enough to find it
    category: rhetorical        # one of the eight category slugs
    tell: empty-significance    # short kebab-case name of the specific pattern
    severity: high              # high | medium | low
    excerpt: "...has the potential to revolutionize patient care."
    why: "Significance asserted, not shown; no mechanism, no number, no named gap."
    correction: "State the specific improvement and over what baseline, or cut the claim."
```

Rules for the block:

- `excerpt` is **verbatim** and short (a clause or sentence), so the reviser can
  locate it exactly. Do not paraphrase it.
- `correction` describes *what to change and why*, not a finished rewrite — the
  reviser owns the rewrite. Point at the underlying vague thought, because a
  reviser that only swaps the banned word while keeping the vagueness just relocates
  the tell.
- Order findings by severity, highest first.
- If nothing is flaggable, emit `findings: []` and say plainly that the text reads
  as human-authored, with the same probabilistic caveat.
- Never invent a citation, result, or fact inside a `correction`. If a claim needs
  support that is not present, the correction is to mark a `[CITE: ...]` placeholder,
  not to supply a source.

## Scoring: the AI-tell coverage percentage

Report one headline percentage, so the user can track a draft across revisions and
compare sections. Compute it from the findings — never guess a number, and never
report a figure a commercial detector would.

**What the number means (say this every time).** The score is *AI-tell coverage*:
the severity-weighted share of the passage's prose that sits inside a flagged span.
It is **not** the probability the text was machine-generated, and **not** comparable
to a detector tool's "% AI" readout. It measures how much of the prose carries
tells — a thing the user can act on — nothing more. A low score means few tells, not
proof of a human author; a high score means dense tells, not proof of a machine.

**Procedure (reproducible):**

1. Unit = sentence. Count `N` = total prose sentences audited. Exclude titles,
   author blocks, tables, figure captions, equations, code listings, and the
   bibliography.
2. For each flagged sentence, take the severity weight of the finding touching it:
   high `1.0`, medium `0.6`, low `0.3`. A sentence touched by several findings takes
   its single **highest** weight — never sum weights on one sentence.
3. `coverage` = sum of those weights over all flagged sentences.
4. `score% = 100 × coverage / N`, rounded to the nearest 5%.
5. Report `N` and the raw flagged-sentence count too, so the number is auditable.

**Band mapping** (report both — the band is the honest headline, the % is the detail):

- `0–10%` → low
- `11–30%` → mixed
- `31–60%` → elevated
- `61–100%` → high

**Rules:**

- Round to the nearest 5%. Never report a decimal; the method does not support that
  precision.
- If `N` is estimated rather than counted exactly, say so and give the score as a
  ±5 range.
- Document-level signals not tied to specific sentences (uniform paragraph shape,
  stylometric flatness, category 8) do **not** enter the coverage count. Note them
  separately in prose as a confidence adjustment up or down; do not inflate the
  percentage with them.
- Prefer a per-section breakdown when the passage is long — where the tells cluster
  is usually more useful than the single number (tells cluster at openings and
  closings).

Emit the score as a `score:` block immediately **before** `findings:` in the report:

```yaml
score:
  ai_tell_coverage_pct: 5        # rounded to the nearest 5
  band: low                      # low | mixed | elevated | high
  sentences_total: 230           # N; append "approx" if estimated
  sentences_flagged: 9
  note: "Coverage of AI tells, not a probability of machine authorship."
```

## Handoff to the reviser

After the report, offer the handoff in one line: the user can run the
`academic-writing` skill, which reads this `findings` block and applies the
corrections by rewriting the underlying thought (not by find-and-replace). This
skill never edits the text itself — that boundary is what keeps diagnosis honest
and lets the user accept or reject each correction.
