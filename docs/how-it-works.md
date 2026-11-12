# How it works

## 1. Read the file
PrusaSlicer runs the script on the exported G-code. Binary `.bgcode` files are decoded (including thumbnails and metadata) and the result is written back as plain G-code. The slicer settings embedded at the end of the file are read so the skin uses your filament, retraction and speed settings.

## 2. Map the print from above
Every extrusion is drawn onto a 0.1 mm grid, layer by layer, giving the height of the top of the print at every point and which tool and object printed it.

## 3. Rebuild the smooth surface
A layer with top height *z* is printed wherever the model surface is above that layer's slicing plane (its mid-height). So the boundary between two layer steps is a contour line of the real surface. The tool measures the distance from every point to the step boundary below and above it and interpolates between the two contours, then smooths very lightly.

- Chamfers and walls are not treated as contours.
- Tiny gaps between top-layer lines are filled first so they do not act as false contours.
- The result is kept within each step's possible height band.

On the test coupons the rebuilt surface is within about ±0.05 mm of the true model, compared with ±0.1 mm for the layer steps.

## 4. Choose regions
An area is smoothed when it:
- is a top surface (nothing printed above it),
- is not part of a steep edge, chamfer or wall,
- is no steeper than `max_slope_deg`,
- crosses at least `min_levels` layer steps,
- is printed with the tool the print ends on,
- and keeps the whole toolhead clear (next section).

## 5. Toolhead clearance
The toolhead is modelled as its lowest point at each distance from the nozzle, in any direction: nozzle flat and cone, heater block, INDX body and part-cooling shroud ([details](toolhead-model.md)). For every point of a region the tool works out the lowest the nozzle may go without any part of the head coming within `safety_margin_mm` of the print, including other objects and tall features nearby. Points where the skin would be lower than that are dropped.

This is repeated against the geometry that will actually remain after clipping until it converges.

## 6. Clip the planar layers
Inside each region, original extrusion above the skin's base is turned into non-extruding moves. Original retractions are kept; extra retractions are added around the removed stretches. Just outside a region, material is lowered only as far as the nozzle cone needs while printing the region's edge.

## 7. Print the skin
At the end of the print, before the end G-code:

1. **Levelling pass:** a perimeter and monotonic lines whose thickness varies from 0.1 to about 0.3 mm to fill the steps, ending 0.2 mm below the surface.
2. **Finish pass:** a perimeter and monotonic lines at 90° to the levelling pass, 0.2 mm thick, following the surface.

Moves are split every millimetre and Z follows the surface. Travel moves retract and lift above everything along the way.

## 8. Verify
The converted file is parsed again and simulated independently ([safety checks](safety-checks.md)). Only if everything passes is the file written.
