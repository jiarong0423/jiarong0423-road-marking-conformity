"""What to do about a refusal, decided by a typed-judgment model.

The gate already answers the measurable question deterministically, and
refuses when §171's own geometry says the thing measured is not the
marking. What it cannot say is which kind of refusal this is:

    the photograph shows no taper at all
    it shows one, but too badly for a measurement - retake it
    something is off that a person should look at

That is a routing decision over evidence the gate has already produced, and
it is the one place in this project where a model earns its call. The
`defect-triage-router` skill's rule is decompose deterministically first and
reserve the model for the class that genuinely needs judgment; here classes
that can be settled by a predicate are settled by one, and only what is left
is asked.

**No image is sent.** The state is the gate's own measurements - how much of
the near field was in frame, how many line segments, how many arms, their
angle to the band and its coherence, how much boundary was in view. The
model judges the evidence, not the scene, and saying so is part of the
answer it returns.

Question design follows that skill's measured findings rather than taste:

  - the options name concrete objects, because abstract wording cost it
    31 points there;
  - `criteria` carry a `what` and a `not_for`, and there is an escape
    option, because a forced choice among three invents a fourth;
  - nothing is ANDed across questions - one Choice, because two questions
    combined scored worse than either alone;
  - anything between 0.4 and 0.6 confidence abstains to a human, which took
    that pilot to 100% on the cases it kept.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Route:
    action: str          # RETAKE | NO_TAPER | HUMAN_REVIEW | MODEL_UNAVAILABLE
    confidence: float | None
    why: str
    asked: bool
    evidence: dict


# The pilot that set 0.4-0.6 was a two-option question, where a low
# confidence means the model is confident in the other option. This
# router asks a four-option question, where chance is 0.25 and a 0.19
# answer is worse than a guess. Treating that as decisive is indefensible,
# so anything short of confident now goes to a person and only the upper
# bound does any work.
ABSTAIN_LOW, ABSTAIN_HIGH = 0.0, 0.6


def _state(verdict_reason: str, checks: dict) -> str:
    """Only what the gate measured. Never the photograph."""
    lines = [f"A road-marking gate declined to measure a lane-closure taper.",
             f"Its stated reason: {verdict_reason}", "",
             "What it measured before declining:"]
    labels = {
        "near_field_in_frame": "fraction of the near ground plane inside the photograph",
        "line_segments": "straight line segments found on the road surface",
        "arms": "chevron arms kept after filtering",
        "arm_angle_coherence": "how far the kept arms share one direction, 0 to 1",
        "arm_to_band_remeasured_deg": "angle between those arms and the band, degrees "
                                      "(道路交通標誌標線號誌設置規則 §171 requires 45)",
        "boundary_run_camera_heights": "length of boundary line in view, in camera heights",
        "camera_to_road_deg": "angle between where the camera pointed and where the road runs",
    }
    for key, label in labels.items():
        if key in checks:
            lines.append(f"  {label}: {checks[key]}")
    return "\n".join(lines)


def route(verdict_reason: str, checks: dict, *, dry_run: bool = False) -> Route:
    # Settled by a predicate, so not asked. The skill's first rule.
    if not checks.get("road_bearing_given", True) or \
            not checks.get("heading_given", True):
        return Route("RETAKE", None,
                     "the request omitted the camera heading or the road's "
                     "bearing; that is a missing field, not a judgment",
                     False, checks)
    if checks.get("near_field_in_frame", 1.0) < 0.35:
        return Route("RETAKE", None,
                     "most of the near ground plane is outside the frame; "
                     "no judgment is needed to know the photograph is wrong",
                     False, checks)

    state = _state(verdict_reason, checks)
    if dry_run:
        return Route("HUMAN_REVIEW", None, f"dry run; would have sent:\n{state}",
                     False, checks)
    if not os.environ.get("TYPESAFE_API_KEY"):
        return Route("MODEL_UNAVAILABLE", None,
                     "TYPESAFE_API_KEY is not set, so the refusal is not "
                     "routed; it stands as a refusal", False, checks)
    try:
        from typesafe_sdk import TypeSafeClient, Choice
    except ImportError:
        return Route("MODEL_UNAVAILABLE", None,
                     "typesafe_sdk is not installed", False, checks)

    question = Choice(
        instructions="Given only these measurements, what should happen next "
                     "with this photograph",
        criteria={
            "no_taper": {
                "what": "the road surface in this photograph carries no "
                        "chevron hatching and no lane-closure taper, so there "
                        "is nothing here to measure",
                "not_for": "a taper that is present but poorly captured",
                "examples": "no arms found at all, or very few line segments "
                            "on the road",
            },
            "retake": {
                "what": "a chevron is probably there but the photograph does "
                        "not show enough of it: too little boundary in view, "
                        "arms that do not share a direction, or the camera "
                        "aimed far off the road",
                "not_for": "a photograph with no marking in it",
                "examples": "arms found but incoherent, or under 1.5 camera "
                            "heights of boundary in view",
            },
            "human_review": {
                "what": "the measurements are internally inconsistent in a way "
                        "that another photograph will not fix, and a person "
                        "should look at it",
                "not_for": "a case where more or better imagery would settle it",
            },
            "unclear": {
                "what": "these measurements do not distinguish the cases above",
            },
        },
    )
    try:
        resp = TypeSafeClient().system_one(state=state,
                                           questions={"next_step": question})
        answer = resp.answers["next_step"]
        pick, conf = answer.choice, float(answer.confidence)
    except Exception as exc:
        return Route("MODEL_UNAVAILABLE", None,
                     f"the router raised {type(exc).__name__}: {exc}", False,
                     checks)

    # The confidence gate the pilot found necessary: the middle band is not
    # a weak answer, it is an answer the model should not be asked to give.
    if conf <= ABSTAIN_HIGH or pick == "unclear":
        return Route("HUMAN_REVIEW", conf,
                     f"routed to a person: the model chose '{pick}' at "
                     f"{conf:.2f}, at or below the {ABSTAIN_HIGH} a "
                     f"four-way choice needs to act on", True, checks)
    mapping = {"no_taper": "NO_TAPER", "retake": "RETAKE",
               "human_review": "HUMAN_REVIEW"}
    return Route(mapping.get(pick, "HUMAN_REVIEW"), conf,
                 f"the model chose '{pick}' at {conf:.2f} from the gate's "
                 f"measurements alone; no image was sent", True, checks)


def route_ensemble(taper: dict, carriageway_found: bool,
                   *, dry_run: bool = False) -> Route:
    """What to do about an ensemble that would not answer.

    The ensemble refuses in two ways that look alike in the output and are
    not alike on the ground. It can find nothing chevron-shaped in any
    encoding, which means there is no taper here to measure. Or it can
    find one in every encoding and get a different angle each time, which
    means there is a taper and this photograph cannot pin it down. The
    reading count is the same in both.

    Deterministic first, as the skill requires. A frame with no
    carriageway, or with no candidate in the regulated corridor in any
    encoding, or with hatching in none of them, is settled by a predicate
    and is not asked. What reaches the model is the case where the
    evidence exists and disagrees with itself, which is a judgment about
    which kind of disagreement it is.

    No image is sent, exactly as in route(). The state is the ensemble's
    own counts.
    """
    ev = taper.get("evidence") or {}
    checks = {
        "encodings_attempted": taper.get("attempted"),
        "encodings_total": taper.get("encodings"),
        "readings": taper.get("readings"),
        "angle_low_deg": taper.get("taper_deg_min"),
        "angle_high_deg": taper.get("taper_deg_max"),
        "encodings_with_candidates": ev.get("encodings_with_candidates"),
        "encodings_with_bordering": ev.get("encodings_with_bordering"),
        "line_segments_min": ev.get("segments_min"),
        "line_segments_max": ev.get("segments_max"),
    }

    if taper.get("state") in ("STEEPER_THAN_REFERENCE", "WITHIN_REFERENCE"):
        return Route("NONE", None, "the ensemble answered; nothing to route",
                     False, checks)

    # The ensemble already decided whether this is a road photograph, and
    # it knows why. Re-deriving it here would let the two disagree.
    why0 = taper.get("why") or ""
    if taper.get("roi_frac") is not None and "not a road photograph" in why0:
        return Route("RETAKE", None,
                     f"this is not a photograph of a road: {why0}. A "
                     f"predicate settles it", False,
                     {**checks, "roi_frac": taper.get("roi_frac")})

    if not carriageway_found:
        return Route("RETAKE", None,
                     "no carriageway was found in the frame, so there is no "
                     "road for a taper to be on; that is a predicate, not a "
                     "judgment", False, checks)

    if not ev.get("encodings_with_candidates"):
        return Route("NO_TAPER", None,
                     "no encoding found any line inside the corridor the "
                     "regulation allows a taper to occupy; a predicate "
                     "settles this", False, checks)

    if not ev.get("encodings_with_bordering"):
        return Route("NO_TAPER", None,
                     f"{ev['encodings_with_candidates']} encodings found "
                     f"lines in the corridor and none of them borders "
                     f"hatching as §171 requires of a chevron boundary; a "
                     f"predicate settles this", False, checks)

    if dry_run:
        return Route("DRY_RUN", None, "predicates did not settle it; the "
                     "model was not called", False, checks)
    return _route_grid(taper, checks)


def _grid_table(taper) -> str:
    """The 3x3 grid, cell by cell.

    The first version of this handed the model eight aggregate counts and
    it answered at 0.22 to 0.36 on a four-way choice, which is chance. The
    counts were the problem: failing only at low resolution and failing in
    all nine cells produce the same totals and call for opposite actions.
    The grid's shape is the evidence, so the grid is what goes.
    """
    cells = (taper.get("evidence") or {}).get("cells") or []
    if not cells:
        return "(no per-encoding record)"
    out = ["Each row is one encoding of the same photograph. px is the long "
           "side it was measured at, q the JPEG quality it was saved at.",
           "",
           "  px     q    line_segments  candidates_in_corridor  "
           "bordering_hatching  angle_deg"]
    for c in cells:
        deg = "none" if c.get("deg") is None else f"{c['deg']:.2f}"
        out.append(f"  {c['px']:<6} {c['q']:<4} {c['segments']:<14} "
                   f"{c['candidates']:<23} {c['bordering']:<19} {deg}")
    return "\n".join(out)


def _route_grid(taper, checks) -> Route:
    if not os.environ.get("TYPESAFE_API_KEY"):
        return Route("MODEL_UNAVAILABLE", None,
                     "TYPESAFE_API_KEY is not set", False, checks)
    try:
        from typesafe_sdk import TypeSafeClient, Choice
    except ImportError:
        return Route("MODEL_UNAVAILABLE", None,
                     "typesafe_sdk is not installed", False, checks)

    state = (
        "A system measures the angle between a road's direction and the "
        "boundary of a chevron road marking, from one photograph. It "
        "measures the same photograph nine times, at three working "
        "resolutions and three JPEG qualities, and reports a verdict only "
        "when all of them agree. On this photograph they did not, so "
        "something must be decided about the photograph itself.\n\n"
        f"Why it would not answer: {taper.get('why', 'unstated')}\n\n"
        + _grid_table(taper) +
        "\n\nNo image is being shown. These measurements are all there is."
    )

    # unclear was an option in the first version. It is not a state of the
    # road or of the photograph, it is a state of the model, and mixing it
    # in with physical states blurred all of them. Not knowing is handled
    # by the confidence gate below, where it belongs.
    question = Choice(
        instructions="Decide what is true of this photograph.",
        criteria={
            "nothing_there": {
                "what": "the road in this photograph carries no chevron "
                        "marking, so the measurement has nothing to find",
                "not_for": "a chevron that is present but poorly captured",
                "examples": "plenty of line segments found, meaning the "
                            "photograph is sharp, but few or no candidates "
                            "border hatching in any row",
            },
            "photograph_inadequate": {
                "what": "a chevron is there, but this photograph does not "
                        "capture it well enough; a better photograph of the "
                        "same place would settle it",
                "not_for": "a road with no marking on it",
                "examples": "the rows differ systematically with resolution "
                            "or quality - working at one size finds the "
                            "marking and another does not - or the line "
                            "segment count falls away as the rows change",
            },
            "scene_ambiguous": {
                "what": "the chevron is captured well and the measurements "
                        "still disagree, because the scene itself offers "
                        "more than one boundary; another photograph of the "
                        "same place would disagree in the same way",
                "not_for": "a case a better photograph would fix",
                "examples": "most rows find bordering candidates and the "
                            "angles they give are far apart, with no pattern "
                            "in resolution or quality",
            },
        },
    )
    try:
        resp = TypeSafeClient().system_one(state=state,
                                           questions={"what_is_true": question})
        a = resp.answers["what_is_true"]
        pick, conf = a.choice, float(a.confidence)
        probs = dict(getattr(a, "probabilities", {}) or {})
    except Exception as exc:
        return Route("MODEL_UNAVAILABLE", None,
                     f"the router raised {type(exc).__name__}: {exc}", False,
                     checks)

    checks = {**checks, "probabilities": probs}
    if conf <= ABSTAIN_HIGH:
        return Route("HUMAN_REVIEW", conf,
                     f"routed to a person: '{pick}' at {conf:.2f}, at or "
                     f"below the {ABSTAIN_HIGH} needed to act", True, checks)
    mapping = {"nothing_there": "NO_TAPER",
               "photograph_inadequate": "RETAKE",
               "scene_ambiguous": "HUMAN_REVIEW"}
    return Route(mapping.get(pick, "HUMAN_REVIEW"), conf,
                 f"'{pick}' at {conf:.2f}, from the nine-row grid alone; "
                 f"no image was sent", True, checks)
