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

Every screw hole is sized to tap for 5/16"-24.

The main dimensions are in their own section at the top of the script:
- `CAMERA_DIAMETER` (1.6") is the camera's neck.
- `FOCUS_DIAL_DIAMETER` (2") is the camera's focus dial.
- `VIEWPORT_DIAMETER` (8") is the raised viewport flange.
- `THICKNESS` (3/16") is the wall thickness of every part, including the prongs.

The glass is set by `GLASS_DIAMETER` and `RECESS_DEPTH`. `INSERTION_DEPTH` sets how far the mount sits in the adapter, which sets the camera-to-viewport distance. `section_preview.png` is a cutaway render.

## Model telescope: `model_telescope.py`
An earlier telescoping design that isn't being taken forward. Its parameters are in mm. Each tube has an inward lip at its camera end that catches the outward foot of the tube inside it.
- **Telescope Mount** (1): a camera cradle and tube with an outward foot at its chamber end.
- **Telescope Cover** (1.5): a half-cylinder cover with the same tongue-and-groove joint as the connector.
- **Telescope Segment N** (2): middle tubes, repeated `SEGMENT_COUNT` times. Each one is sized from the part inside it, so they nest.
- **Telescope Base** (3): the outermost tube, which sits against the chamber.

`EXTENSION` sets how far the telescope is extended, from 0 (collapsed) to 1 (fully extended). `telescope_preview.png` is a cutaway render.
