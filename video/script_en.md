# Video script (English)

Format: `{{...}}` in a subtitle cell is spoken but not shown as subtitle.
Format: slide edit, English subtitles burned in, about 4 min 15 s. The first 30 seconds state the point and the technique. Rows are in play order; # is the audio file number. Bilingual draft approved by the owner on 2026-10-14: `script_bilingual_draft.md`.
No Google Street View imagery on any slide.

| # | Time | On screen | Subtitle |
|---|---|---|---|
| 18 | 0:00–0:25 | Opening: top-down view + red line over the grates | This is OpenCV 5 on AWS, measuring one road from a rider's phone photos. It turns my photo into a top-down view, with the lane dashes as its ruler. Here it found a red line painted across the drain grates, and a merged lane where, by my own sum, a car and a scooter have about ten centimetres to spare. |
| 1 | 0:25–0:41 | Title: Seven drain grates on County Road 116 | I ride this road every day. Before the repainting, you had to change lanes in a hurry. After it, you hit seven drain grates in a row. Who measures the danger to riders? |
| 3 | 0:41–1:01 | Solo — one rider, one smartphone | The team is just me, a rider with a smartphone. I'm not here to say who broke the rules; I turn what a rider feels into numbers anyone can check. {{Every photo in this video, I took myself on 20 and 23 September.}} |
| 5 | 1:01–1:15 | Recognition: red line over grates (`red-line-over-grates.jpg`) | I used OpenCV to find the grates and the red line. In every top-down photo where it found a grate, the new red line runs straight across it. |
| 6 | 1:15–1:32 | Rules card + photo P22 (`redline-gutter-kerb-P22.jpg`) | The rules say a red line goes on the kerb and marks the road's outer edge, and a lane is whatever the markings enclose. So the drain strip is now inside the road. |
| 7 | 1:32–1:54 | Card-as-ruler photo (grate 7) | My ruler is the red line itself: 10 cm wide by law. I checked it with a standard-size card: about 95 to 97 mm. The red line moved out by 0.63 to 0.68 metres. |
| 8 | 1:54–2:11 | Schematic (`schematic.png`) + number card | Here is the stretch: a double white line, then a painted island. Where I measured it, it opens at about 12 to 1; the design table's reference is 5 to 1 at 30 km per hour. |
| 16 | 2:11–2:40 | Before: old edge marked by hand, from my own photo (`before_overlay.jpg`) | During the works, scooters and cars would both ride partly over the painted chevrons: my own observation. OpenCV can't find the old edge, so I marked it myself. From it, about two thirds of the island was painted over where I measured. Beyond it is rough surface I know was milled. How steep the old edge was, I could not establish. |
| 17 | 2:40–3:02 | Top-down: the old end painted over (`erased-triangle-P64.jpg`) | Standing on the road, you can't compare old and new paint. From above, about eight and a half metres of the island's old end was painted over, and an arrow is painted on top. After the merge, everyone shares one lane of about three point one metres. |
| 10 | 3:02–3:18 | Architecture (`architecture.png`) | How it works: upload one photo. It checks it's a road, reports a number only if three of four re-saved versions agree, and says which document to request next. |
| 14 | 3:18–3:34 | Agentic loop: perceive, decide, act (`agent-workflow.png`) | Here is the loop. What OpenCV finds decides the next step: retake the photo, refuse a number with the reason, request a document, or mark a box for a person to open. |
| 11 | 3:34–3:48 | Result card: API response (local container, full-size photo) | This is the same service run locally on a full-size photo; online, full-size photos time out. It says what it measured, what it couldn't, and why. |
| 9 | 3:48–4:00 | Withdrawn: why my 10 to 1 was wrong (`f40_picks.jpg`) | I first published 10 to 1. The program had picked the wrong lines, and the answer changed when the photo was re-saved, so I withdrew it. |
| 15 | 4:00–4:19 | What it can't do yet (text card) | What it can't do yet: full-size photos time out online, the old end is measured on one photo, and the grate step and grip are not measured. {{It files nothing and contacts no one.}} |
| 12 | 4:19–4:43 | The stack: left, right, underfoot, glare, the merge | Each problem sits at the limit. But they all land on the same stretch: no crossing on the left, grates on the right, the lane narrowing, and the winter sun in your eyes. After the merge, in my experience, scooters and cars fight for one lane, and in rain or at night it gets worse. |
| 13 | 4:43–4:53 | Close: three documents to request | Next: request the documents from the Traffic Department, the Metro construction office, and the district office. Thank you. |

## Open decisions
- #8: the old taper before repainting is not given (not established from my own photos; nothing from Street View is published).
- Project name.
- Voiceover: an external TTS would receive this text.
- #11: screenshot from the cloud after deployment, or from the local container, labelled as such.
