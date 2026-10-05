"""
PLD chamber camera connector - parametric model for Blender 5.2

Run it from Blender's Scripting workspace (open this file, then Text > Run Script),
or from a terminal:   blender --python pld_camera_connector.py
Re-running the script rebuilds the model with the current parameter values.

Three parts, all built around the global X axis. The camera is on the left
(X = 0) and the PLD chamber is on the right:

  ChamberAdapter - mounts over the PLD chamber port and grips the camera tube
                   with 5/16"-24 set screws.
  CameraMount    - a bottom half-cylinder cradle the camera sits in, joined to a
                   full tube that slides into the ChamberAdapter. A lip (x5) at
                   its chamber end stops it pulling out of the adapter.
  CameraCover    - a top half-cylinder that covers the camera. Its tongue slides
                   into a groove in the end of the CameraMount tube.

All lengths are in millimetres and all angles in degrees. Names X1..X9, THETA1
and THETA2 match the labels on the hand sketch.
"""

import math

try:
    import bpy
    import bmesh
    from mathutils import Matrix
except ImportError:  # lets the profile math be checked outside Blender
    bpy = None


# =============================================================================
# PARAMETERS
# =============================================================================

# ---- Labelled on the sketch -------------------------------------------------
X1 = 24.0      # wall thickness: camera cradle/cover around the camera neck,
               # ChamberAdapter set-screw collar, cone and skirt
X2 = 88.0      # outer diameter of the CameraMount / CameraCover
X3 = 20.0      # length of the CameraCover tongue that slides into the groove
X4 = 14.0      # wall thickness of the CameraMount tube (and around the camera body)
X5 = 8.0       # radial height of the retaining lip at the chamber end of the tube
X6 = 60.0      # slant length of the ChamberAdapter cone (outer surface)
X7 = 56.0      # length of the ChamberAdapter skirt that fits over the chamber port
X8 = 178.0     # overall length of the CameraMount
X9 = 60.0      # ChamberAdapter neck length (front face to start of the cone)
THETA1 = 30.0  # taper from camera-neck bore to camera-body bore, from the axis
THETA2 = 45.0  # ChamberAdapter cone angle, from the axis

# ---- Not labelled on the sketch ---------------------------------------------
NECK_BORE_LENGTH = 30.0  # length of the narrow bore around the camera's neck
COVER_LENGTH = 68.0      # length of the CameraCover (= where the full tube starts)
TONGUE_THICKNESS = 5.0   # radial thickness of the cover's tongue
JOINT_CLEARANCE = 0.3    # gap around the tongue inside the groove
LIP_THICKNESS = 4.0      # axial thickness of the x5 retaining lip
TUBE_CLEARANCE = 0.5     # radial gap between the tube and the ChamberAdapter bore
COLLAR_LENGTH = 22.0     # length of the ChamberAdapter bore that grips the tube
INSERTION_DEPTH = 43.0   # how far the tube end sits inside the ChamberAdapter

# ---- Set screws: 5/16"-24 UNF -----------------------------------------------
INCH = 25.4
SCREW_HOLE_DIAMETER = 0.272 * INCH  # tap drill (letter I); 5/16 * INCH for clearance
SCREW_COUNT = 2                     # evenly spaced around the collar
SCREW_ANGLE = 90.0                  # angle of the first screw (90 = straight up)
SCREW_POSITION = None               # mm from adapter front face; None = collar middle

# ---- Display ----------------------------------------------------------------
SEGMENTS = 128           # facets around the axis (keep it a multiple of 4)
EXPLODE = 0.0            # mm to pull the parts apart for viewing
CUTAWAY = False          # remove the -Y half of every part to show the cross-section
COLOR = (0.5, 0.5, 0.5)  # matte grey
COLLECTION_NAME = "PLD Camera Connector"
MATERIAL_NAME = "Matte Grey"


# =============================================================================
# DERIVED GEOMETRY  (profiles are (radius, axial position) pairs)
# =============================================================================

def derived():
    """Every radius and axial position the parts are built from."""
    t1, t2 = math.radians(THETA1), math.radians(THETA2)
    g = {}

    # CameraMount / CameraCover, axial position measured from the camera end
    g["r_out"] = X2 / 2
    g["r_neck"] = g["r_out"] - X1
    g["r_bore"] = g["r_out"] - X4
    g["z_taper_end"] = NECK_BORE_LENGTH + (g["r_bore"] - g["r_neck"]) / math.tan(t1)
    r_mid = (g["r_bore"] + g["r_out"]) / 2
    g["tongue_in"] = r_mid - TONGUE_THICKNESS / 2
    g["tongue_out"] = r_mid + TONGUE_THICKNESS / 2
    g["groove_in"] = g["tongue_in"] - JOINT_CLEARANCE
    g["groove_out"] = g["tongue_out"] + JOINT_CLEARANCE
    g["groove_depth"] = X3 + JOINT_CLEARANCE

    # ChamberAdapter, axial position measured from its front (camera-side) face
    g["a_bore"] = g["r_out"] + TUBE_CLEARANCE
    g["a_out"] = g["a_bore"] + X1
    g["a_counterbore"] = g["r_out"] + X5 + TUBE_CLEARANCE
    g["a_skirt_out"] = g["a_out"] + X6 * math.sin(t2)
    g["a_skirt_in"] = g["a_skirt_out"] - X1
    g["z_skirt"] = X9 + X6 * math.cos(t2)
    g["z_end"] = g["z_skirt"] + X7

    # The inner cone surface is the outer one moved X1 into the material,
    # which is an axial shift of X1 / sin(theta2).
    def z_inner_cone(r):
        return X9 + (r - g["a_out"]) / math.tan(t2) + X1 / math.sin(t2)

    g["z_cone_in_start"] = z_inner_cone(g["a_counterbore"])
    g["z_cone_in_end"] = z_inner_cone(g["a_skirt_in"])
    g["z_screw"] = COLLAR_LENGTH / 2 if SCREW_POSITION is None else SCREW_POSITION
    return g


def check_dimensions(g):
    problems = []

    def need(ok, msg):
        if not ok:
            problems.append(msg)

    need(0 < THETA1 < 90 and 0 < THETA2 < 90, "THETA1 and THETA2 must be between 0 and 90")
    need(g["r_neck"] > 1, "X1 must be smaller than X2 / 2 (camera-neck bore would vanish)")
    need(X4 < X1, "X4 must be smaller than X1 (the camera-body bore is wider than the neck bore)")
    need(g["z_taper_end"] < COVER_LENGTH, "NECK_BORE_LENGTH plus the THETA1 taper must end before COVER_LENGTH")
    need(g["groove_in"] > g["r_bore"] + 0.5 and g["groove_out"] < g["r_out"] - 0.5,
         "TONGUE_THICKNESS + 2 * JOINT_CLEARANCE must fit inside the X4 wall with some material left")
    need(COVER_LENGTH + g["groove_depth"] < X8 - LIP_THICKNESS,
         "COVER_LENGTH + X3 must be shorter than X8 minus the lip")
    need(g["a_counterbore"] < g["a_out"] - 0.5, "X5 must be smaller than X1 (lip pocket breaks through the adapter wall)")
    need(COLLAR_LENGTH < X9, "COLLAR_LENGTH must be shorter than X9")
    need(SCREW_HOLE_DIAMETER < COLLAR_LENGTH, "screw hole is wider than the collar")
    need(INSERTION_DEPTH >= COLLAR_LENGTH + LIP_THICKNESS,
         "INSERTION_DEPTH must put the lip past the collar (>= COLLAR_LENGTH + LIP_THICKNESS)")
    need(INSERTION_DEPTH <= g["z_cone_in_start"],
         f"INSERTION_DEPTH must be <= {g['z_cone_in_start']:.1f} (where the inner cone starts)")
    need(g["z_cone_in_start"] > COLLAR_LENGTH, "inner cone starts inside the collar; increase X9 or reduce X1/X5")
    need(g["z_cone_in_end"] < g["z_end"], "X7 is too short for the cone wall thickness")
    need(INSERTION_DEPTH < X8 - COVER_LENGTH - g["groove_depth"],
         "the adapter would cover the cover/tube joint; reduce INSERTION_DEPTH or increase X8")
    if problems:
        raise ValueError("Dimension problems:\n  - " + "\n  - ".join(problems))


def adapter_profile(g):
    return [
        (g["a_bore"], 0.0),
        (g["a_out"], 0.0),
        (g["a_out"], X9),
        (g["a_skirt_out"], g["z_skirt"]),
        (g["a_skirt_out"], g["z_end"]),
        (g["a_skirt_in"], g["z_end"]),
        (g["a_skirt_in"], g["z_cone_in_end"]),
        (g["a_counterbore"], g["z_cone_in_start"]),
        (g["a_counterbore"], COLLAR_LENGTH),
        (g["a_bore"], COLLAR_LENGTH),
    ]


def mount_profile(g):
    """Full-length tube; the top half of the camera end is cut away afterwards."""
    return [
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], X8 - LIP_THICKNESS),
        (g["r_out"] + X5, X8 - LIP_THICKNESS),
        (g["r_out"] + X5, X8),
        (g["r_bore"], X8),
        (g["r_bore"], g["z_taper_end"]),
        (g["r_neck"], NECK_BORE_LENGTH),
    ]


def mount_cutter_profile(g):
    """Top-half region removed from the mount: the cover's space plus the groove."""
    r_in = g["r_neck"] / 2
    r_big = g["r_out"] + X5 + 1
    return [
        (r_in, -1.0),
        (r_big, -1.0),
        (r_big, COVER_LENGTH),
        (g["groove_out"], COVER_LENGTH),
        (g["groove_out"], COVER_LENGTH + g["groove_depth"]),
        (g["groove_in"], COVER_LENGTH + g["groove_depth"]),
        (g["groove_in"], COVER_LENGTH),
        (r_in, COVER_LENGTH),
    ]


def cover_profile(g):
    return [
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH + X3),
        (g["tongue_in"], COVER_LENGTH + X3),
        (g["tongue_in"], COVER_LENGTH),
        (g["r_bore"], COVER_LENGTH),
        (g["r_bore"], g["z_taper_end"]),
        (g["r_neck"], NECK_BORE_LENGTH),
    ]


# =============================================================================
# BLENDER HELPERS
# =============================================================================

def setup_units():
    units = bpy.context.scene.unit_settings
    units.system = 'METRIC'
    units.length_unit = 'MILLIMETERS'
    units.scale_length = 0.001  # 1 Blender unit = 1 mm
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.clip_start = 0.1
                    space.clip_end = 100000


def clean_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    for obj in list(coll.objects):
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    return coll


def finish_mesh(name, bm, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def revolve(name, profile, coll, start=0.0, sweep=360.0):
    """Spin a closed (radius, x) polygon around the X axis.
    Angle 0 is +Y and 90 is +Z, so start=0, sweep=180 gives the top half."""
    full = math.isclose(sweep, 360.0)
    steps = SEGMENTS if full else max(2, round(SEGMENTS * sweep / 360.0))
    rings = steps if full else steps + 1
    n = len(profile)

    bm = bmesh.new()
    verts = []
    for i in range(rings):
        a = math.radians(start + sweep * i / steps)
        ca, sa = math.cos(a), math.sin(a)
        verts.append([bm.verts.new((x, r * ca, r * sa)) for r, x in profile])
    for i in range(steps):
        ring, nxt = verts[i], verts[(i + 1) % rings]
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((ring[j], ring[k], nxt[k], nxt[j]))
    if not full:
        bm.faces.new(verts[0])
        bm.faces.new(verts[-1])
    return finish_mesh(name, bm, coll)


def boolean(target, cutter, operation='DIFFERENCE'):
    """Apply a boolean to target's mesh, then delete the cutter."""
    mod = target.modifiers.new("Boolean", 'BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = 'EXACT'
    depsgraph = bpy.context.evaluated_depsgraph_get()
    new_mesh = bpy.data.meshes.new_from_object(target.evaluated_get(depsgraph))
    target.modifiers.remove(mod)
    old_mesh = target.data
    target.data = new_mesh
    new_mesh.name = target.name
    bpy.data.meshes.remove(old_mesh)
    cutter_mesh = cutter.data
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(cutter_mesh)


def matte_grey():
    mat = bpy.data.materials.get(MATERIAL_NAME) or bpy.data.materials.new(MATERIAL_NAME)
    mat.diffuse_color = (*COLOR, 1.0)  # solid-mode viewport colour
    mat.roughness = 1.0
    mat.metallic = 0.0
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None) \
            or nodes.new('ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    settings = {"Base Color": (*COLOR, 1.0), "Roughness": 1.0, "Metallic": 0.0,
                "Specular IOR Level": 0.0}
    for socket, value in settings.items():
        if socket in bsdf.inputs:
            bsdf.inputs[socket].default_value = value
    return mat


def finish_object(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.data.shade_smooth()
    try:
        obj.data.set_sharp_from_angle(angle=math.radians(35))
    except AttributeError:
        pass


# =============================================================================
# PARTS
# =============================================================================

def build_chamber_adapter(g, coll):
    adapter = revolve("ChamberAdapter", adapter_profile(g), coll)
    if SCREW_COUNT > 0:
        bm = bmesh.new()
        r_mid = (g["a_bore"] + g["a_out"]) / 2
        depth = g["a_out"] - g["a_bore"] + 4
        for i in range(SCREW_COUNT):
            a = math.radians(SCREW_ANGLE + 360.0 * i / SCREW_COUNT)
            place = (Matrix.Translation((g["z_screw"], r_mid * math.cos(a), r_mid * math.sin(a)))
                     @ Matrix.Rotation(a - math.pi / 2, 4, 'X'))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=SCREW_HOLE_DIAMETER / 2,
                                  radius2=SCREW_HOLE_DIAMETER / 2, depth=depth, matrix=place)
        boolean(adapter, finish_mesh("ScrewHoles", bm, coll))
    return adapter


def build_camera_mount(g, coll):
    mount = revolve("CameraMount", mount_profile(g), coll)
    boolean(mount, revolve("CoverCutter", mount_cutter_profile(g), coll, start=0, sweep=180))
    return mount


def build_camera_cover(g, coll):
    return revolve("CameraCover", cover_profile(g), coll, start=0, sweep=180)


def cutaway(obj, coll):
    big = 10000.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -big / 2, 0))
                          @ Matrix.Diagonal((big, big, big, 1)))
    boolean(obj, finish_mesh("CutawayBox", bm, coll))


def main():
    g = derived()
    check_dimensions(g)
    setup_units()
    coll = clean_collection(COLLECTION_NAME)
    mat = matte_grey()

    adapter = build_chamber_adapter(g, coll)
    mount = build_camera_mount(g, coll)
    cover = build_camera_cover(g, coll)

    adapter.location.x = X8 - INSERTION_DEPTH + EXPLODE
    cover.location = (-EXPLODE, 0.0, EXPLODE)

    for obj in (adapter, mount, cover):
        if CUTAWAY:
            cutaway(obj, coll)
        finish_object(obj, mat)
    print(f"Built {COLLECTION_NAME}: adapter OD {2 * g['a_skirt_out']:.1f} mm, "
          f"overall length {X8 - INSERTION_DEPTH + g['z_end']:.1f} mm")


if __name__ == "__main__" and bpy is not None:
    main()
