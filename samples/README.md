# Samples

## Test coupons
Small parts for trying nonplanar_top before using it on real prints. All three convert at the default settings (`shroud_height_mm = 1.5`). See [docs/test-coupons.md](../docs/test-coupons.md).

| File | Size | Surface |
|---|---|---|
| `coupon_dome_50mm.stl` | 50 × 50 × 3.2 mm | spherical dome, 1.2 mm rise |
| `coupon_ramp_2deg.stl` | 60 × 25 × 4.1 mm | flat 2° ramp |
| `coupon_wave_80mm.stl` | 80 × 40 × 3.6 mm | gentle wave, ±0.6 mm |

`nonplanar_top_test_coupons.3mf` is a ready PrusaSlicer project with all three coupons on the plate and the **0.20mm NONPLANAR @COREONEINDX HF0.4** print profile (Prusa's stock 0.20mm Balanced plus `nonplanar` in Notes, 5 top layers, no ironing), on the stock **Prusa CORE One INDX 8T HF0.4** printer profile with Prusament PLA. Add your own post-processing line (see installation) before slicing.

There are no pre-sliced G-code files because start G-code depends on your printer and firmware.

## Example output
`example_output/` holds the log and region map from converting the dome coupon:

- `coupon_dome_50mm.log`: what was found, removed and added, and every verification number
- `coupon_dome_50mm_regions.png`: blue outline = smoothed region, red = left as layers because the shroud would come too close (the flat corners sit right next to the higher dome)
