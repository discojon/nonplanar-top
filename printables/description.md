<!-- Paste-ready text for the Printables listing. Title, summary and tags are at the top;
     the description (everything under "Description") goes in the main text box. -->

# Title
Nonplanar top surfaces for Core One INDX (PrusaSlicer post-processing script)

# Summary (one line)
Smooth, layer-line-free tops on gently curved prints: a PrusaSlicer script that reprints shallow top surfaces with Z moving while extruding.

# Tags
nonplanar, non-planar, core one, indx, prusaslicer, post-processing, top surface, script, gcode, smooth

# Category
3D Printers > Test Models (or Other)

# Licence (Printables field)
Creative Commons - Attribution - Share Alike (covers the coupons and images on the listing). The software in the zip is AGPL-3.0-or-later; see the note at the end of the description.

---

# Description

**Tired of contour lines on domed and gently sloped tops?** This PrusaSlicer post-processing script finds the shallow top surfaces in your print and reprints them as a smooth skin that follows the curve, with the nozzle moving up and down while it extrudes.

It is built for the **Prusa Core One with the INDX toolhead** and knows the toolhead's shape (nozzle, heater block, INDX body and part-cooling shroud), so it only smooths where nothing on the head can touch your part.

### How it works
1. You slice and export as usual. PrusaSlicer runs the script on the exported file.
2. The script rebuilds the smooth surface from the layer steps and picks the areas that are shallow enough and safe for the toolhead.
3. It removes the stair-stepped top layers there and adds two passes at the end of the print: a levelling pass that fills the steps, and a 0.2 mm finish pass that follows the surface.
4. **It simulates the whole converted file before writing it.** Toolhead clearance, coverage, retractions and feed rates must all pass, or nothing is converted and PrusaSlicer tells you why.

Works with plain and binary G-code, PrusaLink and USB.

**Source code, documentation and updates:** https://github.com/discojon/nonplanar-top

### What's in the download
- `nonplanar_top.py`: the script
- `nonplanar_top.ini`: settings
- `install_windows.bat`: installs the Python libraries and gives you the line to paste into PrusaSlicer
- `profiles/NONPLANAR_print_profile.ini`: ready-made print profile bundle
- `docs/`: full documentation
- three **test coupons** (dome, ramp, wave)

### Setup (about 10 minutes)
1. Install Python 3.10+ from python.org (tick *Add python.exe to PATH*).
2. Run `install_windows.bat`.
3. **Measure the gap between your nozzle tip and the lowest point of the fan shroud** (nozzle hot) and enter it in `nonplanar_top.ini`. This one number decides how much can be smoothed.
4. In PrusaSlicer (Expert mode), paste the line from the installer into *Print Settings > Output options > Post-processing scripts*.
5. Type `nonplanar` in *Print Settings > Notes* and save the profile under a new name. Only profiles with that word are converted.
6. To see the result, open the exported file with *File > G-code preview*.

### Limits
- Shallow surfaces only (default up to 12°, and the shroud limits how much a surface can rise within ~30 mm).
- Tall parts within about 45 mm block smoothing (the INDX body is only ~4 mm above the nozzle tip).
- The top must be printed with the last tool used.
- No sequential printing or spiral vase.
- Beta: start with the test coupons and watch the end of the print where the skin goes on.

### Licence and credits
The software is licensed under the **GNU AGPL v3.0 or later**; the test coupons and images are CC BY-SA 4.0.

- Toolhead clearance data measured from the reverse-engineered **INDX CAD by robertsamples** (github.com/robertsamples/INDX-CAD, CC BY-SA 4.0), based on **Prusa Research's INDX toolhead model** (CC BY-SA 4.0). These data tables remain CC BY-SA 4.0.
- Fan shroud shape measured from **Prusa Research's CORE_One_INDX_fan_shroud_r1** (Core One INDX printed parts).
- Binary G-code reading based on **Prusa Research's libbgcode** (AGPL-3.0), including a port of its **MeatPack** decoder (MeatPack by **Scott Mudge**); compression format **heatshrink** by **Scott Vokes / Atomic Object**.

Full list: CREDITS.md in the download. Not affiliated with Prusa Research.

Problems or suggestions: please open an issue at https://github.com/discojon/nonplanar-top/issues (attach `nonplanar_top_last.log`).
