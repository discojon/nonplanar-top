# Limitations

- **Shallow surfaces only.** Up to `max_slope_deg` (12° default), and in practice limited by the fan shroud: the surface cannot rise more than about `shroud_height_mm - safety_margin_mm` within roughly 30 mm of any point being smoothed.
- **Tall parts nearby block smoothing.** The INDX body is only about 4 mm above the nozzle tip out to about 46 mm from it. Anything much taller within that distance stops the skin.
- **One tool.** The top must be printed with the tool the print ends on.
- **No sequential printing or spiral vase.**
- **Region edges in the middle of a slope** (where clearance cut a region short) show a small step between smooth and layered.
- **Small lowered rim around regions.** Just outside a region the tops of nearby lines are lowered slightly so the nozzle cone clears them.
- **Preview.** PrusaSlicer's preview shows the file before conversion; use File > G-code preview on the exported file. The printer's thumbnail and remaining-time estimate are from before conversion (the skin usually adds a few minutes on small parts and around 15 minutes on large ones).
- **Built for the Core One INDX.** Other printers need their own toolhead model.
- **Surface is rebuilt from the layers,** not taken from your model; expect about ±0.05 mm.
