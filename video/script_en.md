# Video script (English, translated line by line from script_zh.md merged version)

Format: slide edit, English subtitles burned in, ≤ 5 min. Covers team, application, architecture, results.
No Google Street View imagery on any slide.

| # | Time | On screen | Subtitle |
|---|---|---|---|
| 1 | 0:00–0:15 | Title: 85 metres of County Road 116 | I ride this road every day. Before the repainting, you had to change lanes in a hurry. After it, you hit seven drain grates in a row, right where the asphalt dips. Roadworks never stop, but who measures the danger to riders? |
| 2 | 0:15–0:35 | Early-morning photo, grate 3 (`redline-gutter-kerb-P22.jpg`) | This is the right-hand side. The old red line sits at the edge of the asphalt. The new one is painted on the drain strip. The kerb is further out. |
| 3 | 0:35–0:55 | Solo — one rider, one smartphone | The team is just me: a rider who uses this road every day, with a smartphone. I'm not here to say who broke the rules. I turn what a rider feels into numbers anyone can check. |
| 4 | 0:55–1:25 | Schematic (`schematic-85m.png`) | In these 85 metres: 35 m of solid line where you can't change lanes, then 50 m where the painted island narrows the lane, and seven drain grates on your right. |
| 5 | 1:25–1:55 | Recognition: red line over grates (`red-line-over-grates.jpg`) | I used OpenCV to find the grates and the red line. In 16 out of 16 top-down photos, the new red line runs straight across a grate. |
| 6 | 1:55–2:15 | Rules card: §169, §183, Urban Road Standard §2 | The rules say a red line goes on the kerb, that it marks the outer edge of the road, and that a lane is whatever the markings enclose. So the new line puts the drain strip inside the road. |
| 7 | 2:15–2:40 | Card-as-ruler photo (grate 7) | My ruler is the red line itself: 10 cm wide by law. I checked it with a real card and measured 95 to 97 mm. The red line moved out by about 0.6 m. |
| 8 | 2:40–3:10 | Taper after repainting (`taper-2026-after-erasure.jpg`) + number card | How sharply does the lane close? At 30 km/h the rules ask for at least 5 to 1. Before the repainting it was about 4 to 5 to 1, right at the limit. Now it's about 12 to 1, which passes. The repainting made it better. |
| 9 | 3:10–3:30 | Withdrawn: why my 10 to 1 was wrong (`f40_picks.jpg`) | I first published 10 to 1. When I checked again, I found the program had picked the wrong lines, and the answer changed with image quality. I withdrew it. Now two different tools have to agree before I use a number. |
| 10 | 3:30–3:55 | Architecture (`architecture.png`) | How it works: upload one photo. It checks the photo shows a road, only reports a measurement if it holds across four versions of the image, and tells you which document to request next. |
| 11 | 3:55–4:15 | Result card: API response | It runs on AWS with OpenCV 5. It tells you what it measured, what it couldn't, and why. |
| 12 | 4:15–4:40 | The stack: left, right, underfoot, glare | Each problem on its own sits right at the limit. But they all land on the same 85 metres: no crossing on the left, grates on the right, the lane narrowing, and on winter mornings, the sun in your eyes. |
| 13 | 4:40–5:00 | Close: three documents to request | Next: request the documents from the Traffic Department, the Metro construction office, and the district office. Thank you. |

## Open decisions (same as the Chinese version)
- #8 "before repainting 4–5 to 1" was measured on Google Street View: keep or drop.
- Project name.
- Voiceover: an external TTS would receive this text.
- #11: screenshot from the cloud after deployment, or from the local container, labelled as such.
