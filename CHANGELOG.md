# Changelog

## 0.4.0 - 2026-11-12
- PrusaSlicer 3 support: checked with 3.0.0-alpha14 output (the post-processing script works unchanged).
- New PrusaSlicer 3 plugin (`prusaslicer3-plugin/`): a *Nonplanar top surfaces* print goal (5 top layers, 0.7 mm top shell, no ironing) and a command that adds the test coupons. The smoothing still runs as the post-processing script, because PrusaSlicer 3 plugins cannot change G-code yet.

## 0.3.0 - 2026-11-12
- The skin now uses the print profile's line widths, speeds and accelerations: perimeter and solid infill settings for the levelling pass, external perimeter and top solid infill settings for the finish pass. Each can still be overridden in `nonplanar_top.ini` or Notes.
- The finish pass runs at the profile's *Fill angle* by default (`finish_direction = profile`); `auto` keeps the old behaviour.
- The skin respects the filament's *Max volumetric speed*, so thick parts of the levelling pass slow down instead of under-extruding.
- If you keep an old `nonplanar_top.ini`, its fixed speeds still override the profile; change them to `profile` to use the new behaviour.

## 0.2.1 - 2026-11-12
- Licence changed to AGPL-3.0-or-later (the `.bgcode` reader ports code from Prusa's AGPL-licensed libbgcode).
- Toolhead data tables are marked and licensed separately under CC BY-SA 4.0, as required by their source.
- Added CREDITS.md and attribution notes for INDX-CAD, Prusa Research (INDX model, fan shroud, libbgcode), MeatPack and heatshrink.
- Fixed the face orientation of the test coupon STLs (PrusaSlicer was repairing them on import).
- Added `samples/nonplanar_top_test_coupons.3mf`, a PrusaSlicer project with the three coupons and the nonplanar print profile.

## 0.2.0 - 2026-11-12
- Fixed: tiny gaps between top-layer lines were read as height contours and could raise the skin by up to 0.15 mm on flat areas next to slopes.
- Fixed: smoothing could lift flat areas next to a slope; the smoothed surface now stays within 0.04 mm of the interpolated one and inside each layer step's height band.
- Fixed: a seam in the step-width estimate left a faint diagonal line on some flat areas.
- Region selection keeps an extra 0.02 mm of toolhead clearance so verification never lands on its limit.
- Added test coupons, documentation, Windows installer and PrusaSlicer profile bundle.

## 0.1.0 - 2026-11-12
- First version: surface reconstruction, region selection with INDX toolhead and shroud clearance, planar clipping, two-pass skin, full re-simulation before writing, `.bgcode` input, PrusaSlicer post-processing integration.
