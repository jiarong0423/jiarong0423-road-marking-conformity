> **Historical working note (content from 2026-09-21).** Numbers and status here may be superseded. The current account is [`technical-report.md`](technical-report.md); withdrawn figures are listed there.

# Submission checklist — OpenCV AI Competition 2026

Deadline 2026-10-26. Rubric as recorded in `docs/competition.md`, which was
written against https://opencv26.devpost.com/ on 2026-09-21.

This page is the checklist, not the argument. `docs/competition.md` is the
rubric-by-rubric assessment; `docs/claims.md` is what the project claims and
does not claim. Where the two disagree with this page, re-run the command in
the right-hand column — the commands are the only things here that do not go
stale.

**Who can do what.** Three of the open items cannot be done by writing, and
two of those can only be done by the repository owner:

| actor | can do |
|---|---|
| **owner only** | push to GitHub; record the video; anything needing AWS credentials (redeploy, benchmark, reading the live function's configuration) |
| **anyone working in the repository** | track untracked files, fix stale prose, write scripts, publish the offline harness |
| **nobody, by writing** | the video. It has to be recorded. |

---

## 1. Hard requirements

| requirement | state | what is missing | who | check |
|---|---|---|---|---|
| **Video, ≤ 5 min, showing team, application, architecture, results** | **absent** | nothing is recorded. This cannot be produced by writing, planning or documenting. Someone has to sit down and record it, and it is the single item most likely to cost the entry. | owner | `find . -iname '*.mp4' -o -iname '*.mov'` returns nothing |
| **Judge-accessible repository** | **public, stale** | the remote is behind local. A judge opening it today gets no field photographs, no licence, and `carriageway()` still cutting the chevron out. **Pushing needs the owner's approval and has not been given.** | owner | `git ls-remote origin main` against `git rev-parse HEAD`; `git log --oneline origin/main..HEAD` |
| **Technical report: problem, users, architecture, implementation, deployment, evaluation** | **partial** | all six are covered across `docs/`, but no single reader-facing report exists. `docs/competition.md` is closest and is itself untracked. | anyone | `ls docs/` |
| **Architecture diagram showing OpenCV 5 and AWS components** | **exists, untracked** | the Mermaid diagram in `docs/competition.md` §1. It was the first architecture diagram in the repository and the file holding it is not in git. | anyone | `git status --short docs/competition.md` |
| **Working web endpoint** | **live** | it returns 200. It runs the pre-fix image, is unauthenticated and unthrottled, and one measured request took ~31 s against a 30 s gateway timeout. | owner (redeploy) | `curl -s -o /dev/null -w '%{http_code} %{time_total}\n' https://3p4k7s4bx7.execute-api.ap-southeast-2.amazonaws.com/` |
| **Evaluation evidence, including failure cases** | **strong on failures, no ground truth** | the failure record is unusually complete: a withdrawn headline measurement, a defect that made results worse, and a register of void comparisons. What is absent is a held-out set and any measured truth for the taper. | anyone | `grep -l withdrawn results/*.json`; `docs/reproducibility-2026-09-21.md` |
| **Pinned dependencies** | **partial** | `requirements.txt` is fully pinned; `aws/Dockerfile` installs `numpy>=2.0` unpinned, so the image is not reproducible across rebuild dates. | anyone | `grep -n numpy requirements.txt aws/Dockerfile` |
| **Clear instructions** | **partial** | `README.md` covers install and run. `docs/deployment.md` is stale on memory size and image tag (see `docs/claims.md` §6). | anyone | `grep -n '2048\|v2' docs/deployment.md` |
| **Tests** | **pass, one-sided** | 32 pass. Standing rule 6: every one tests a refusal; none asserts that a genuine road photograph is measured. | anyone | `/opt/anaconda3/bin/python3 -m pytest tests/ -q` |
| **Licence** | **present, unpushed** | MIT, commit `ce770e0`, not on `origin`. | owner | `ls LICENSE; git log --oneline origin/main..HEAD -- LICENSE` |
| **Primary evidence published** | **present, unpushed** | 42 originals with a SHA-256 manifest, commit `ce770e0`, not on `origin`. | owner | `ls evidence/field-2026-09-20/ \| wc -l` |

## 2. Prize-track requirements

| requirement | state | what is missing | who |
|---|---|---|---|
| **COOL — core workload on Graviton** | **met** | `Architectures: ["arm64"]` on the live function; the image is built `--platform linux/arm64`. | — |
| **COOL — reproducible measurement against a baseline** | **absent** | no benchmark has been run. `docs/competition.md` §8 specifies one precisely enough to execute: same commit, two Lambdas, 42 originals, 9 timings each, correctness gate on the verdicts, output to `results/cool_benchmark.json` and the registry. | owner (needs AWS) |
| **COOL — actually uses the Cloud-Optimized OpenCV Library** | **unestablished** | the image installs the stock `opencv-python-headless` wheel. What COOL is has two irreconcilable accounts in `docs/status-2026-09-20.md`. **Settle this before running the benchmark**, or the benchmark answers a different question from the one the award asks. | anyone (research), then owner |
| **Agentic Vision — a vision result drives an action** | **built, not wired** | `src/marking/route.py` is imported by nothing, the deployed function has no model key, and the harness that produced its numbers is not in the repository. A judge cannot rerun any of it. | anyone (wire + publish harness); owner (key, via a secrets store, never an env var in a public repo) |

## 3. Things that are wrong in the repository right now

Not competition requirements, but each is visible to a judge.

| item | check |
|---|---|
| Untracked files a judge would need — the comparisons register, the architecture diagram, `models/` with its Apache-2.0 licence, and whatever else has appeared since | `git status --short` |
| Documents quoting withdrawn figures — `docs/evidence.md`, `docs/thesis.md`, `docs/timeline-116.md` | `docs/claims.md` §6 lists them line by line |
| `evidence/field-2026-09-20/README.md` overstates nothing and understates the set size; its second verification snippet raises `KeyError` | `docs/claims.md` §6 |
| `docs/reproducibility-2026-09-21.md` quotes the pre-recalibration frame-coverage gate | `grep -n ROI_FRAC_MAX src/marking/situation.py` |
| The endpoint's `GET` documents five finding codes; the code can emit six | compare the `curl` output against `grep -rno 'CARRIAGEWAY_OCCUPIED' src/` |
| `scripts/check_stage.sh` and `scripts/install_hooks.sh` are repaired but uncommitted | `git status --short scripts/` |

## 4. Order of work

Ordered by what blocks what, not by effort.

1. **Push.** Seven commits, including the 42 photographs, the licence and the
   `carriageway()` fix, exist only locally. Nothing else on this list is
   visible to a judge until this happens, and it needs the owner's approval.
2. **Track what is untracked.** The architecture diagram and the comparisons
   register are both `??` today.
3. **Rebuild and redeploy from the post-fix commit**, then send it a
   photograph that actually asserts a taper. That code path crashed in local
   code until 08:15 on 2026-09-21 and has never run in production.
4. **Record the video.** It cannot be written, it is absent, and it is a
   stated requirement.
5. **Re-run what §3 of `docs/claims.md` lists as measured through the
   defect**, or leave the numbers withdrawn. Quoting them to a judge without
   re-running is the failure mode this project exists to avoid.
6. **Settle what COOL is**, then run the benchmark in `docs/competition.md`
   §8 if the answer permits.
7. **Publish the routing harness**, or drop the Agentic Vision claim. The
   numbers behind it are currently unreproducible by anyone but their author.
8. **Fix the stale prose** listed in `docs/claims.md` §6 and pin `numpy` in
   `aws/Dockerfile`.
9. **Write one reader-facing technical report**, if time remains after the
   above. The material exists; it is assembly.

## 5. What to say if the honest version costs the entry

It should not, and saying it plainly is cheaper than being caught.

The entry's argument is that a conformity check under measurement uncertainty
must be allowed to refuse, and this project demonstrated that on itself: it
withdrew its own headline measurement when the same photograph at a different
JPEG quality gave a different answer. A submission that hid that would be
claiming the opposite of what it is arguing for.

What must not happen is quoting a withdrawn figure in the video or the report
because it made a better slide. `results/figure_registry.json` is the list of
what may be quoted, and `docs/claims.md` §2 is the list of what may not.
