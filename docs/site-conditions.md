# What the site is like, from someone who rides it

Facts about this location that no dataset holds and no photograph gives up
on its own. They are recorded as testimony from the person who uses the
road, separately from anything measured, because that is what they are -
and because each one has changed what the measurement means.

## The right-hand edge is not carriageway, and the rule says so

The rider's question was whether that strip is somewhere a motorcycle is
supposed to ride, because if it is not, then a car alongside leaves nowhere
to go. 道路交通標誌標線號誌設置規則 §169, on where a 禁止臨時停車線 is
drawn:

> 以劃設於**道路緣石**正面或頂面為原則，無緣石之道路得標繪於路面上，
> 距路面邊緣以三十公分為度

The red line here is painted on the raised concrete strip. By §169 that
makes the strip the **kerb**, and a kerb is not carriageway. The drain
covers and studs set into it are a second reason, but the first is enough.

So the squeeze is an arithmetic result, not a behaviour:

1. ~~the red line is on the kerb, so the carriageway ends there (§169)~~
   **WITHDRAWN 2026-09-22.** §169 also provides for red lines on the road
   surface where there is no kerb, so a red line does not prove a kerb;
   F30-F32 show the intact line on a concrete strip level with the road,
   the kerb a separate raised element further out, and a second worn line
   0.63-0.68 m nearer the lane. `isolation/REDLINE.md`.
2. the kerb is raised and studded, so a motorcycle cannot use it anyway
3. with a vehicle alongside there is no room right, only left
4. left is the chevron, reached through 14.9 m of taper - under 2 s at any
   speed this road carries, against 2.5 s to react
5. and 道路交通安全規則 §101 asks half a metre of clearance, which beside
   anything at the 2.5 m legal maximum no lane in the design range provides

Two of those five are statute, one is measured here, two are the rider's
account of standing there. They meet.

## The right-hand edge is not available

Beyond the carriageway edge there is a concrete gutter carrying the
kerbside red line and the drain covers, and beyond that the pavement.

**Two things I wrote here were wrong and are corrected.** I described the
gutter as raised and said a row of road studs ran along it. The person who
rides this road says it is not raised, and asked what I meant by road
studs - which is the right question, because I had inferred both from one
magnified Street View crop and neither is in the photograph. A dark speckle
beside a red line is not a stud. They were load-bearing claims in this file
and in a commit message, and they were mine, not the site's.

What survives without them is the part with a citation. §169 puts the
kerbside red line on the kerb, so the carriageway ends at it, and drain
covers are not a running surface for two wheels whether or not they stand
proud. A motorcycle squeezed by a wider vehicle still has no room right.

The consequence runs straight into the rest of this project. The lane has
one escape and it is to the left, onto the chevron, through a taper measured
here at 14.9 m - under 2 s at any speed this road carries, against the 2.5 s
a driver needs merely to react. The rider's account of this site, given
before any of it was measured, was 「之前有來不及騎到槽化線過，因為縮減太
快」. The geometry agrees with them.

`src/marking/extract.py` now bounds its region at that edge, which is also
why the extractor stopped finding markings in the verge.

## There are a great many drain covers

Stated by the rider: this stretch has a lot of them, and the road is hostile
to motorcycles because of it. Longitudinal grating is a known lateral-grip
problem for two wheels, so this is a traction fact, not a comfort one.

A detector for dark filled rectangles sitting on the pale raised gutter
finds a median of 12 per frame across the eight 2025-06 panoramas spanning
84 m, ranging 3 to 24. Neighbouring frames see the same covers, so that is a
density per view and not a count along the road, and **it has not been
validated against ground truth.**

Which is a failure worth stating. The rider annotated a capture with arrows
pointing at individual covers - labels, given unprompted, for exactly this.
The first pass through that annotation kept only the long dashed lines and
discarded the arrows as short red noise. The second pass tried to recover
them and extracted 48 "arrow tips" that are in fact the dashes of the dashed
line, marching monotonically along it; matching those against 12 detections
returned 5 hits and validates nothing. **The labels were mishandled twice** before being recovered.

The third attempt separates them on area, and the threshold is the data's
own: sorted by area the red components step 60, 63, ... 91, then **288**,
372, 425, 513, 525, 913. The largest ratio between neighbours is 3.16, at
91 → 288, so the cut is 190 and nothing is chosen by eye. That returns six
components against the rider's count of seven, and the largest is 913
where the others average 424 - two arrows touching, which reconciles the
two numbers. The width-profile test used before this failed because an
arrow that touches the dashed line stops having an arrow's profile.

Tips are at `data/annotations/drain_arrow_tips.npy`, in the repository
rather than a session directory this time.

## The works

Speed limit 50 before, 30 during. The rider saw two arrows where Street View
shows one; the second is under the chevron. They corrected a misreading of a
車道縮減線 as a 斑馬線, which is what turned up §155 and §188-1. There was no
milling before these works, so the rough surface on the right is entirely
new and was carriageway.

None of this is in 養工處's records, the excavation permits, the orthophoto
or Street View. It came from someone standing there.

## The kerb was cut out, and I read it wrong twice before reading it right

**The premise was withdrawn by the person who gave it.** The account was
that the drain covers were later removed and the road widened; they have
since said they misspoke and that nothing was removed. So there is no
"why was it widened" to answer.

The three attempts at verifying it are kept anyway, because the errors in
them were mine and not the premise's, and because two photographs do
support something narrower that is worth having.

**First attempt, wrong place.** I compared the right-hand edge in the
2025-06 Street View against field photographs F05 and F07 and concluded
the carriageway had been extended over the gutter. F05 and F07 are not at
the chevron - they are upstream, at the 往樹林 legend, with the site
hoarding on the left. I compared two different locations and drew a
conclusion from the difference between them. Withdrawn.

**Second attempt, right place, wrong reading.** Comparing the same spot -
2025-06 against F17 and F19 - I saw the chevron gone thin and a broad
rough band on the right, and called it deterioration. It is not.

**Third attempt.** Cropped to the edge itself at the same location:

| | |
|---|---|
| 2025-06 | smooth asphalt, concrete kerb, the red line on it, a grated drain cover, then the pavement |
| 2026-09 F17, F19 | asphalt, then **a straight continuous cut** running with the road, and beyond it a broad band of rough backfill reaching the frame edge. No kerb, no red line, no grated cover along that stretch |

**Wrong as well.** The rider says the drain covers are still there. What
F17 and F19 show at that crop is not their absence; it is a stretch where
they are not in the frame, and I read the crop as the road.

So: a straight continuous cut runs with the road and there is rough fill
beyond it, which is a saw cut and made-up ground rather than a crack and
damage. That much two photographs support. **What it means for the kerb
and the drainage they do not support, and I asserted it three times.**

It also identifies something this project failed to measure earlier. The
"milled area" that a segmentation put at 12.8% and that was recorded as
under-detected is not pavement damage. **It is this work.**

Three readings of the same photographs, all three confident, all three
corrected by the person standing on the road. The pattern is not that the
photographs are poor - the first error was comparing two different
locations, the second and third were reading absence into a crop. It is
that I kept inferring site change from imagery at a scale the imagery does
not carry, after being corrected twice.

**What two photographs support**: a straight continuous cut running with
the road, with rough made-up ground beyond it - a saw cut and backfill
rather than a crack and damage. And that the "milled area" an earlier
segmentation put at 12.8% is that work rather than pavement damage.

**What they do not support**: that anything was removed. The kerb, the red
line and the drain covers are still there. I asserted otherwise three
times from crops that simply did not contain them.

Worth separating the two failures. Mine was inferring site change from
imagery at a scale it does not carry, three times, after two corrections.
The premise being mistaken is not the same thing and does not excuse it -
the readings were wrong on their own terms, and the first one, comparing
two different locations, would have been wrong whatever the premise.
