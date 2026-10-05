# 3D model for camera PLD chamber connector

Parametric Blender model of the connector that holds a camera on a PLD chamber port.

## Parts
All parts are revolved around the global X axis, with the camera on the left (X = 0) and the PLD chamber on the right.

- **ChamberAdapter**: fits over the PLD chamber port and grips the camera tube with 5/16"-24 set screws.
- **CameraMount**: a bottom half-cylinder cradle for the camera, joined to a full tube that slides into the adapter. A lip at its chamber end keeps it from pulling out.
- **CameraCover**: a top half-cylinder that covers the camera. Its tongue slides into a groove in the CameraMount tube.

## Usage
Requires Blender 5.2. Open `pld_camera_connector.py` in the Scripting workspace and choose **Text > Run Script**, or run:

```
blender --python pld_camera_connector.py
```

All dimensions are parameters at the top of the script. Lengths are in mm and angles in degrees. `X1`–`X9`, `THETA1` and `THETA2` match the labels on the hand sketch. `SCALE` resizes the whole model. Each part has its own matte color: `ADAPTER_COLOR`, `MOUNT_COLOR` and `COVER_COLOR`. `CUTAWAY = True` shows a section view, and `EXPLODE` pulls the parts apart.

`section_preview.png` is a 2D cross-section drawn from the script's geometry.
