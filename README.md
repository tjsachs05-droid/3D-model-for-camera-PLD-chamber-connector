# 3D model for camera PLD chamber connector

Parametric Blender models of mounts that hold a camera on a PLD chamber port. There are two designs, one script each. Both scripts require Blender 5.2.

In both, every part is revolved around the global X axis, with the camera on the left (X = 0) and the PLD chamber on the right. All dimensions are parameters at the top of each script, in mm (and degrees where angles are used). Every script has these options:
- `SCALE` resizes the whole model.
- Each part has its own matte color parameter.
- `CUTAWAY = True` shows a section view.
- `EXPLODE` pulls the parts apart.

To run a script, open it in the Scripting workspace and choose **Text > Run Script**, or run:

```
blender --python <script>.py
```

## Chamber connector: `pld_camera_connector.py`
- **ChamberAdapter**: fits over the PLD chamber port and grips the camera tube with 5/16"-24 set screws.
- **CameraMount**: a bottom half-cylinder cradle for the camera, joined to a full tube that slides into the adapter. A lip at its chamber end keeps it from pulling out.
- **CameraCover**: a top half-cylinder that covers the camera. Its tongue slides into a groove in the CameraMount tube.

`X1`–`X9`, `THETA1` and `THETA2` match the labels on the hand sketch. `section_preview.png` is a 2D cross-section drawn from the script's geometry.

## Model telescope: `model_telescope.py`
A telescoping version. Each tube has an inward lip at its camera end that catches the outward foot of the tube inside it.
- **Telescope Mount** (1): a camera cradle and tube with an outward foot at its chamber end.
- **Telescope Cover** (1.5): a half-cylinder cover with the same tongue-and-groove joint as the connector.
- **Telescope Segment N** (2): middle tubes, repeated `SEGMENT_COUNT` times. Each one is sized from the part inside it, so they nest.
- **Telescope Base** (3): the outermost tube, which sits against the chamber.

`EXTENSION` sets how far the telescope is extended, from 0 (collapsed) to 1 (fully extended). `telescope_preview.png` is a cutaway render.
