# Printables publishing checklist

## Before publishing
- [ ] Measure your shroud height and print all three test coupons with the nonplanar profile.
- [ ] Take photos of a normal and a nonplanar coupon side by side, under a raking light. Real photos matter far more on Printables than renders.
- [ ] Optional: slice the coupons in PrusaSlicer with the nonplanar profile and keep the G-code to upload as print files.

## Upload
- **Model files:** `samples/coupon_dome_50mm.stl`, `samples/coupon_ramp_2deg.stl`, `samples/coupon_wave_80mm.stl`
- **Other files:** `nonplanar_top-0.2.0.zip` (from the GitHub release, or build it with `tools/make_release.py`)
- **Images:** your photos first, then `docs/images/coupon_dome_50mm_before_after.png`, `coupon_wave_80mm_before_after.png`, `coupon_dome_50mm_profile.png`, `samples/example_output/coupon_dome_50mm_regions.png`
- **Text:** title, summary, tags, licence and description from `description.md`

## Notes
- Link the source: https://github.com/discojon/nonplanar-top
- Licence field: Creative Commons - Attribution - Share Alike. The software itself is AGPL-3.0 (stated in the description and in the zip).
- Credit the INDX CAD (robertsamples) and Prusa Research in the description; the text in `description.md` already does.
