"""
PLD chamber camera connector - parametric model for Blender 5.2

Run it from Blender's Scripting workspace (open this file, then Text > Run Script),
or from a terminal:   blender --python pld_camera_connector.py
Re-running the script rebuilds the model with the current parameter values.

Three parts, all built around the global X axis. The camera is on the left
(X = 0) and the PLD chamber is on the right:

  ChamberAdapter - fits over the PLD chamber viewport and grips the camera tube
                   with 5/16"-24 set screws.
  CameraMount    - a bottom half-cylinder cradle the camera sits in, joined to a
                   full tube that slides into the ChamberAdapter. A lip at its
                   chamber end stops it pulling out of the adapter.
  CameraCover    - a top half-cylinder that covers the camera. Its tongue slides
                   into a groove in the end of the CameraMount tube.

A fourth, separate part sits below the assembly:

  ChamberAdapter2 - a second adapter of the same design with its own ADAPTER2_*
                    parameters, so a variant can be tried side by side.

All lengths are in millimetres and all angles in degrees.

Labels on the hand sketch -> parameters:
  x1 -> THICKNESS        x2 -> CAMERA_DIAMETER + 2 * THICKNESS (mount outside diameter)
  x3 -> TONGUE_LENGTH    x4 -> TUBE_WALL
  x5 -> LIP_HEIGHT       x6 -> set by VIEWPORT_DIAMETER (cone slant length)
  x7 -> SKIRT_LENGTH     x8 -> MOUNT_LENGTH
  x9 -> CONE_START       theta1 -> NECK_TAPER_ANGLE    theta2 -> CONE_ANGLE
"""

import math

try:
    import bpy
    import bmesh
    from mathutils import Matrix
except ImportError:  # lets the profile math be checked outside Blender
    bpy = None


# =============================================================================
# MAIN DIMENSIONS
# =============================================================================

CAMERA_DIAMETER = 42.0     # bore that holds the camera's neck, at the camera end
VIEWPORT_DIAMETER = 172.0  # PLD chamber viewport the adapter skirt fits over
                           # (= inside diameter of the skirt)
THICKNESS = 15.0           # wall thickness of the cradle/cover around the camera's
                           # neck and of the ChamberAdapter collar, cone and skirt


# =============================================================================
# OTHER PARAMETERS
# =============================================================================

# ---- CameraMount and CameraCover --------------------------------------------
MOUNT_LENGTH = 250.0     # overall length of the CameraMount
TUBE_WALL = 10.0         # wall thickness of the mount tube and around the camera body
NECK_BORE_LENGTH = 30.0  # length of the CAMERA_DIAMETER bore at the camera end
NECK_TAPER_ANGLE = 65.0  # taper from that bore out to the camera-body bore, from the axis
LIP_HEIGHT = 5.0         # radial height of the retaining lip at the chamber end of the tube
LIP_THICKNESS = 10.0     # axial thickness of that lip
COVER_LENGTH = 68.0      # length of the CameraCover (= where the full tube starts)
TONGUE_LENGTH = 33.3     # length of the cover's tongue that slides into the groove
TONGUE_THICKNESS = 5.0   # radial thickness of the tongue
JOINT_CLEARANCE = 0.3    # gap around the tongue inside the groove

# ---- ChamberAdapter ---------------------------------------------------------
CONE_START = 150.0       # front face to where the cone starts
CONE_ANGLE = 45.0        # cone angle, from the axis
SKIRT_LENGTH = 56.0      # length of the skirt that fits over the viewport
TUBE_CLEARANCE = 0.5     # radial gap between the mount tube and the adapter bore
COLLAR_LENGTH = 22.0     # length of the adapter bore that grips the tube
INSERTION_DEPTH = 43.0   # how far the tube end sits inside the adapter

# ---- Set screws: 5/16"-24 UNF -----------------------------------------------
INCH = 25.4
SCREW_HOLE_DIAMETER = 0.272 * INCH  # tap drill (letter I); 5/16 * INCH for clearance
SCREW_COUNT = 2                     # evenly spaced around the collar
SCREW_ANGLE = 90.0                  # angle of the first screw (90 = straight up)
SCREW_POSITION = None               # mm from adapter front face; None = collar middle

# ---- ChamberAdapter2: separate adapter placed below the assembly ------------
# Each one means the same as the ChamberAdapter parameter without the prefix.
ADAPTER2_CAMERA_DIAMETER = 42.0     # with ADAPTER2_THICKNESS, sets the tube size it fits
ADAPTER2_VIEWPORT_DIAMETER = 172.0
ADAPTER2_THICKNESS = 15.0
ADAPTER2_LIP_HEIGHT = 5.0
ADAPTER2_CONE_START = 150.0
ADAPTER2_CONE_ANGLE = 45.0
ADAPTER2_SKIRT_LENGTH = 56.0
ADAPTER2_TUBE_CLEARANCE = 0.5
ADAPTER2_COLLAR_LENGTH = 22.0
ADAPTER2_SCREW_HOLE_DIAMETER = 0.272 * INCH
ADAPTER2_SCREW_COUNT = 2
ADAPTER2_SCREW_ANGLE = 90.0
ADAPTER2_SCREW_POSITION = None
ADAPTER2_GAP = 20.0                 # space between the assembly and ChamberAdapter2

# ---- Size -------------------------------------------------------------------
SCALE = 1.0              # uniform scale for the whole finished model; the screw
                         # holes and clearances scale with it

# ---- Display ----------------------------------------------------------------
SEGMENTS = 128           # facets around the axis (keep it a multiple of 4)
EXPLODE = 0.0            # mm (after scaling) to pull the parts apart for viewing
CUTAWAY = True           # remove the -Y half of every part to show the cross-section
ADAPTER_COLOR = (0.50, 0.50, 0.50)  # ChamberAdapter: matte grey
MOUNT_COLOR = (0.20, 0.35, 0.65)    # CameraMount: matte blue
COVER_COLOR = (0.80, 0.45, 0.15)    # CameraCover: matte orange
ADAPTER2_COLOR = (0.50, 0.50, 0.50) # ChamberAdapter2: matte grey
COLLECTION_NAME = "PLD Camera Connector"


# =============================================================================
# DERIVED GEOMETRY  (profiles are (radius, axial position) pairs)
# =============================================================================

ADAPTER_KEYS = ("CAMERA_DIAMETER", "VIEWPORT_DIAMETER", "THICKNESS", "LIP_HEIGHT", "CONE_START",
                "CONE_ANGLE", "SKIRT_LENGTH", "TUBE_CLEARANCE", "COLLAR_LENGTH",
                "SCREW_HOLE_DIAMETER", "SCREW_COUNT", "SCREW_ANGLE", "SCREW_POSITION")


def adapter_geometry(prefix=""):
    """Radii and axial positions (from the front face) of an adapter built from
    the parameters prefix + CAMERA_DIAMETER, ... (see ADAPTER_KEYS)."""
    p = {k: globals()[prefix + k] for k in ADAPTER_KEYS}
    if not 0 < p["CONE_ANGLE"] < 90:
        raise ValueError(f"{prefix}CONE_ANGLE must be between 0 and 90")
    t = math.radians(p["CONE_ANGLE"])
    a = {"prefix": prefix, "p": p}
    r_tube = p["CAMERA_DIAMETER"] / 2 + p["THICKNESS"]  # outside of the camera tube
    a["bore"] = r_tube + p["TUBE_CLEARANCE"]
    a["out"] = a["bore"] + p["THICKNESS"]
    a["counterbore"] = r_tube + p["LIP_HEIGHT"] + p["TUBE_CLEARANCE"]
    a["skirt_in"] = p["VIEWPORT_DIAMETER"] / 2
    a["skirt_out"] = a["skirt_in"] + p["THICKNESS"]
    a["cone_slant"] = (a["skirt_out"] - a["out"]) / math.sin(t)
    a["z_skirt"] = p["CONE_START"] + (a["skirt_out"] - a["out"]) / math.tan(t)
    a["z_end"] = a["z_skirt"] + p["SKIRT_LENGTH"]

    # The inner cone surface is the outer one moved THICKNESS into the
    # material, which is an axial shift of THICKNESS / sin(angle).
    def z_inner_cone(r):
        return p["CONE_START"] + (r - a["out"]) / math.tan(t) + p["THICKNESS"] / math.sin(t)

    a["z_cone_in_start"] = z_inner_cone(a["counterbore"])
    a["z_cone_in_end"] = z_inner_cone(a["skirt_in"])
    a["z_screw"] = p["COLLAR_LENGTH"] / 2 if p["SCREW_POSITION"] is None else p["SCREW_POSITION"]
    return a


def derived():
    """Every radius and axial position the parts are built from."""
    g = {}

    # CameraMount / CameraCover, axial position measured from the camera end
    g["r_neck"] = CAMERA_DIAMETER / 2
    g["r_out"] = g["r_neck"] + THICKNESS
    g["r_bore"] = g["r_out"] - TUBE_WALL
    g["z_taper_end"] = (NECK_BORE_LENGTH
                        + (g["r_bore"] - g["r_neck"]) / math.tan(math.radians(NECK_TAPER_ANGLE)))
    r_mid = (g["r_bore"] + g["r_out"]) / 2
    g["tongue_in"] = r_mid - TONGUE_THICKNESS / 2
    g["tongue_out"] = r_mid + TONGUE_THICKNESS / 2
    g["groove_in"] = g["tongue_in"] - JOINT_CLEARANCE
    g["groove_out"] = g["tongue_out"] + JOINT_CLEARANCE
    g["groove_depth"] = TONGUE_LENGTH + JOINT_CLEARANCE

    g["adapter"] = adapter_geometry()
    g["adapter2"] = adapter_geometry("ADAPTER2_")
    return g


def check_dimensions(g):
    problems = []

    def need(ok, msg):
        if not ok:
            problems.append(msg)

    need(SCALE > 0, "SCALE must be greater than 0")
    need(0 < NECK_TAPER_ANGLE < 90, "NECK_TAPER_ANGLE must be between 0 and 90")
    need(g["r_neck"] > 1, "CAMERA_DIAMETER must be greater than 2")
    need(0 < TUBE_WALL < THICKNESS,
         "TUBE_WALL must be between 0 and THICKNESS (the camera-body bore is wider than CAMERA_DIAMETER)")
    need(g["z_taper_end"] < COVER_LENGTH,
         "NECK_BORE_LENGTH plus the NECK_TAPER_ANGLE taper must end before COVER_LENGTH")
    need(g["groove_in"] > g["r_bore"] + 0.5 and g["groove_out"] < g["r_out"] - 0.5,
         "TONGUE_THICKNESS + 2 * JOINT_CLEARANCE must fit inside TUBE_WALL with some material left")
    need(COVER_LENGTH + g["groove_depth"] < MOUNT_LENGTH - LIP_THICKNESS,
         "COVER_LENGTH + TONGUE_LENGTH must be shorter than MOUNT_LENGTH minus LIP_THICKNESS")
    for a in (g["adapter"], g["adapter2"]):
        n, p = a["prefix"], a["p"]
        need(p["THICKNESS"] > 0 and p["CAMERA_DIAMETER"] > 0,
             f"{n}THICKNESS and {n}CAMERA_DIAMETER must be greater than 0")
        need(a["counterbore"] < a["out"] - 0.5,
             f"{n}LIP_HEIGHT must be smaller than {n}THICKNESS (lip pocket breaks through the adapter wall)")
        need(a["skirt_in"] > a["counterbore"] + 0.5,
             f"{n}VIEWPORT_DIAMETER must be larger than {2 * a['counterbore'] + 1:.1f} (the adapter's bore)")
        need(p["COLLAR_LENGTH"] < p["CONE_START"], f"{n}COLLAR_LENGTH must be shorter than {n}CONE_START")
        need(p["SCREW_HOLE_DIAMETER"] < p["COLLAR_LENGTH"], f"{n}SCREW_HOLE_DIAMETER is wider than the collar")
        need(a["z_cone_in_start"] > p["COLLAR_LENGTH"],
             f"{n}inner cone starts inside the collar; increase {n}CONE_START or reduce {n}THICKNESS/{n}LIP_HEIGHT")
        need(a["z_cone_in_end"] < a["z_end"], f"{n}SKIRT_LENGTH is too short for the cone wall thickness")
    a = g["adapter"]
    need(INSERTION_DEPTH >= COLLAR_LENGTH + LIP_THICKNESS,
         "INSERTION_DEPTH must put the lip past the collar (>= COLLAR_LENGTH + LIP_THICKNESS)")
    need(INSERTION_DEPTH <= a["z_cone_in_start"],
         f"INSERTION_DEPTH must be <= {a['z_cone_in_start']:.1f} (where the inner cone starts)")
    need(INSERTION_DEPTH < MOUNT_LENGTH - COVER_LENGTH - g["groove_depth"],
         "the adapter would cover the cover/tube joint; reduce INSERTION_DEPTH or increase MOUNT_LENGTH")
    if problems:
        raise ValueError("Dimension problems:\n  - " + "\n  - ".join(problems))


def adapter_profile(a):
    cone_start, collar = a["p"]["CONE_START"], a["p"]["COLLAR_LENGTH"]
    return [
        (a["bore"], 0.0),
        (a["out"], 0.0),
        (a["out"], cone_start),
        (a["skirt_out"], a["z_skirt"]),
        (a["skirt_out"], a["z_end"]),
        (a["skirt_in"], a["z_end"]),
        (a["skirt_in"], a["z_cone_in_end"]),
        (a["counterbore"], a["z_cone_in_start"]),
        (a["counterbore"], collar),
        (a["bore"], collar),
    ]


def mount_profile(g):
    """Full-length tube; the top half of the camera end is cut away afterwards."""
    return [
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], MOUNT_LENGTH - LIP_THICKNESS),
        (g["r_out"] + LIP_HEIGHT, MOUNT_LENGTH - LIP_THICKNESS),
        (g["r_out"] + LIP_HEIGHT, MOUNT_LENGTH),
        (g["r_bore"], MOUNT_LENGTH),
        (g["r_bore"], g["z_taper_end"]),
        (g["r_neck"], NECK_BORE_LENGTH),
    ]


def mount_cutter_profile(g):
    """Top-half region removed from the mount: the cover's space plus the groove."""
    r_in = g["r_neck"] / 2
    r_big = g["r_out"] + LIP_HEIGHT + 1
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
        (g["tongue_out"], COVER_LENGTH + TONGUE_LENGTH),
        (g["tongue_in"], COVER_LENGTH + TONGUE_LENGTH),
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


def snap(bm):
    """Zero out float noise (~1e-15) so points meant to lie on the cover split
    and cutaway planes really do; the exact boolean leaves holes otherwise."""
    for v in bm.verts:
        v.co = [0.0 if abs(c) < 1e-9 else c for c in v.co]


def finish_mesh(name, bm, coll):
    snap(bm)
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
    bm = bmesh.new()
    bm.from_mesh(new_mesh)
    snap(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(new_mesh)
    bm.free()
    target.modifiers.remove(mod)
    old_mesh = target.data
    target.data = new_mesh
    new_mesh.name = target.name
    bpy.data.meshes.remove(old_mesh)
    cutter_mesh = cutter.data
    bpy.data.objects.remove(cutter)
    bpy.data.meshes.remove(cutter_mesh)


def matte_material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)  # solid-mode viewport colour
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
    settings = {"Base Color": (*color, 1.0), "Roughness": 1.0, "Metallic": 0.0,
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

def build_chamber_adapter(name, a, coll):
    adapter = revolve(name, adapter_profile(a), coll)
    p = a["p"]
    if p["SCREW_COUNT"] > 0:
        bm = bmesh.new()
        r_mid = (a["bore"] + a["out"]) / 2
        depth = a["out"] - a["bore"] + 4
        radius = p["SCREW_HOLE_DIAMETER"] / 2
        for i in range(p["SCREW_COUNT"]):
            ang = math.radians(p["SCREW_ANGLE"] + 360.0 * i / p["SCREW_COUNT"])
            place = (Matrix.Translation((a["z_screw"], r_mid * math.cos(ang), r_mid * math.sin(ang)))
                     @ Matrix.Rotation(ang - math.pi / 2, 4, 'X'))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=radius,
                                  radius2=radius, depth=depth, matrix=place)
        boolean(adapter, finish_mesh("ScrewHoles", bm, coll))
    return adapter


def build_camera_mount(g, coll):
    mount = revolve("CameraMount", mount_profile(g), coll)
    boolean(mount, revolve("CoverCutter", mount_cutter_profile(g), coll, start=0, sweep=180))
    return mount


def build_camera_cover(g, coll):
    return revolve("CameraCover", cover_profile(g), coll, start=0, sweep=180)


def cutaway(obj, coll):
    """Remove the -Y half of obj with a box sized to cover the whole object."""
    # Read the vertices directly: bound_box and matrix_world are stale until the
    # scene next updates.
    h = max(abs(c) for v in obj.data.vertices for c in v.co) + obj.location.length + 1.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, -h, 0))
                          @ Matrix.Diagonal((4 * h, 2 * h, 4 * h, 1)))
    boolean(obj, finish_mesh("CutawayBox", bm, coll))


def main():
    g = derived()
    check_dimensions(g)
    setup_units()
    coll = clean_collection(COLLECTION_NAME)

    adapter = build_chamber_adapter("ChamberAdapter", g["adapter"], coll)
    mount = build_camera_mount(g, coll)
    cover = build_camera_cover(g, coll)
    adapter2 = build_chamber_adapter("ChamberAdapter2", g["adapter2"], coll)
    parts = [(adapter, ADAPTER_COLOR), (mount, MOUNT_COLOR), (cover, COVER_COLOR),
             (adapter2, ADAPTER2_COLOR)]

    for obj, _ in parts:
        obj.data.transform(Matrix.Scale(SCALE, 4))
    adapter.location.x = (MOUNT_LENGTH - INSERTION_DEPTH) * SCALE + EXPLODE
    cover.location = (-EXPLODE, 0.0, EXPLODE)
    # Directly below the ChamberAdapter, ADAPTER2_GAP clear of the assembly.
    assembly_radius = max(g["adapter"]["skirt_out"], g["r_out"] + LIP_HEIGHT)
    drop = assembly_radius + ADAPTER2_GAP + g["adapter2"]["skirt_out"]
    adapter2.location = (adapter.location.x, 0.0, -drop * SCALE)

    for obj, color in parts:
        if CUTAWAY:
            cutaway(obj, coll)
        finish_object(obj, matte_material(f"{obj.name} Matte", color))
    a = g["adapter"]
    print(f"Built {COLLECTION_NAME}: mount OD {2 * g['r_out'] * SCALE:.1f} mm, "
          f"adapter OD {2 * a['skirt_out'] * SCALE:.1f} mm, cone slant {a['cone_slant'] * SCALE:.1f} mm, "
          f"overall length {(MOUNT_LENGTH - INSERTION_DEPTH + a['z_end']) * SCALE:.1f} mm")


if __name__ == "__main__" and bpy is not None:
    main()
