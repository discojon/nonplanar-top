# Settings

Settings live in `nonplanar_top.ini`, next to the script. Any setting can be overridden for one print profile by adding a line to **Print Settings > Notes**:

```
nonplanar
nonplanar_top: max_slope_deg=8, finish_direction=y
```

On the command line, use `--set key=value`.

| Setting | Default | What it does |
|---|---|---|
| `activate` | `notes` | `notes`: only convert when the print profile's Notes contain `nonplanar`. `always`: convert every export. |
| `shroud_height_mm` | `1.5` | Lowest point of the fan shroud above the nozzle tip. **Measure it** ([how](measuring.md)). |
| `safety_margin_mm` | `0.3` | Extra clearance kept between the toolhead/shroud and the print (not the nozzle tip). |
| `plow_tolerance_mm` | `0.08` | How far the flat face of the nozzle may iron into the surface right beside it. |
| `max_slope_deg` | `12` | Steepest surface that gets smoothed. Steeper areas keep normal layers. |
| `min_region_area_mm2` | `20` | Smallest area worth smoothing. |
| `min_levels` | `3` | A surface must cross at least this many layer steps (flat tops are left alone). |
| `edge_inset_mm` | `0.0` | Gap kept from vertical walls and hole edges. `0` lets the skin run to the edge. |
| `finish_layer_mm` | `0.2` | Thickness of the finish pass. |
| `min_level_layer_mm` | `0.1` | Thinnest allowed levelling pass. |
| `finish_direction` | `profile` | Finish line direction (monotonic lines): `profile` (the print profile's *Fill angle*), `auto` (along the region's long side), `x`, `y`, or an angle in degrees. The levelling pass runs at 90° to it. |
| `skin_line_width` | `profile` | Line width in mm for all skin lines. `profile`: see below. |
| `level_perimeter_speed` | `profile` | mm/s. `profile` = *Perimeters* speed |
| `level_infill_speed` | `profile` | mm/s. `profile` = *Solid infill* speed |
| `finish_perimeter_speed` | `profile` | mm/s. `profile` = *External perimeters* speed |
| `finish_infill_speed` | `profile` | mm/s. `profile` = *Top solid infill* speed |
| `skin_accel` | `profile` | mm/s² for all skin moves. `profile` = the matching acceleration per line type (the previous value is restored afterwards). |

### Skin settings taken from the print profile

With `profile` (the default), the skin uses the settings PrusaSlicer would use for the same kind of line, resolved the same way (percentages, and `0` meaning "use the default"):

| | Levelling pass | Finish pass |
|---|---|---|
| Outline loop | *Perimeters*: width, speed, acceleration | *External perimeters*: width, speed, acceleration |
| Lines | *Solid infill*: width, speed, acceleration | *Top solid infill*: width, speed, acceleration |
| Direction | *Fill angle* + 90° | *Fill angle* |

The lines are always monotonic; other *Top fill pattern* choices are noted in the log and ignored. Speeds are further limited by the filament's *Max volumetric speed* (the levelling pass can be up to about 1 mm thick, so it often runs slower than the profile speed) and by the printer's maximum Z speed on slopes. Accelerations are capped at the printer's maximum.
| `travel_lift_mm` | `0.6` | Height of travel moves above the skin. |
| `on_unsafe` | `error` | If a safety check fails: `error` stops the export and shows why; `skip` exports the file unchanged. |
| `debug_image` | `0` | `1` saves `nonplanar_top_last.png` (smoothed and excluded areas) next to the log. Needs `matplotlib`. |

Feeds are also capped so the Z axis never exceeds the printer's `machine_max_feedrate_z`.

## Print profile settings that matter

- **Top solid layers / minimum thickness:** keep at least about 0.7 mm. The tool removes up to roughly half a millimetre of the top and prints the skin on what remains.
- **Relative E distances** must be on (Prusa default).
- **Sequential printing** (one object at a time) and **spiral vase** are not supported; the script leaves those files unchanged.
- **Ironing:** turn it off for this profile; the skin replaces it.
