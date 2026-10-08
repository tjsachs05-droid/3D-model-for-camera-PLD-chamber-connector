# 3D model for camera PLD chamber connector

Parametric Blender models of mounts that hold a camera on a PLD chamber viewport. Both scripts require Blender 5.2.

In both, every part is revolved around the global X axis, with the camera on the left (X = 0) and the PLD chamber on the right. All dimensions are parameters at the top of each script. Every script has these options:
- `SCALE` resizes the whole model.
- Each part has its own matte color parameter.
- `CUTAWAY = True` shows a section view.
- `EXPLODE` pulls the parts apart.

To run a script, open it in the Scripting workspace and choose **Text > Run Script**, or run:

```
blender --python <script>.py
```

## Chamber connector: `pld_camera_connector.py`
This is the design being taken forward for 3D printing. Parameters are in inches. The model is built in millimetres, so exported files come out the right size for slicers, and Blender displays lengths in inches.

- **CameraMount**: a bottom half-cylinder cradle for the camera, joined to a full tube that slides into the adapter. A lip at its chamber end keeps it from pulling out.
- **CameraCover**: a top half-cylinder that covers the camera. Its tongue slides into a groove in the CameraMount tube.
- **ChamberAdapter**: grips the mount tube with set screws in its collar, then flares out to a face that sits on the viewport flange. An indent in that face fits around the protruding glass. Three prongs reach over the flange's side, each with a set screw that clamps onto it.
- **ChamberAdapter2**: the same adapter, set up for the alternate 6" viewport and placed below the assembly. It has its own `ADAPTER2_*` parameters. `ADAPTER2_GAP` sets the space between it and the assembly.

Every screw hole is sized to tap for 5/16"-24. Each one sits in a raised pad (`SCREW_PAD_DIAMETER`, `SCREW_PAD_THICKNESS`), so there's more plastic for the threads. The mount tube also gets a band (`JOINT_PAD_THICKNESS`) where the cover's tongue slides in, so the walls on either side of the groove aren't too thin.

The defaults fit an Ender-3 V2 (220 × 220 × 250 mm) with each part printed standing on end. The adapter is 9.75" tall including the prongs, and the mount is 9.75" long. `PRINTER_MAX_HEIGHT` and `PRINTER_BED_SIZE` make the script stop with an error if a part grows too big. Set them to `None` to skip the check.

The main dimensions are in their own section at the top of the script:
- `CAMERA_DIAMETER` (1.6") is the camera's neck.
- `FOCUS_DIAL_DIAMETER` (2") is the camera's focus dial.
- `VIEWPORT_DIAMETER` (8") is the raised viewport flange.
- `THICKNESS` (1/8") is the wall thickness of every part, including the prongs.

The glass is set by `GLASS_DIAMETER` and `RECESS_DEPTH`. `INSERTION_DEPTH` sets how far the mount sits in the adapter, which sets the camera-to-viewport distance. `section_preview.png` is a cutaway render.

### Printing
Each run of the script writes one STL per part to `stl/`: `CameraMount.stl`, `CameraCover.stl` and `ChamberAdapter.stl`. `EXPORT_FOLDER` and `EXPORT_PARTS` control this. Add `"ChamberAdapter2"` to `EXPORT_PARTS` to get the 6" adapter too.

The files are always whole parts, even when `CUTAWAY` is on. They're in millimetres, watertight, and already standing the way they should print:
- **CameraMount** stands on its lip end, which is a full ring on the bed, so the cover's groove opens upward. The only overhangs are two small ledges, and both print fine without support.
- **CameraCover** stands on its camera end and needs no supports.
- **ChamberAdapter** stands on its three prong tips. It needs support under its flange face, between the prongs, and a brim helps it stay stuck to the bed.

Print with at least 4 walls (perimeters) so the plastic around the screw holes is solid. Then drill the holes out with a letter-I (0.272") bit and cut the threads with a 5/16"-24 tap.

## Model telescope: `model_telescope.py`
An earlier telescoping design that isn't being taken forward. Its parameters are in mm. Each tube has an inward lip at its camera end that catches the outward foot of the tube inside it.
- **Telescope Mount** (1): a camera cradle and tube with an outward foot at its chamber end.
- **Telescope Cover** (1.5): a half-cylinder cover with the same tongue-and-groove joint as the connector.
- **Telescope Segment N** (2): middle tubes, repeated `SEGMENT_COUNT` times. Each one is sized from the part inside it, so they nest.
- **Telescope Base** (3): the outermost tube, which sits against the chamber.

`EXTENSION` sets how far the telescope is extended, from 0 (collapsed) to 1 (fully extended). `telescope_preview.png` is a cutaway render.
