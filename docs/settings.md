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
| `finish_direction` | `auto` | Finish line direction: `auto` (along the region's long side), `x`, `y`, or an angle in degrees. The levelling pass runs at 90° to it. |
| `level_perimeter_speed` | `40` | mm/s |
| `level_infill_speed` | `60` | mm/s |
| `finish_perimeter_speed` | `35` | mm/s |
| `finish_infill_speed` | `50` | mm/s |
| `skin_accel` | `1500` | mm/s² while printing the skin (the previous value is restored afterwards). |
| `travel_lift_mm` | `0.6` | Height of travel moves above the skin. |
| `on_unsafe` | `error` | If a safety check fails: `error` stops the export and shows why; `skip` exports the file unchanged. |
| `debug_image` | `0` | `1` saves `nonplanar_top_last.png` (smoothed and excluded areas) next to the log. Needs `matplotlib`. |

Feeds are also capped so the Z axis never exceeds the printer's `machine_max_feedrate_z`.

## Print profile settings that matter

- **Top solid layers / minimum thickness:** keep at least about 0.7 mm. The tool removes up to roughly half a millimetre of the top and prints the skin on what remains.
- **Relative E distances** must be on (Prusa default).
- **Sequential printing** (one object at a time) and **spiral vase** are not supported; the script leaves those files unchanged.
- **Ironing:** turn it off for this profile; the skin replaces it.
