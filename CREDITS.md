# Credits and third-party material

nonplanar_top is licensed under the **GNU Affero General Public License v3.0 or later** (see [LICENSE](LICENSE)), except for the toolhead data tables noted below.

## Toolhead geometry (CC BY-SA 4.0)

The clearance tables `INDX_FINE`, `INDX_COARSE` and `SHROUD_REL` in `nonplanar_top.py` are licensed under **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**, not the AGPL. They are marked in the code with `BEGIN/END CC BY-SA 4.0 DATA`.

| Source | Author | Licence | Used for | Changes |
|---|---|---|---|---|
| [INDX-CAD](https://github.com/robertsamples/INDX-CAD) | robertsamples | CC BY-SA 4.0 | INDX toolhead shape (`INDX_FINE`, `INDX_COARSE`) | STEP assembly meshed and reduced to the lowest point at each distance from the nozzle |
| [INDX toolhead model](https://www.printables.com/model/1761468-indx-toolhead) (since removed from Printables; archived in INDX-CAD) | Prusa Research | CC BY-SA 4.0 | Source of the INDX-CAD reverse engineering | Indirect, via INDX-CAD |
| `CORE_One_INDX_fan_shroud_r1` from [Core One INDX printed parts](https://www.printables.com/model/1758233-core-one-indx-printed-parts) | Prusa Research | See the Printables page | Fan shroud shape (`SHROUD_REL`) | Reduced to the lowest point at each distance from its outlet centre, relative to its own lowest point; 3 mm position uncertainty applied |

## Binary G-code reading

| Source | Author | Licence | Used for |
|---|---|---|---|
| [libbgcode](https://github.com/prusa3d/libbgcode) | Prusa Research | AGPL-3.0 | `.bgcode` file layout (specification). `meatpack_decode` is a Python port of libbgcode's MeatPack decoder (`src/LibBGCode/binarize/meatpack.cpp`). |
| [MeatPack](https://github.com/scottmudge/Prusa-Firmware-MeatPack) | Scott Mudge | see project | The G-code packing format decoded by `meatpack_decode` |
| [heatshrink](https://github.com/atomicobject/heatshrink) | Scott Vokes / Atomic Object | ISC | The compression format; `_heatshrink_py` is an independent implementation of its decoder. The optional `heatshrink2` package is used instead when installed. |

## Runtime libraries (installed separately, not included)

| Library | Licence |
|---|---|
| [NumPy](https://numpy.org) | BSD-3-Clause |
| [SciPy](https://scipy.org) | BSD-3-Clause |
| [Shapely](https://github.com/shapely/shapely) | BSD-3-Clause |
| [OpenCV (opencv-python)](https://github.com/opencv/opencv-python) | Apache-2.0 / MIT |
| [Matplotlib](https://matplotlib.org) (optional) | Matplotlib licence (PSF-style) |
| [heatshrink2](https://github.com/eerimoq/pyheatshrink) (optional) | ISC |

## Original work

The surface reconstruction, region selection, clipping, skin generation and verification code, the test coupons, documentation, images and installer are original to this project.

Not affiliated with or endorsed by Prusa Research.
