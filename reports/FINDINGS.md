# Does machine learning beat similarity search for CNS virtual screening?

A retrospective benchmark on three CNS targets, ChEMBL_37.

---

## Summary

**No, not reliably — and the answer depends on which metric you ask about.**

Random forest over ECFP4 fingerprints beat nearest-neighbour Tanimoto similarity on BEDROC
for two of three targets. But similarity search beat random forest on **enrichment at 1% for
all three**, which is the metric that governs what you would actually assay.

On that evidence, NeuroLab ships **similarity search**, not the machine-learning models. The
ML advantage is narrow, metric-dependent, does not replicate across targets, and does not
justify the cost of shipping a trained model, versioning it, and retraining it.

A secondary finding proved more consequential than the primary one: **the similarity baseline
gets substantially stronger as you give it more reference actives.** Benchmarks that
under-resource the baseline will overstate how much ML adds.

---

## The question

The platform previously ranked compounds by a descriptor score built from molecular weight,
LogP, TPSA and hydrogen-bond counts. Direct testing showed it does not work: it ties
haloperidol (an antipsychotic) with aspirin, and ranks benzene and hexane above caffeine.
This is expected — those descriptors measure drug-likeness, which carries no information
about whether a compound binds a *particular* protein.

The question was therefore whether a method exists that does predict target-specific
activity, and whether it can be shown to work rather than assumed to.

## Pre-registration

Criteria were fixed before the first run and not altered afterward:

> A method is validated only if it beats **all three** baselines — random, the existing
> descriptor score, and nearest-neighbour Tanimoto similarity — on BEDROC, with the lower
> bound of its 95% bootstrap interval above the best baseline.

The third baseline is the one that matters. A large share of published QSAR models never beat
plain similarity search, and reporting a win over random alone is the most common way this
class of work misleads.

## Methods

**Data.** ChEMBL_37, pinned and cached. Actives are compounds with median pChEMBL >= 7.0
across repeat measurements; inactives are pChEMBL <= 5.0 or an explicit "Not Active" comment.
The 5.0-7.0 band is discarded because between-laboratory measurement error is comparable to
that window's width, so those labels would be noise. Median rather than max across repeat
measurements, so a compound is represented by its consensus rather than its most flattering
assay.

**Two tracks, reported separately and never pooled.**

- *Track A* uses measured inactives. Most defensible, but publication bias means actives
  vastly outnumber inactives for well-studied targets, so the class ratio is unrealistic. It
  measures **discrimination**, not screening.
- *Track B* pads actives with property-matched decoys to a realistic ~0.5% hit rate. Decoys
  match on molecular weight, cLogP, HBD, HBA, rotatable bonds and formal charge, and are
  required to be topologically dissimilar (ECFP4 Tanimoto < 0.35) so a "decoy" is not an
  unlabelled active. It measures **retrieval from a haystack**, which is what virtual
  screening actually is.

**Splitting.** Bemis-Murcko scaffold split, large scaffold groups packed into train so the
test set consists of rare and singleton scaffolds. ChEMBL actives arrive as congeneric series
from individual publications; a random split places near-identical analogs on both sides and
inflates every metric. A random split is reported alongside purely as a diagnostic — the gap
between the two quantifies the analog bias present.

**Metrics.** Enrichment factor at 1% and 5%, and BEDROC (alpha=20), as primaries. ROC-AUC and
PR-AUC as secondaries. ROC-AUC weights the whole ranked list equally while screening only ever
uses the top slice, so a model can post a respectable AUC while its top 100 is worthless. EF
and BEDROC were implemented directly, since scikit-learn provides neither, and validated
against their closed forms.

**Methods compared.** Random baseline; the existing descriptor score; max ECFP4 Tanimoto to
training actives; random forest (300 trees) on ECFP4; linear SVM on ECFP4.

## Results

Track B, scaffold split — the realistic screening condition. ChEMBL_37, seed 20260718,
95% bootstrap intervals from 300 resamples.

| target | method | BEDROC | 95% CI | EF@1% | ROC-AUC |
|---|---|---|---|---|---|
| **D2** (CHEMBL217) | random | 0.049 | [0.027, 0.072] | 1.1 | 0.479 |
| 179 test actives | descriptor score | 0.426 | [0.043, 0.096] | 40.3 | 0.505 |
| | max Tanimoto | 0.927 | [0.894, 0.956] | **89.0** | 0.988 |
| | random forest | **0.959** | [0.939, 0.976] | 80.6 | 0.989 |
| | linear SVM | 0.936 | [0.910, 0.957] | 79.5 | 0.991 |
| **MAO-B** (CHEMBL2039) | random | 0.043 | [0.019, 0.073] | 0.0 | 0.518 |
| 69 test actives | descriptor score | 0.661 | [0.059, 0.151] | 65.3 | 0.672 |
| | max Tanimoto | **0.874** | [0.797, 0.940] | **84.1** | 0.962 |
| | random forest | 0.899 | [0.837, 0.955] | 82.7 | 0.974 |
| | linear SVM | 0.810 | [0.728, 0.881] | 74.0 | 0.947 |
| **5-HT1A** (CHEMBL214) | random | 0.047 | [0.027, 0.072] | 1.1 | 0.478 |
| 175 test actives | descriptor score | 0.492 | [0.052, 0.107] | 46.8 | 0.547 |
| | max Tanimoto | 0.962 | [0.934, 0.982] | **92.5** | 0.992 |
| | random forest | **0.977** | [0.964, 0.987] | 88.0 | 0.998 |
| | linear SVM | 0.954 | [0.936, 0.975] | 81.1 | 0.996 |

Bold marks the best non-random value in each group. Random forest clears the similarity
baseline outside its confidence interval on D2 and 5-HT1A. On MAO-B the intervals overlap, so
that comparison is unresolved rather than a loss. The linear SVM never clears it on any
target, and loses outright on MAO-B.

The pre-registered criterion required beating all three baselines on **every** target. It was
not met.

**A note on the SVM.** At Track B scale liblinear hit its default 1000-iteration cap without
converging, which produces a fitted-looking model whose scores are unreliable. That was fixed
(primal solver, `max_iter=20000`) and the panel re-run. The corrected numbers differ from the
originals by at most 0.001 — the non-convergence turned out to be numerically immaterial for
ranking. Reported because the warning was real and the check was worth doing, not because it
rescued a result. Random forest values were bit-identical across both runs, confirming the
pipeline is deterministic under a fixed seed.

### Finding 1 — the metrics disagree, and the disagreement matters

Random forest wins on BEDROC for two of three targets. Similarity search wins on EF@1% for
**all three**, by 2-8 percentage points.

These measure different things. BEDROC weights a broad early region of the ranked list; EF@1%
asks only what fraction of the very top is active. For a screening campaign that can afford to
assay the top 1% of a library, EF@1% is the operative number, and there similarity search is
consistently ahead.

The honest reading is that random forest spreads its advantage across the early ranks without
improving the extreme top, which is the part that gets tested.

### Finding 2 — the similarity baseline strengthens with more reference actives

The benchmark was first run with a 20,000-molecule decoy pool, which caps Track B at ~100
actives and leaves only 12-36 in the test set after splitting. Re-running at 100,000 raised
this to 69-179. The baseline moved sharply:

| target | max Tanimoto BEDROC (20k pool) | (100k pool) | change | test actives |
|---|---|---|---|---|
| D2 | 0.740 | 0.927 | **+0.187** | 36 → 179 |
| MAO-B | 0.778 | 0.874 | **+0.096** | 12 → 69 |
| 5-HT1A | 0.829 | 0.962 | **+0.133** | 35 → 175 |

Nearest-neighbour search benefits directly from denser coverage of chemical space: more
reference actives means a closer nearest neighbour for any given query. A benchmark that gives
the baseline few actives is measuring a handicapped baseline, and will overstate how much any
model adds on top of it.

At the 20k pool the earlier run reported "no model beat similarity" on two targets. That
conclusion was not wrong so much as unsupported — 12 test actives cannot resolve a difference
of a few BEDROC points either way.

### Finding 3 — the method is far better at "right neighbourhood" than "which analog binds"

The headline Track B numbers describe an easy discrimination: separating actives from
property-matched compounds drawn at random from ChEMBL. Separating actives from compounds
that were *measured and found inactive* against the same target is a different and much
harder task, because those inactives are typically close analogs from the same SAR campaign.

Measured directly, scaffold split, shipped method:

| task | target | ROC-AUC |
|---|---|---|
| actives vs random library compounds | MAO-B (Track B) | **0.962** |
| actives vs **measured inactives** | MAO-B (Track A) | **0.794** |

On a spot check with 100 D2 reference actives, held-out real actives averaged 0.362
similarity while real measured inactives averaged 0.334 — a gap of under 0.03. Unrelated
drugs and solvents averaged 0.135, an order of magnitude clearer separation.

This is the activity-cliff problem, and it is intrinsic to similarity-based scoring: two
molecules differing by one substituent are near-identical by fingerprint while differing by
orders of magnitude in affinity.

**Practical consequence.** The method is well suited to triaging a large diverse library down
to the right chemical neighbourhood. It is considerably weaker at lead optimisation — picking
the winner among close analogs — and should not be relied on for that.

### Finding 4 — Track A is degenerate for well-studied targets

For D2 and 5-HT1A, ChEMBL holds ~3,400 actives against 350-500 measured inactives. The test
set lands at ~82% actives, where a *random* ranking already scores 0.813-0.817 BEDROC and
EF@1% cannot exceed 1.22. There is almost no dynamic range for a method to demonstrate
anything, and on 5-HT1A three methods tie at a perfect 1.000.

Those splits are reported but marked low-information. MAO-B is the exception (31.6% test
actives) because MAO-B inhibitor papers do publish negative results.

This is publication bias made visible: the better-studied the target, the less usable its
measured-inactive set is for benchmarking.

## The BBB score: tested, and it failed

The developability score was displayed to users as a BBB-oriented read-out and had never been
tested against measured brain penetration. Benchmarked against B3DB (7,807 compounds with
experimental BBB outcomes, same scaffold-split protocol):

| method | ROC-AUC | 95% CI |
|---|---|---|
| random forest on ECFP4 | **0.929** | [0.916, 0.939] |
| TPSA alone | 0.823 | [0.804, 0.842] |
| **hand-tuned descriptor score** | **0.799** | [0.780, 0.820] |
| LogP alone | 0.618 | [0.589, 0.644] |
| random | 0.457 | [0.429, 0.485] |

The hand-tuned score is better than random, so it was not pure noise. But it is **worse than
a single descriptor**. A paired bootstrap on the difference against TPSA gives
[-0.037, -0.009] — entirely below zero, so the gap is real and not sampling noise.

Its molecular weight, LogP, and hydrogen-bond terms were not merely redundant with TPSA; on
this data they were actively harmful. Four extra terms and a hand-chosen weighting produced a
worse predictor than the one descriptor they were built around.

The score was replaced with the random forest, which beats it by 0.13 ROC-AUC with
non-overlapping intervals. Note this sends the opposite way to the activity result above,
where similarity search won and the ML did not ship. The principle is identical in both cases
— the evidence decides — and the difference is the margin: 0.13 with disjoint intervals here
against ~0.03 with a contrary early-enrichment result there.

## The actives are more homogeneous than the benchmark implies

A caveat that qualifies every activity number above, found while sizing the docking
comparison. Test compounds were binned by their maximum ECFP4 Tanimoto to the *training*
actives — that is, by how novel they are relative to what a similarity search gets to see:

| bin | MAO-B compounds | MAO-B actives | D2 compounds | D2 actives |
|---|---|---|---|---|
| novel (<0.3) | 1496 | **14** | 1419 | **3** |
| related (0.3–0.5) | 401 | 39 | 435 | 11 |
| close analog (≥0.5) | 98 | 92 | 146 | 136 |

Almost every active is a close analog of something in the training set, *despite* a
Bemis-Murcko scaffold split having already separated them by scaffold. A different scaffold
is not the same as different chemistry: these are congeneric series with decorated cores, and
the fingerprint still sees the shared chemotype.

Two consequences:

1. **Similarity search's headline numbers describe the easy case.** It is being asked to
   recognise chemistry that resembles chemistry it was shown, which is close to the only case
   this data contains. The 0.874–0.962 BEDROC is real but should not be read as a claim about
   genuinely novel scaffolds.
2. **The interesting comparison is barely measurable.** Testing whether a structure-based
   method helps on unfamiliar chemistry needs unfamiliar actives, and for these targets
   ChEMBL holds almost none — 3 for D2. That is a limit of the available data, not of the
   method being tested, and it is why the docking comparison below runs on MAO-B alone.

This is the same publication-bias pattern seen in Track A, in a different guise: the
literature explores around what already works.

## Docking: validated on 2 of 3 targets

Docking was added only after the ligand-based methods were benchmarked, so it has something
to be measured against. Before scoring any unknown, the setup must reproduce a pose whose
answer is already known: rebuild a co-crystal ligand from SMILES alone, dock it back into its
own structure, and measure the distance to the crystallographic pose. Under 2 Å is the
accepted standard.

| target | PDB | ligand | top affinity | crystal-pose affinity | top RMSD | best RMSD | result |
|---|---|---|---|---|---|---|---|
| MAO-B | 2V5Z | SAG (safinamide) | −10.09 | −9.21 | **1.40 Å** | 0.64 Å | PASS |
| D2 | 6CM4 | 8NU (risperidone) | −11.86 | −11.04 | **0.62 Å** | 0.62 Å | PASS |
| 5-HT1A | 7E2Z | 9SC (aripiprazole) | −8.64 | −7.56 | 6.54 Å | 5.53 Å | **FAIL** |

**The 5-HT1A failure is a scoring failure, not a search failure**, and the distinction is
diagnosable. Scoring the crystal pose in place gives −7.56, and it stays put under local
minimisation (0.60 Å drift). Docking found poses at −8.64. So the search worked fine and the
scoring function genuinely prefers a wrong pose to the experimental one. Quadrupling
exhaustiveness from 16 to 64 changed nothing (best RMSD 5.53 → 5.33 Å), which is what the
diagnosis predicts: more sampling cannot fix a scoring function that ranks the truth second.

This is a well-documented limitation of empirical docking scoring functions, and it is the
reason a docking score should not be trusted on a novel target without first checking that
target can be redocked.

### Two setup errors worth recording

Both produced confident numbers about the wrong molecule, and both came from hand-writing
what could be looked up:

- The 5-HT1A entry originally pointed at **chain A, which is the G protein**, not the
  receptor (chain R) — the same trap as PDB 7CMU, whose first entity is a G protein.
- The largest HET group in that structure is **PIP₂, a membrane lipid**, which a naive
  "biggest ligand wins" rule selects as though it were a drug.
- A hand-written risperidone SMILES caused D2 to fail at 10.34 Å. Fetching the authoritative
  SMILES from RCSB's chemical dictionary moved it to **0.62 Å**.

The harness now discovers the ligand from the structure and takes bond orders from RCSB
rather than accepting them by hand.

## Docking versus similarity: docking loses, including where it should have won

With the setup validated by redocking, the question is whether docking earns its cost against
the method already shipped. Both ranked the identical 1,995 compounds for MAO-B — 145
held-out actives and 1,850 property-matched decoys. Docking took **236 minutes**; similarity
took milliseconds.

| method | BEDROC | 95% CI | EF@1% | EF@5% | ROC-AUC |
|---|---|---|---|---|---|
| similarity | **0.887** | [0.843, 0.924] | 13.8 | 12.9 | 0.953 |
| docking | 0.273 | [0.207, 0.340] | 3.4 | 2.6 | 0.773 |

The intervals do not overlap. Docking loses decisively.

(EF@1% for similarity is at its ceiling: at a 7.3% active ratio the maximum possible is 13.8,
so essentially the entire top 1% is active. EF cannot discriminate further here, which is why
BEDROC carries the comparison.)

### The hypothesis was refuted

This run existed to test a specific prediction: similarity search cannot see past resemblance,
so docking — which scores a pose against a protein and is indifferent to whether a ligand
resembles anything known — should have an advantage on unfamiliar chemistry. That prediction
was stated before the run.

| novelty bin | n | actives | similarity | docking |
|---|---|---|---|---|
| dissimilar (<0.5) | 1897 | 53 | **0.549** | 0.209 |
| close analog (≥0.5) | 98 | 92 | **0.997** | 0.963 |

It is wrong. Docking loses in *both* bins, including the one where it was supposed to win.

The half of the hypothesis about similarity is confirmed — it degrades sharply on unfamiliar
compounds, 0.997 → 0.549. That weakness is real. But docking does not fill the gap; it
degrades further still, 0.963 → 0.209. Whatever is hard about those compounds is hard for
both methods, and structure-based scoring does not rescue it.

### What this does and does not license

**Does:** docking is not shipped. On the evidence it costs roughly six orders of magnitude
more compute per compound and ranks worse, on the only target eligible to be tested.

**Does not:** this is one docking configuration — smina's default scoring function, rigid
receptor, exhaustiveness 8, single structure, no rescoring. It is not a verdict on docking as
a technique. Ensemble docking, induced-fit protocols, and ML-based rescoring functions all
exist and are not tested here. The honest claim is that *this* setup does not beat similarity
search for *this* target under *these* conditions.

Also one target, and 53 actives in the bin that mattered. Above the power threshold, but not
by much.

## What shipped, and why

**Similarity search**, exposed at `POST /screen`.

It beat random and the descriptor score outside the confidence interval on every split of
every target, it wins the operative metric (EF@1%) on all three targets, and it requires no
training step, no model artifact, no versioning, and no retraining as ChEMBL grows. Its score
is also directly inspectable — every prediction reports which known active it matched.

Random forest was **not** shipped. Its BEDROC edge is real on two targets but does not
replicate on the third, does not appear in early enrichment at all, and would carry
substantially more operational cost.

The linear SVM initially failed to converge at Track B scale (liblinear hitting its default
1000-iteration cap), which silently produced a fitted-looking model whose scores were
meaningless. Fixed by raising max_iter and selecting the primal solver.

## Limitations

Stated plainly, because the result is easy to oversell:

- **Retrospective, not prospective.** Benchmark performance systematically overestimates what
  happens on genuinely novel chemistry.
- **Weak within a congeneric series.** See Finding 3: ROC-AUC drops from 0.962 against random
  library compounds to 0.794 against measured inactives. Use it to find the neighbourhood,
  not to pick the winner inside one.
- **Only works where actives already exist.** The method is nearest-neighbour to known
  binders; it has nothing to say about a target with no ChEMBL data, and its quality degrades
  as the reference set thins.
- **Decoys are presumed inactive, not measured inactive.** A decoy that in truth binds is a
  false negative invisible to this evaluation.
- **Three targets, all CNS, all aminergic GPCRs or a monoamine oxidase.** Generalisation to
  other target classes is untested.
- **Nothing here addresses selectivity, toxicity, ADMET, or synthesizability.** The output is
  a prioritisation signal, not a drug candidate.
- **BBB prediction is a class, not a concentration.** The model predicts BBB+/BBB− and says
  nothing about brain concentration, efflux liability, metabolism, or free fraction in tissue.
  Its training labels are curated from literature with varying assay conditions.
- **No experimental validation.** Nothing in this report is wet-lab evidence.

## Reproducing

```bash
cd backend
uv sync --group dev
uv run python -m backend.science.cli --panel --decoy-pool 100000

# Verify reproducibility: identical numbers, no network
NEUROLAB_OFFLINE=1 uv run python -m backend.science.cli --panel --decoy-pool 100000
```

Every dataset and report is stamped with the ChEMBL release and the random seed. Raw API
responses are cached to `backend/data/cache/`, so an offline re-run reproduces byte-identical
metrics — verified, not asserted.
