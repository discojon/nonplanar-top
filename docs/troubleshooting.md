# Troubleshooting & FAQ

Every run writes `nonplanar_top_last.log` next to the script. Start there.

## Messages

**Nothing happened / the file looks unchanged.**
The print profile's Notes must contain the word `nonplanar` (or set `activate = always`). Check that the post-processing line is in the print profile you sliced with.

**"No changes made: no shallow top surfaces found"**
Nothing qualified: flat tops, steep surfaces, or areas too small. Try lowering `min_region_area_mm2`.

**"... skipped: flat (crosses only 1 layer)"**
Flat tops are left alone on purpose.

**"... toolhead/shroud clearance excluded N mm2"**
The shroud or toolhead would come too close: tall parts nearby, a surface rising too much within ~30 mm, or `shroud_height_mm` set low. Measure the shroud and enter the real value.

**"... its top is printed with T1 but the print ends on T0"**
The top surface must be printed with the last tool used.

**"NOT CONVERTED - safety check failed: ..."**
The converted file did not pass simulation, so nothing was changed. Set `on_unsafe = skip` to export unconverted, and please report the message with the log.

**"missing Python package"**
Run `py -m pip install numpy scipy shapely opencv-python`.

**PrusaSlicer says the post-processing script failed.**
The message shows the reason. If it says the file could not be found or opened, check both paths in the post-processing line and that they are in quotes.

## FAQ

**Will it work with binary G-code?**
Yes. The output is plain `.gcode` (PrusaSlicer renames it on export).

**Does it work with PrusaLink / Prusa Connect uploads?**
Yes. The script runs before the upload.

**How much longer does a print take?**
A few minutes on small parts (2–4 min on the test coupons), around 15 minutes on a large 250 mm part.

**Can I see where it smoothed?**
Set `debug_image = 1` (needs `pip install matplotlib`) and look at `nonplanar_top_last.png` next to the script.

**Other printers?**
The clearance model is specific to the Core One INDX toolhead and shroud. The code would work elsewhere with a different toolhead table.
