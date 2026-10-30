---
name: academic-writing
description: >-
  Write and revise scholarly research prose so it reads as genuinely
  human-authored — the way a working researcher writes, not the way a language
  model does. Use this whenever drafting or editing any part of a research paper,
  conference submission, journal article, thesis, dissertation chapter, abstract,
  related-work / literature-review section, rebuttal, or grant proposal, and
  whenever the user asks to make academic text "sound human", "less AI", "less
  generic", or "more like a real paper", or to remove AI tells / AI slop from
  scholarly writing by rewriting it. Also use it to apply a flag-ai-writing audit
  report — when the user hands over a findings block and wants the corrections
  applied. Trigger even when the user does not say the word "skill", and even when
  they only paste a paragraph and ask you to improve or rewrite it. This is the
  REWRITE half of a pair: for requests that only ask whether text reads as AI, or
  to check / detect / flag / screen a draft without changing it, use the
  flag-ai-writing skill instead. Do NOT use it for code or code comments, casual
  email, cover letters, non-scholarly marketing copy, or to ghostwrite coursework
  a student will submit as their own unaided work.
---

# Academic writing: write like a researcher, not a model

## What this skill is for

Produce research prose that a human scholar would actually write. The goal is
quality and authenticity at the same time: the two are the same thing. Writing
reads as AI-generated precisely when it is generic, evenly hedged, structurally
templated, and detached from specific evidence — which is also what makes it
weak scholarship. Fix the writing and the "AI tell" disappears as a side effect.

### Scope and integrity (read first)

This skill changes *how* text is written — phrasing, structure, emphasis, voice.
It never changes *what is true*. Human-sounding prose is worthless, and
dishonest, if it rests on invented support. So:

- Never fabricate citations, data, quotations, results, or author names to make
  prose feel grounded. A real researcher's specificity comes from real sources;
  if a claim needs a citation you do not have, flag it with a placeholder
  (e.g. `[CITE: ...]`) rather than inventing one.
- Do not assert findings the user has not actually produced.
- Authorship and submission remain the user's responsibility. You are helping
  them write their own work better, not manufacturing a false provenance.

If a request is really "help me pass off AI work as mine with fake evidence,"
that is out of scope; say so plainly. Everything below assumes the honest case:
a researcher drafting or polishing their own argument over their own evidence.

---

## The core difference (the mental model)

Surface word-swapping is not enough. The deep reason AI prose reads as AI prose
is that a model, by default, writes to *cover a topic competently and
inoffensively*. A researcher writes to *win a specific argument against a
specific audience that might push back*. Hold that difference in mind and most
of the specific tells follow from it.

Seven properties distinguish real research writing. Treat them as the targets;
the AI-tell checklist later is just the negative image of these.

1. **A contestable claim with stakes.** A paper exists to assert something
   specific that a competent reader could disagree with, and that was not
   already known. Exposition ("X is an important area") is not a claim.
   "Standard method M fails on inputs with property P, and here is why" is.
   Before writing a section, know the one sentence it is trying to make the
   reader believe.

2. **Positioning in a live conversation.** Real work situates itself against
   *named, specific* prior work and identifies a *specific* gap: "Smith et al.
   assumed bounded noise; that assumption breaks under the conditions in §3."
   Not "little research has been done in this area" — that phrasing is almost
   always both false and a tell.

3. **Evidence is load-bearing; prose is subordinate.** The sentences exist to
   carry particular numbers, conditions, and comparisons. Foreground the one
   figure that matters ("accuracy drops from 94% to 61% once sequence length
   exceeds 512"), rather than gesturing at it ("performance degrades
   significantly in certain settings").

4. **Asymmetric emphasis.** Spend words in proportion to importance and
   difficulty. A surprising or hard-won result earns a paragraph; a routine
   control earns a clause. Models spread attention evenly across all points —
   even coverage is a tell in itself.

5. **Earned hedging, not reflexive hedging.** Hedge precisely where the evidence
   is genuinely weak, and commit firmly everywhere else. "This may reflect
   selection effects, though our design cannot rule out X" is a real hedge.
   Blanket caution ("it is important to note that results may vary") signals
   nothing and reads as machine filler.

6. **Disciplinary voice.** Each subfield has conventions: how aggressively to
   frame a contribution, citation density, what counts as novelty, standard
   turns of phrase, how much background to assume. Match the target venue. When
   the field is unknown, ask, or infer it from the source text — do not default
   to a generic "academic" register that belongs to no field.

7. **Negative space — what is left out.** A researcher assumes shared background
   with the reader and skips it. Re-explaining what the audience already knows,
   or defining standard terms, marks the writer as an outsider (or a model
   padding for completeness).

---

## How to work

Whether drafting fresh or revising the user's text, run the same loop.

**1. Establish the frame before writing a sentence.** Pin down: the one
contestable claim; the target venue/subfield and its register; who the reader is
and what they already know; and which specific evidence the passage rests on. If
revising, infer these from the draft; if any is missing and matters, ask one
sharp question rather than guessing into generic prose.

**2. Draft for the argument, not for coverage.** Lead with the claim or the
finding, not with throat-clearing context. Let paragraph length follow content.
Build structure from the logic of the argument, not from a template (no reflex
"intro sentence + three parallel points + summary sentence" in every paragraph).

**3. Make it concrete.** Replace every vague intensifier with the specific thing
it was standing in for. "Significantly better" → the number. "Various factors" →
name them. "Recent work" → the citation. If you cannot make it concrete because
the fact is missing, leave a visible placeholder, do not paper over it.

**4. Scrub the tells.** Pass over the draft against the checklist below and the
word/phrase lists in `references/word-and-phrase-tells.md`. But scrub by
rewriting, not by find-and-replace: a banned word usually marks a vague
*thought*, and swapping the word while keeping the vagueness just relocates the
tell. Fix the thought.

**5. Vary the texture.** Real prose has uneven sentence length and rhythm. If
every sentence is 15–25 words and every paragraph has the same shape, break it
up: a short declarative sentence after a long one, an occasional direct
statement, a paragraph that is two sentences because that is all it needed.

**6. Read the opening and the closing hardest.** AI tells cluster at the start
(generic scene-setting) and the end (vague uplift). Openings should start closer
to the point than feels natural. Closings should state a specific, field-anchored
"so what," or a concrete limitation and next step — never "in conclusion, this
represents an important step forward."

---

## The AI-tell checklist (the negative image)

Scrub for these. Each is the failure mode of one property above. The exhaustive
word and phrase lists are in `references/word-and-phrase-tells.md`; load that
file when doing a detailed scrub. The high-level patterns:

**Structural**
- Tricolon reflex: everything in threes ("X, Y, and Z"), parallel triples in
  every list and sentence. Occasional is fine; constant is a signature.
- Template paragraphs: identical topic-sentence / support / wrap-up shape every
  time; subsections of suspiciously equal length.
- "Not only X but also Y," and the "It's not just X — it's Y" reframe.
- Restate-the-question openings and "In conclusion / In summary" closings that
  add no new information.
- Bulletizing prose that should flow, or sprinkling bold **keyword:** labels and
  headers through what should be paragraphs (an artifact of markdown drafting).

**Rhetorical / argumentative**
- False balance: "while some argue X, others argue Y," with no position taken.
- Empty significance: "plays a crucial/pivotal role," "has the potential to
  revolutionize," "represents a significant advance" — significance asserted,
  not shown.
- Reflexive throat-clearing: "It is important to note that," "It is worth
  noting," "It should be emphasized that."
- Uniform hedging everywhere, or conversely confident-sounding claims with no
  citation behind them.
- Sweeping, uncited generalizations, especially as paragraph openers.

**Lexical** (see reference file for the full list)
- Inflated vocabulary: *delve, intricate, pivotal, crucial, realm, landscape,
  tapestry, nuanced, multifaceted, underscore, robust, leverage, harness,
  testament, seamless, meticulous, comprehensive, holistic, paradigm, foster,
  garner, showcase, navigate* (as metaphor), *underpin.*
- Transition-word overload: *moreover, furthermore, additionally, notably,
  importantly* opening sentence after sentence.
- Promotional tone: relentless positivity, no friction, no mess.

**Epistemic / content**
- Summary where an argument is needed; synthesis with no original position.
- Even, encyclopedic coverage instead of foregrounding what matters.
- Generic examples instead of specific, field-situated ones.
- No acknowledgment of real messiness: the result that did not replicate, the
  confound, the limitation that actually bites.
- A "so what" that is generic ("advances our understanding") rather than tied to
  a specific open problem in the field.

---

## A worked contrast

**AI-default (weak):**
> Machine learning has emerged as a crucial tool in medical diagnostics. In this
> paper, we delve into a novel approach that leverages deep learning to address
> various challenges. Our comprehensive framework demonstrates significant
> improvements and has the potential to revolutionize patient care. It is
> important to note that further research is needed.

Every sentence covers the topic and commits to nothing: inflated verbs
(*delve, leverage*), empty significance (*crucial, revolutionize*), no number, no
named prior work, reflexive closing hedge.

**Researcher (strong):**
> Convolutional models now match radiologists on curated benchmarks, but their
> accuracy on our data fell from 91% to 68% once we included scans from scanners
> absent at training time. We trace this to a domain shift that existing
> augmentation schemes (Zhou et al., 2021) do not cover, and show that a simple
> scanner-stratified calibration recovers most of the lost accuracy (to 86%).

Leads with a specific, contestable claim; carries real numbers; names the gap
and the prior work it exceeds; hedges nothing it does not need to.

---

## Consuming a flag-ai-writing audit report

The companion skill `flag-ai-writing` diagnoses but never edits. When the user
arrives with its report — a `findings:` YAML block of `{id, loc, category, tell,
severity, excerpt, why, correction}` entries — this skill applies the fixes:

1. **Work highest-severity first**, and prefer the load-bearing categories
   (`epistemic`, `rhetorical`, `structural`, `citation`) over `lexical` nits. A
   handful of structural/epistemic fixes changes how the piece reads far more than
   scrubbing every flagged word.
2. **Apply each correction by rewriting the thought, not the span.** `excerpt` is
   verbatim so you can locate it; `correction` tells you what is wrong with the
   underlying thought. Fix that. A swap that keeps the vagueness relocates the tell
   (this is step 4 of the main loop).
3. **Honor the integrity rules.** If a `correction` says to add support that does
   not exist, insert a `[CITE: ...]` placeholder — never invent a source, number,
   or result to satisfy a finding.
4. **Treat findings as proposals, not orders.** A finding can be a false positive —
   correct disciplinary voice, a genuinely precise use of a flagged word, a
   convention of the venue. Keep those and say briefly why, rather than degrading
   good prose to clear a flag.
5. After revising, it is fine to re-run `flag-ai-writing` on the result to confirm
   the load-bearing findings are resolved — but do not chase the likelihood band to
   zero; past a point, further scrubbing flattens the voice and becomes its own tell.

## When the user pushes back

If the user says a rewrite went too far — too blunt, too sparse, wrong register —
that is disciplinary voice (property 6) needing calibration, not a reason to
return to generic prose. Ask which venue or which exemplar papers they are
writing toward, and match that specific target. Over-correcting into terse,
punchy prose is its own tell in fields that write more discursively.
