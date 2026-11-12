# Changelog

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
