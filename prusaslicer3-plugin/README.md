# nonplanar_top plugin for PrusaSlicer 3

Plugin bundle for PrusaSlicer 3.0 (alpha14 or newer). It adds:

- **Print Goals > Nonplanar top surfaces**: at least 5 top solid layers and 0.7 mm top shell, ironing off.
- **Plugins > Nonplanar top > Add test coupons**: the dome, ramp and wave test coupons.

The smoothing itself is done by the `nonplanar_top` post-processing script; PrusaSlicer 3 plugins cannot change G-code. You still need the post-processing line and `nonplanar` in *Print Settings > Notes*.

**Install:** *Plugins > Show User Plugins Folder*, copy the `io.github.discojon.nonplanar-top` folder there, then *Plugins > Rescan Plugins*.

Details: [docs/prusaslicer-3.md](../docs/prusaslicer-3.md). Licence: AGPL-3.0-or-later (the coupon STLs are CC BY-SA 4.0).
