# Working in this repository

## What this is

One street-level photograph in, a conformity verdict out: does this sidewalk
meet the clear width the law requires, or is the answer too uncertain to give.

The measurement is not the product. The **verdict under uncertainty** is. The
state of the art reports a mean absolute error and no verdict error rate and
no way to decline; on the only dataset with field-measured truth, a third of
real sidewalks sit within half a metre of Taiwan's 1.5 m threshold, which is
inside that error. A system that answers all of those is wrong on some of
them and cannot say which.

## The interpreter

`/opt/anaconda3/bin/python3` — cv2 5.0.0, numpy 2.4.4, scipy. `python3` in a
login shell is the system one and has none of them. `scikit-learn` is
installed and **cannot be imported** against this numpy; write the linear
algebra out.

## The thresholds, and where they come from

《市區道路及附屬工程設計標準》第 16 條 and the design specification
(`市區道路及附屬工程設計規範`):

| | clear width |
|---|---|
| general | >= **1.5 m**, 2.5 m preferred |
| roads 12 m wide or less | >= **1.2 m** |
| constrained, with the authority's consent | >= **0.9 m** |
| painted sidewalk (標線型人行道) | >= 1.5 m, and only on service roads |

Which one applies depends on the road class, which is a semantic judgement
about the scene rather than a geometric one. That is where the VLM goes.

## The data

`data/` is not in git. `scripts/fetch_seoul.sh` refills it.

**Seoul Sidewalk Accessibility Image Dataset** — Zenodo 22699523, published
2026-09-11, **CC-Zero**. 513 pedestrian-perspective photographs at 5712x4284,
each with a field-measured width in metres, running and cross slope in
degrees, a five-grade pavement condition and GPS. Public domain: it may train
a model, set a parameter that ships, and be redistributed.

It is Seoul and the thresholds are Taiwan's. That mismatch is a limitation to
state, not to paper over. Taiwan's own `data.gov.tw` dataset 58791 (人行道)
carries SW_WTH and SWW_WTH per segment and is the threshold-side source.

Note the protocol document says `ground_truth.csv` and `cross_slope_deg`; the
file is `summary_attributes.csv` and the column is `cross_slope`.

## The evaluation rule

A model is measured against predicting the training set's mean, on subjects
it was not fitted on. A ratio above 1 means the measurement is worse than not
measuring.

**And the evaluation set must not share the training set's blind spot.** This
rule exists because the previous project earned every accuracy figure on
rendered imagery while the product was fed photographs, and no amount of
cross-validation between two render-based sets could show it. Here the
photographs are real from the start, which removes that particular blind
spot and does not remove the rule.

**The decisive metric is the verdict, not the metre.** Report the wrong-verdict
rate among verdicts given, and the rate of declining, together. Either alone
can be made to look good.

## The order rule

Establish what inference is actually fed before quoting any accuracy figure.
Not after. The same applies to a unit, a threshold, a split and a
preprocessing step.

## The discovery rule

Standard practice is not a finding. Training and inference sharing a
distribution, a conversion living in one place, a proxy metric not being the
metric - applying these is the job. Record what was measured, in one line.

## The claim rule

Do not state that something exists, does not exist, or has a particular value
without checking it in this session. Memory of a repository is not evidence
about it.

Say "because X" only with evidence in hand that rules out not-X. Without it,
say "probably X, and I have not ruled out Y". On 2026-09-19 the previous
project produced three causal claims stated as fact in one day, each with a
mechanism that explained everything in view, and all three were wrong.
Explanatory power is not evidence.

## Figures

`results/figure_registry.json` pins every published figure to an RFC 6901
pointer into the file that produced it, with an `expect` block on a
neighbouring value so a mis-aimed pointer fails instead of passing.
`scripts/check_stage.sh` runs the check before every commit.

Figures quoted to anyone come from `results/` or from a script rerun in the
same session, never from a number remembered earlier in the conversation.

## Where this came from

An earlier competition entry of the owner's, in a separate repository,
was stopped on 2026-09-19; its own decision record says why, with the
measurements. The guard band, the tiered bands, the refusal ceiling and
the three-state gate are carried from it and are the part worth
carrying.

That repository is not named here and nothing in this project depends on
it. This entry is judged on its own, and a sibling path in a tracked
file tells a reader of a public repository about the author's disk and
nothing about the road.
