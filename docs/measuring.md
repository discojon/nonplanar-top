# Measuring your toolhead

The tool knows the INDX toolhead's shape from its CAD model. One thing varies from printer to printer and decides how much of a surface can be smoothed: **how low the part-cooling fan shroud hangs**.

## Shroud height (`shroud_height_mm`)

This is the vertical gap between the **nozzle tip** and the **lowest point of the fan shroud**.

1. Heat the nozzle to printing temperature (the gap changes slightly when hot).
2. Measure the gap. Either:
   - lower the nozzle until it just touches a sheet of paper on the bed, note Z, then raise Z until the lowest point of the shroud just touches the paper and subtract; or
   - use feeler gauges or a caliper depth rod from the shroud's lowest point down to the nozzle tip level.
3. Round **down** to the nearest 0.1 mm and enter it in `nonplanar_top.ini`:

```ini
shroud_height_mm = 2.4
```

The default, 1.5 mm, is deliberately cautious. With the real (usually larger) number the tool can smooth more of a surface.

### Why it matters
While the nozzle prints the low edge of a dome, the shroud passes over the higher middle. The surface may not rise more than `shroud_height_mm - safety_margin_mm` within the shroud's reach (about 30 mm around the nozzle). The tool checks this everywhere and leaves areas with normal layers where it would be too close.

## Optional: shroud position
By default the tool assumes the lowest part of the shroud could be in any direction around the nozzle. That is safe whichever way it is mounted, but cautious. Directional modelling (using the screw axis height and its distance behind the nozzle) is planned; see the issue tracker.
