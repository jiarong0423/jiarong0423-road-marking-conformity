# Standing rules

Frozen 2026-09-21. Every rule here exists because it was broken on that
day, and the instance is named so the rule cannot be argued with in the
abstract.

## 1. No number without a full-population run

A claim measured on part of the set is a hypothesis. It is written down as
a hypothesis, with its n, or it is not written down.

> Reduction to 2000 px was called lossless on 2 photographs. Over 42 it
> changed 17 findings and 10 verdicts. Parameter scaling improved the
> spread three-fold on 14; over 42 it was worse. A defect was called "95%"
> from one crop; frame-wide it is 14.3%. Four times in one session, and
> four times the full run reversed it.

## 2. No number without an artifact

Every figure that appears in prose goes into `results/figure_registry.json`
with a JSON pointer to the file that produced it, and that file is
produced by a script in `scripts/`. The registry's own note already says
it: *a number that is not here is not verified, wherever else it appears.*

> Not one figure from 2026-09-21 was registered. By the project's own
> definition all of them are unverified.

## 3. The pre-commit check runs, or the commit does not

`scripts/check_stage.sh` must reach `scripts/check_figures.py`. If a
workspace-level hook replaces it, the project's check is chained behind
it, not dropped.

> On 2026-09-21 the hook was replaced by a shim to a shared security gate
> that does not call `check_figures`. The commit immediately before was a
> hardening of the check that had just become unreachable.

## 4. Measure the original; perturbation is a check, not a measurement

The value comes from the best available data. Perturbation establishes
whether that value is stable, and its spread is the uncertainty. A grid
that never includes the original has no value to be uncertain about.

> The ensemble measured nine degraded cells and never the original, while
> the regulation is written in centimetres: a 10 cm line is 14.2 px in the
> original and 3.5 px at the working size, and the ±6 mm tolerance is
> 0.85 px and 0.21 px. The conformity check was impossible by
> construction.

## 5. Fixing a defect invalidates every constant calibrated against it

When behaviour changes, every threshold measured against the old
behaviour is re-derived in the same commit, or the commit says which were
not and why.

> `ROI_FRAC_MAX = 0.75` came from "real road photographs run 18-61%",
> measured against a region that cut the chevron out. After the fix the
> region legitimately grew and 7 of 12 real photographs were refused as
> "not a road photograph".

## 6. Test that valid input is accepted, not only that invalid input is refused

> 32 tests passed throughout rule 5's regression. Every one of them tests
> a refusal. Not one asserts that a genuine road photograph is measured.

## 7. Check it is connected before improving it

> Hours went into a routing component - tuning its inputs, its confidence
> rising from 0.27 to 0.91 - and nothing in the codebase imports it.

## 8. A subagent's report is re-derived, not relayed

> Of three claims checked from one agent's report, two were wrong: a
> "shared extractor" that the script does not import, and an "n=3" that
> the source states as n=4 and flags as thin. The report was detailed and
> confident.

## 9. A metric must not be able to score itself

> The fix in rule 5 was scored by "what fraction of the marking mask
> survives the region", and the fix works by erasing the marking mask
> before computing the region. Any preprocessing that erases the scoring
> mask wins by construction. 46 of 46 is what the design guarantees.

## 10. Measure both errors

A gate that only reports what it keeps is not evaluated. Report what it
wrongly admits at the same time.

> `carriageway()` exists to exclude the opposite carriageway and the
> verge. After the change only retention was measured. Segments tripled
> and that was reported as signal recovered, with nothing distinguishing
> it from signal wrongly admitted.

## 11. Review before the irreversible step, not after

Publishing, pushing, making public, sending: each is a door that only
opens one way. The review that decides whether the thing is fit to go
happens before it goes.

> 42 photographs of a public road were pushed to a public repository and
> the privacy review was started afterwards. Five carried a legible
> vehicle registration plate. The repository was made private within
> minutes, but by then the fix was no longer a `git rm`: the originals
> were blobs in the remote's history, a force-push left them retrievable
> by SHA through GitHub's API, and the repository had to be deleted and
> rebuilt to be sure they were gone. Reviewing first would have cost
> twenty minutes.

The corollary, which cost the second half of that afternoon: **a rewrite
is not a deletion.** Removing something from a repository's history does
not remove it from the host that already has it.

## 12. `git commit` takes the index, not your last `git add`

Staging your own files is not enough when something else is also
staging. Check `git diff --cached --name-only` before committing, or
commit the paths explicitly.

> Two commits on 2026-09-21 carried, under their own messages, a test
> file and a set of document annotations written by another agent that
> had staged them moments earlier. The content was sound and it was
> published unreviewed, which is what rule 8 exists to prevent one level
> up.

## 13. A test that passes without testing its claim is worse than no test

A missing test is visible. A vacuous one reads as coverage. Before
trusting a test, make the thing it forbids and watch it fail.

> `test_pitch_error_does_not_reach_the_angle` looped
> `for wrong in (-23, -25, -27)` and never used `wrong`. It asserted the
> same fixed expression three times. It passed, it had passed since it
> was written, and it was the single test the project's whole
> measurement claim rested on after the pose-based pipeline was dropped.
> Found 2026-09-21 by a supervision agent reading it, not by running it.
>
> The same day, `pipeline.py` asserted twice in its own docstring that
> `tests/test_pipeline.py` enforced the invariant that was the module's
> reason for existing. That file did not exist.

Both are now written and both were checked by mutation: four changes
that break an invariant, four failures, and a pass on restore.

## 14. A remediation edits the evidence, and has to be verified like one

A fix applied to primary evidence is a change to primary evidence. It
gets the same check as the thing it is fixing, and the check runs
against the whole set, not the files that were touched.

> The plate redaction on 2026-09-21 wrote five photographs without
> carrying the EXIF over. They shipped with zero tags. `MANIFEST.csv`
> still recorded their 35 mm equivalent focal length - the one camera
> parameter every measurement here needs - so for five of the 42 that
> number had quietly become an assertion no reader could check against
> the file.
>
> Nothing reported was wrong. Nobody looked for it either. It surfaced
> because the new pipeline was run over all 42 and returned no focal
> length on exactly five, which is rule 1 paying for itself on a
> question nobody had asked.

`tests/test_evidence_integrity.py` now reads the focal length out of
every published photograph and fails if any is missing or disagrees with
the manifest. A repaired file has to prove the repair, not be trusted
for it.

## What to do when a rule and a deadline disagree

Write the number down with its n and mark it a hypothesis. That costs one
line and is the whole difference between a result and a guess.
