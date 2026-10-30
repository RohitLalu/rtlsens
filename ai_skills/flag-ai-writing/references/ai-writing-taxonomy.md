# A taxonomy of AI writing, and how human academic writing differs

This file does two things. First, it enumerates the kinds of AI writing — the
layers at which language-model prose betrays itself. Second, it states what
genuine human academic writing does instead, as positive properties rather than
mere absence of tells. The detector classifies findings against the eight
categories in Part 1; the likelihood judgment leans on Part 2, because the deepest
tells are failures of the human properties, not the presence of any one word.

A standing caution runs under all of it: none of these features *proves* machine
authorship. Each is a probability shift. Non-native English, rigid schooling,
institutional house style, and heavy copy-editing all produce overlapping
surface patterns. Diagnose; never convict.

---

## Part 1 — The eight categories of tell

### 1. Lexical (word choice)

The most superficial layer, and the easiest to fake, so weight it lightly.

- **Inflated / favored vocabulary.** Models reach for a recognizable register of
  impressive-sounding words far more often than human writers: *delve, intricate,
  pivotal, crucial, realm, landscape, tapestry, nuanced, multifaceted, holistic,
  paradigm, underscore, underpin, robust, leverage, harness, testament, seamless,
  meticulous, comprehensive, foster, garner, showcase, navigate* (used as a
  metaphor), *boast, pivotal, intricate, vibrant.*
- **Transition-word overload.** Sentences and paragraphs opened again and again
  with *Moreover, Furthermore, Additionally, Notably, Importantly, Consequently,
  In addition.* Humans use these too, but not as a metronome.
- **Promotional register.** Relentless positivity, no friction, everything
  "powerful" and "exciting"; the tonal default of marketing copy leaking into
  scholarship.
- **Collocational sameness.** The same two or three words always travel together
  ("rich tapestry", "rapidly evolving landscape", "plays a vital role").

### 2. Syntactic (sentence level)

- **Uniform length and shape.** Most sentences land in a narrow band (roughly
  15–25 words) with the same subject–verb–object contour. Human prose varies far
  more: a three-word sentence beside a forty-word one.
- **The "not only… but also" / "it's not just X, it's Y" reframe.** A signature
  construction, especially as a rhetorical flourish.
- **Participial pile-ups.** Chains of "-ing" and "-ed" opening phrases
  ("Leveraging recent advances, building on prior work, we…").
- **Balanced, closed cadence.** Sentences that resolve too neatly, every clause
  mirrored, no loose or trailing structure.

### 3. Structural (document and paragraph level) — high weight

- **The tricolon reflex.** Everything arrives in threes: three adjectives, three
  parallel clauses, three-item lists, in sentence after sentence. An occasional
  triad is natural; constant triads are a signature.
- **Template paragraphs.** The same shape every time — topic sentence, three
  parallel supporting sentences, a wrap-up sentence — regardless of what the
  content needs. Subsections come out suspiciously equal in length.
- **Restate-the-prompt opening.** The first paragraph paraphrases the question or
  task back before saying anything.
- **Empty summary closing.** "In conclusion / In summary / Overall," followed by a
  recap that adds no new information and often a vague uplift.
- **Format bleed.** Prose that should flow is chopped into bullet lists; stray bold
  **keyword:** labels and markdown headers appear inside running text — artifacts
  of a model drafting in markdown.

### 4. Rhetorical / argumentative — high weight

- **False balance.** "While some researchers argue X, others contend Y" — both
  sides presented, no position taken, no resolution. A paper exists to take a side.
- **Empty significance.** Importance asserted instead of shown: "plays a crucial
  role", "has the potential to revolutionize", "represents a significant advance",
  "is of paramount importance."
- **Reflexive throat-clearing.** "It is important to note that", "It is worth
  noting", "It should be emphasized that", "Needless to say" — filler that
  announces significance without supplying any.
- **Uniform hedging.** The same cautious temperature everywhere, strong claims and
  weak ones hedged identically, rather than committing where the evidence is strong
  and hedging precisely where it is weak.

### 5. Epistemic / content — highest weight

This is where machine writing most deeply differs, and where it is hardest to fake.

- **Summary in place of argument.** The text synthesizes what is known and takes no
  original, contestable position of its own.
- **Even, encyclopedic coverage.** Attention spread evenly across all subtopics.
  Human writers spend words in proportion to difficulty and importance; a surprising
  result earns a paragraph, a routine control earns a clause.
- **Generic examples.** Illustrations that could appear in any paper on the topic,
  not ones situated in the specific sub-literature or dataset at hand.
- **No mess.** No failed replication, no confound that actually bites, no limitation
  that costs anything — reality is always messier than model prose admits.
- **Generic "so what."** The stakes are "advances our understanding" or "has broad
  implications," never tied to one named open problem a specific community cares
  about.

### 6. Citation & evidence — high weight

- **Uncited load-bearing claims** where the field would demand a reference.
- **Vague attribution.** "Studies have shown", "research suggests", "it is widely
  accepted", "experts agree" — authority invoked without a name or year.
- **Unverifiable or malformed citations.** Plausible-looking references that do not
  resolve, mismatched author/year/title, invented DOIs — a hazard specific to
  model-generated bibliographies.
- **"Little research has been done in this area."** Almost always false, and a tell:
  real positioning names the specific prior work and the specific gap.

### 7. Formatting & mechanics

- Emoji in scholarly prose.
- Markdown headers or bold runs inside continuous text.
- Curly-vs-straight quote and apostrophe inconsistency, mixed within one document.
- A conspicuously even em-dash cadence (the model's house punctuation).
- Title-case headings in a venue that uses sentence case, or vice versa.

### 8. Stylometric signatures — corroborating only

Soft statistical signals. Never a standalone finding; use them to raise or lower
confidence in patterns already found.

- **Low burstiness.** Little variation in sentence length and complexity across the
  passage. Human writing is bursty — it clusters and breaks.
- **Low lexical diversity** with a small set of repeated favored phrases.
- **Near-constant paragraph length.**
- **An unnaturally clean surface.** No typos, no self-interruption, no idiosyncratic
  aside, no abandoned sub-thought — a flatness that is itself suspicious in a long
  draft.

---

## Part 2 — How human academic writing is fundamentally different

The surface tells above are downstream of a deeper difference in *purpose*. These
are the positive properties of genuine research writing. Their absence, not the
presence of any single word, is the real signal. (These mirror the seven
properties the `academic-writing` skill writes *toward*; here they are read as
diagnostic.)

1. **A contestable claim with stakes.** A real passage is trying to make the reader
   believe one specific thing a competent peer could dispute and that was not
   already obvious. "X is an important area" is exposition; "standard method M
   fails on inputs with property P, and here is the mechanism" is a claim. AI prose
   covers; human prose argues.

2. **Positioning in a live conversation.** Human work situates itself against named,
   specific prior work and identifies a specific gap ("Smith et al. assumed bounded
   noise; that breaks under the conditions in §3"). AI prose gestures at "the
   literature" and "recent advances" without pinning anything down.

3. **Load-bearing evidence, subordinate prose.** In human writing the sentences
   exist to carry particular numbers, conditions, and comparisons; the foregrounded
   figure is the one that matters ("accuracy fell from 94% to 61% past length 512").
   AI prose gestures ("performance degrades significantly in certain settings")
   because it often has no specific figure to carry.

4. **Asymmetric emphasis.** Humans spend words in proportion to importance and
   difficulty, so emphasis is uneven and informative. Even coverage is itself the
   tell of a writer with no particular stake.

5. **Earned, local hedging.** Humans commit firmly where evidence is strong and
   hedge precisely where it is weak, naming the specific threat ("this may reflect
   selection effects, though our design cannot rule out X"). AI hedging is uniform
   and contentless ("results may vary").

6. **Disciplinary voice.** Real writers have internalized one field's conventions —
   citation density, how aggressively to frame a contribution, which turns of phrase
   are standard, how much background to assume. AI prose defaults to a generic
   "academic" register belonging to no field. (Note the inverse risk: correct
   disciplinary voice can look templated to an outsider. Do not flag genuine
   convention.)

7. **Negative space.** Human writers assume shared background with their reader and
   skip it. Re-explaining what the audience already knows, or defining standard
   terms, marks the writer as an outsider or a model padding for completeness.

8. **Idiosyncrasy and traceable process.** Human drafts carry fingerprints: a
   favorite irregular construction, a dry aside, a sentence that trails off, an
   honest "we initially tried Y and it failed because…", the occasional typo or
   inconsistency. Model prose is smoother and more anonymous than a real draft,
   and its specificity, when present, is often unverifiable rather than lived.

---

## A worked contrast

**AI-default (weak):**
> Machine learning has emerged as a crucial tool in medical diagnostics. In this
> paper, we delve into a novel approach that leverages deep learning to address
> various challenges. Our comprehensive framework demonstrates significant
> improvements and has the potential to revolutionize patient care. It is important
> to note that further research is needed.

Flaggable: lexical (*crucial, delve, leverages, comprehensive*); rhetorical (empty
significance "revolutionize", throat-clearing "it is important to note"); epistemic
(covers, no number, no named gap); citation (none). Every sentence covers the topic
and commits to nothing.

**Researcher (strong):**
> Convolutional models now match radiologists on curated benchmarks, but their
> accuracy on our data fell from 91% to 68% once we included scans from scanners
> absent at training time. We trace this to a domain shift that existing
> augmentation schemes (Zhou et al., 2021) do not cover, and show that a simple
> scanner-stratified calibration recovers most of the lost accuracy (to 86%).

A contestable claim, real numbers carried by the prose, a named gap and the prior
work it exceeds, and hedging only where earned.
