# Toolhead model

To keep the head clear of the print, the tool needs to know how low each part of the toolhead hangs at each distance from the nozzle.

## Sources
- **INDX toolhead:** measured from the reverse-engineered [INDX CAD](https://github.com/robertsamples/INDX-CAD) by robertsamples ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)), based on Prusa Research's [INDX toolhead model](https://www.printables.com/model/1761468-indx-toolhead) (CC BY-SA 4.0). The STEP assembly was meshed and, for every distance from the nozzle axis, the lowest point above the nozzle tip was recorded.
- **Part-cooling shroud:** measured from Prusa's `CORE_One_INDX_fan_shroud_r1` part ([Core One INDX printed parts](https://www.printables.com/model/1758233-core-one-indx-printed-parts)), relative to its own lowest point. Its height above the nozzle tip is `shroud_height_mm`, which you measure ([how](measuring.md)).

## Key numbers (above the nozzle tip)
| Distance from nozzle | Lowest part | Height |
|---|---|---|
| 0 – 0.6 mm | nozzle flat | 0 |
| 0.6 – 2.2 mm | nozzle cone (~47°) | 0.15 – 1.75 mm |
| 2.2 – 3.4 mm | heater sock | 2.66 mm |
| 3.4 – 6 mm | heater / tool body | 2.8 – 3.8 mm |
| ~6 – 31 mm | tool shell / shroud | 3.8 – 9.8 mm, or the shroud ring (18–28 mm) at `shroud_height_mm` |
| ~38 – 46 mm | INDX body (side shells) | about 4.2 mm |

## Conservative choices
- Each value is the lowest point **in any direction** at that distance, so the model holds whichever way the shroud faces.
- The shroud profile allows 3 mm of uncertainty in its position.
- The envelope is made non-decreasing outward from the nozzle.
- `safety_margin_mm` (0.3 mm) is added to everything except the nozzle tip and cone.

The tables are `INDX_FINE`, `INDX_COARSE` and `SHROUD_REL` in `nonplanar_top.py`. Because they are derived from CC BY-SA 4.0 material, they are licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), separately from the AGPL-licensed program. See [CREDITS.md](../CREDITS.md).
