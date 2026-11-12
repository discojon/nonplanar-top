# Samples

## Test coupons
Small parts for trying nonplanar_top before using it on real prints. All three convert at the default settings (`shroud_height_mm = 1.5`). See [docs/test-coupons.md](../docs/test-coupons.md).

| File | Size | Surface |
|---|---|---|
| `coupon_dome_50mm.stl` | 50 × 50 × 3.2 mm | spherical dome, 1.2 mm rise |
| `coupon_ramp_2deg.stl` | 60 × 25 × 4.1 mm | flat 2° ramp |
| `coupon_wave_80mm.stl` | 80 × 40 × 3.6 mm | gentle wave, ±0.6 mm |

Slice them with your nonplanar print profile; there are no pre-sliced G-code files because start G-code depends on your printer and firmware.

## Example output
`example_output/` holds the log and region map from converting the dome coupon:

- `coupon_dome_50mm.log`: what was found, removed and added, and every verification number
- `coupon_dome_50mm_regions.png`: blue outline = smoothed region, red = left as layers because the shroud would come too close (the flat corners sit right next to the higher dome)
