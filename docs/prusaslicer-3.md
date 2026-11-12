# PrusaSlicer 3

PrusaSlicer 3.0 is in alpha (tested with **3.0.0-alpha14**). `nonplanar_top` works with it the same way as with 2.x, and there is a small plugin that sets up a plate for it.

## What works

- **The post-processing script.** PrusaSlicer 3 keeps *Print Settings > Output options > Post-processing scripts*. G-code sliced by 3.0.0-alpha14 converts and passes every check, the same as files from 2.9. Set it up exactly as in [Installation](installation.md): the post-processing line, and `nonplanar` in *Print Settings > Notes*.
- **Profiles are separate.** The alphas keep their settings in their own folder (`PrusaSlicer3-dev`), so the print profile from 2.x has to be set up again in 3.

## The plugin

PrusaSlicer 3 adds Lua plugins. The plugin bundle in `prusaslicer3-plugin/` adds:

| | Where | What it does |
|---|---|---|
| **Nonplanar top surfaces** | Print sidebar > *Print Goals* | Makes sure the plate has at least 5 top solid layers and 0.7 mm of top shell (both adjustable), and turns ironing off. |
| **Add test coupons** | *Plugins > Nonplanar top* | Adds the dome, ramp and wave coupons (one, or all three spaced so the shroud clears its neighbours) and raises the top layers on the plate if needed. |

### What the plugin cannot do (yet)

PrusaSlicer 3 plugins run in a sandbox: they can add objects to the plate and change some print settings, but they **cannot read or change G-code, run other programs, or set text settings** such as *Notes* and *Post-processing scripts*. The smoothing itself therefore still runs as the post-processing script, and the two text settings have to be entered once by hand.

Prusa has said more plugin types are planned. If a later version lets plugins work on toolpaths or G-code, the conversion can move into the plugin.

### Install

1. In PrusaSlicer 3: **Plugins > Show User Plugins Folder**.
2. Copy the whole `io.github.discojon.nonplanar-top` folder (from the download, inside `prusaslicer3-plugin`) into that folder.
3. **Plugins > Rescan Plugins**.

Remove it by deleting the folder and rescanning.

## Viewing the result

PrusaSlicer 3.0 does not have the stand-alone G-code viewer yet, and its preview shows the toolpaths before the script ran. To look at the converted file, open it in PrusaSlicer 2.9 (*File > G-code preview*) or another G-code viewer.

## Notes

- The plugin API is experimental and may change between alphas. The bundle declares `3.0.0-alpha14` as its minimum version.
- The plugin has been checked against the API documentation and PrusaSlicer's manifest validator, and its logic tested outside the slicer. Please report anything that does not work in the PrusaSlicer 3 interface.
