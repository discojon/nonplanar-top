# Safety checks

After converting, the tool reads its own output back and simulates it. The file is written only if all of these pass. Otherwise PrusaSlicer shows the reason (or, with `on_unsafe = skip`, the file is exported unchanged).

| Check | Limit |
|---|---|
| **Toolhead clearance while printing the skin**: nozzle cone, heater block, INDX body and shroud against everything printed so far (both passes separately) | must clear the safety margin (0.02 mm numerical tolerance) |
| **Travel moves over the skin** against the toolhead and the material underneath | same |
| **Nozzle against the layers below the skin** | at most 0.15 mm |
| **Coverage**: both skin passes must cover the region | at least 98.5 % each |
| **Retractions**: no extrusion while retracted beyond what the original file had; no over-retraction | |
| **Feed rates**: no new feed rate below 100 mm/min or above 60 000 mm/min | |
| **Height**: the skin never goes above the original top of the print | |
| **Filament balance**: skin filament vs. removed filament | between 0.6 and 1.5 |

Numbers from each run are in `nonplanar_top_last.log`.

## What is not checked
- Collisions with parts of the printer other than the toolhead and shroud.
- Whether your printer's actual shroud height matches `shroud_height_mm`. Measure it.
- Print quality (flow, cooling, adhesion of the skin). Print a test coupon first.
