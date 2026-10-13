# Video script (English)

Format: `{{...}}` in a subtitle cell is spoken but not shown as subtitle.
Format: slide edit, English subtitles burned in, ≤ 5 min. Covers team, application, architecture, results.
No Google Street View imagery on any slide.

| # | Time | On screen | Subtitle |
|---|---|---|---|
| 1 | 0:00–0:15 | Title: Seven drain grates on County Road 116 | I ride this road every day. Before the repainting, you had to change lanes in a hurry. After it, you hit seven drain grates in a row. Who measures the danger to riders? |
| 2 | 0:15–0:35 | Early-morning photo, grate 3 (`redline-gutter-kerb-P22.jpg`) | This is the right-hand side. The old red line sits at the edge of the asphalt. The new one is painted on the drain strip. The kerb is further out. |
| 3 | 0:35–0:55 | Solo — one rider, one smartphone | The team is just me: a rider who uses this road every day, with a smartphone. I'm not here to say who broke the rules. I turn what a rider feels into numbers anyone can check. {{Every photo you see in this video, I took myself on site, on 20 and 23 September.}} |
| 4 | 0:55–1:25 | Schematic (`schematic.png`) | Here is the stretch: a double white line where you can't change lanes, then a long painted island that narrows the lane, and seven drain grates on your right. |
| 5 | 1:25–1:55 | Recognition: red line over grates (`red-line-over-grates.jpg`) | I used OpenCV to find the grates and the red line. In every top-down photo where it found a grate, the new red line runs straight across it. |
| 6 | 1:55–2:15 | Rules card: §169, §183, Urban Road Standard §2 | The rules say a red line goes on the kerb, that it marks the outer edge of the road, and that a lane is whatever the markings enclose. So the new line puts the drain strip inside the road. |
| 7 | 2:15–2:40 | Card-as-ruler photo (grate 7) | My ruler is the red line itself: 10 cm wide by law. I checked it with a standard-size card: about 95 to 97 mm. The red line moved out by 0.63 to 0.68 metres. |
| 8 | 2:40–3:00 | Lane narrowing today (`taper-2026-after-erasure.jpg`) + number card | How sharply does the lane close? Today it's about 12 to 1. For reference, the design table asks for 5 to 1 at 30 km per hour, for lane shifts at turning lanes. |
| 16 | 2:55–3:25 | Before: old edge marked by hand, from my own photo (`before_overlay.jpg`) | During the works the lane closed in a sharp turn, and scooters and cars could easily ride onto the island: my own observation. OpenCV measures the paint, but it can't find the old edge or the milled asphalt, so I marked the old edge myself. From it, about two thirds of the island was painted over where I measured, and beyond that edge the photo shows at least two and a half island-widths of rough surface, which I know was milled. How steep the old edge was, I could not establish. |
| 9 | 3:10–3:30 | Withdrawn: why my 10 to 1 was wrong (`f40_picks.jpg`) | I first published 10 to 1. When I checked again, I found the program had picked the wrong lines, and the answer changed with image quality. I withdrew it. In my offline analysis, two different tools now have to agree. |
| 10 | 3:30–3:55 | Architecture (`architecture.png`) | How it works: upload one photo. It checks the photo shows a road, reports a measurement only if at least three of four re-saved versions agree, and tells you which document to request next. |
| 14 | 3:30–3:55 | Agentic loop: perceive, decide, act (`agent-workflow.png`) | Here is the loop. What OpenCV finds decides what happens next: not a road, retake; a number that moves when the photo is re-saved, refused with the reason; a finding that calls for it, a document request or a box for a person to open. |
| 11 | 3:55–4:15 | Result card: API response (local container, full-size photo) | This is the same service run locally on a full-size photo, because the online endpoint's memory cap makes full-size photos time out. It tells you what it measured, what it couldn't, and why. |
| 15 | 4:20–4:40 | What it can't do yet (text card) | What it can't do yet: online, full-size photos time out, the slanted edge's length is uncertain, and I haven't measured the grate step or the grip. {{The system files nothing and contacts no one.}} |
| 12 | 4:15–4:40 | The stack: left, right, underfoot, glare | Each problem sits at the limit. But they all land on the same stretch: no crossing on the left, grates on the right, the lane narrowing, and the winter sun in your eyes. |
| 13 | 4:40–5:00 | Close: three documents to request | Next: request the documents from the Traffic Department, the Metro construction office, and the district office. Thank you. |

## Open decisions
- #8: the old taper before repainting is not given (not established from my own photos; nothing from Street View is published).
- Project name.
- Voiceover: an external TTS would receive this text.
- #11: screenshot from the cloud after deployment, or from the local container, labelled as such.
