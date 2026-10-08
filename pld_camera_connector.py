"""
PLD chamber camera connector - parametric model for Blender 5.2, for 3D printing

Run it from Blender's Scripting workspace (open this file, then Text > Run Script),
or from a terminal:   blender --python pld_camera_connector.py
Re-running the script rebuilds the model with the current parameter values.

Three parts, all built around the global X axis. The camera is on the left
(X = 0) and the PLD chamber viewport is on the right:

  CameraMount    - a bottom half-cylinder cradle the camera sits in, joined to a
                   full tube that slides into the ChamberAdapter. A lip at its
                   chamber end stops it pulling out of the adapter.
  CameraCover    - a top half-cylinder that covers the camera. Its tongue slides
                   into a groove in the end of the CameraMount tube.
  ChamberAdapter - grips the mount tube with set screws in its collar, flares out
                   to a face that sits on the viewport flange with an indent
                   around the glass, and clamps onto the flange with prongs that
                   each carry a set screw.

A fourth, separate part sits below the assembly:

  ChamberAdapter2 - the same adapter with its own ADAPTER2_* parameters, set up
                    for the alternate 6" viewport.

All parameters are in inches (angles in degrees). The model itself is built in
millimetres, so an exported STL comes out the right size for slicers; Blender
displays lengths in inches. Every screw hole is sized to tap for 5/16"-24 and
sits in a raised pad for more thread. The defaults fit an Ender-3 V2 with each
part printed standing on end; the PRINTER_* checks enforce that.
"""

import math
import os
import struct

try:
    import bpy
    import bmesh
    from mathutils import Matrix
except ImportError:  # lets the profile math be checked outside Blender
    bpy = None


# =============================================================================
# MAIN DIMENSIONS  (inches)
# =============================================================================

CAMERA_DIAMETER = 1.6        # camera neck, held at the camera end of the mount
FOCUS_DIAL_DIAMETER = 2.0    # camera focus dial, the wider part of the camera
VIEWPORT_DIAMETER = 8.0      # raised viewport flange the prongs clamp around
THICKNESS = 1 / 8            # wall thickness of every part, including the prongs
                             # (screw holes and the cover joint get extra pads)


# =============================================================================
# OTHER PARAMETERS  (inches)
# =============================================================================

# ---- Viewport ---------------------------------------------------------------
GLASS_DIAMETER = 6.5         # glass sticking out of the flange face
RECESS_DEPTH = 1 / 4         # depth of the indent that fits around the glass
FLANGE_HEIGHT = 1.375        # how far the flange sticks out from the chamber wall

# ---- Fit --------------------------------------------------------------------
FIT_CLEARANCE = 0.01         # radial gap wherever parts slide together or fit
                             # around the camera, glass or flange

# ---- CameraMount and CameraCover --------------------------------------------
MOUNT_LENGTH = 9.75          # overall length: neck section + focus dial section
NECK_BORE_LENGTH = 1.0       # length of the CAMERA_DIAMETER section at the camera end
LIP_HEIGHT = 1 / 8           # radial height of the retaining lip at the chamber end
LIP_THICKNESS = 1 / 4        # axial thickness of that lip
COVER_LENGTH = 2.75          # length of the cover (= where the full tube starts)
TONGUE_LENGTH = 1.25         # length of the cover's tongue that slides into the groove
TONGUE_THICKNESS = 1 / 16    # radial thickness of the tongue
JOINT_PAD_THICKNESS = 1 / 16 # extra wall on the outside of the mount tube where the
                             # groove is, so the groove's walls aren't too thin

# ---- ChamberAdapter ---------------------------------------------------------
ADAPTER_LENGTH = 8.5         # front face to the face that sits on the flange (prongs extra)
CONE_ANGLE = 45.0            # cone angle, degrees from the axis
RIM_LENGTH = 0.5             # straight section between the cone and the flange face
COLLAR_LENGTH = 1.0          # length of the bore that grips the mount tube
INSERTION_DEPTH = 1.5        # how far the mount tube sits inside the adapter
PRONG_COUNT = 3              # prongs that clamp onto the flange, evenly spaced
PRONG_WIDTH = 1.0            # width of each prong
PRONG_LENGTH = 1.25          # how far the prongs reach along the flange (<= FLANGE_HEIGHT)
PRONG_ANGLE = 270.0          # angle of the first prong (270 = straight down, so the
                             # other two sit up at 30 and 150)
PRONG_SCREW_POSITION = None  # from the flange face; None = middle of the prong

# ---- Screws: 5/16"-24 tapped straight into the plastic ----------------------
SCREW_HOLE_DIAMETER = 0.272  # tap drill (letter I), used for every screw hole
SCREW_COUNT = 2              # collar set screws, evenly spaced
SCREW_ANGLE = 90.0           # angle of the first collar screw (90 = straight up)
SCREW_POSITION = None        # from the adapter front face; None = collar middle
SCREW_PAD_DIAMETER = 0.75    # round pad on the outside around every screw hole
SCREW_PAD_THICKNESS = 1 / 8  # how far the pad stands out, for more thread

# ---- ChamberAdapter2: alternate 6" viewport, placed below the assembly ------
# Each one means the same as the ChamberAdapter parameter with the same name
# (ADAPTER2_LENGTH is the ADAPTER_LENGTH of this part).
ADAPTER2_FOCUS_DIAL_DIAMETER = 2.0  # with ADAPTER2_THICKNESS, sets the tube size it fits
ADAPTER2_VIEWPORT_DIAMETER = 6.0
ADAPTER2_THICKNESS = 1 / 8
ADAPTER2_GLASS_DIAMETER = 4.5
ADAPTER2_RECESS_DEPTH = 3 / 16
ADAPTER2_FLANGE_HEIGHT = 1.375
ADAPTER2_FIT_CLEARANCE = 0.01
ADAPTER2_LIP_HEIGHT = 1 / 8
ADAPTER2_LENGTH = 8.5
ADAPTER2_CONE_ANGLE = 45.0
ADAPTER2_RIM_LENGTH = 0.5
ADAPTER2_COLLAR_LENGTH = 1.0
ADAPTER2_PRONG_COUNT = 3
ADAPTER2_PRONG_WIDTH = 1.0
ADAPTER2_PRONG_LENGTH = 1.25
ADAPTER2_PRONG_ANGLE = 270.0
ADAPTER2_PRONG_SCREW_POSITION = None
ADAPTER2_SCREW_HOLE_DIAMETER = 0.272
ADAPTER2_SCREW_COUNT = 2
ADAPTER2_SCREW_ANGLE = 90.0
ADAPTER2_SCREW_POSITION = None
ADAPTER2_SCREW_PAD_DIAMETER = 0.75
ADAPTER2_SCREW_PAD_THICKNESS = 1 / 8
ADAPTER2_GAP = 1.0                  # space between the assembly and ChamberAdapter2

# ---- Size -------------------------------------------------------------------
SCALE = 1.0                  # uniform scale for the whole finished model; the screw
                             # holes and clearances scale with it

# ---- Printer (each part is checked printed standing on end) -----------------
PRINTER_MAX_HEIGHT = 250 / 25.4  # Ender-3 V2: 250 mm; None skips the check
PRINTER_BED_SIZE = 220 / 25.4    # Ender-3 V2: 220 x 220 mm; None skips the check

# ---- Export -----------------------------------------------------------------
# Every run writes one STL per part (always whole, never cut away), in mm and
# stood on end the way it should print. A relative folder is next to this script.
EXPORT_FOLDER = "stl"        # None turns export off
EXPORT_PARTS = ("CameraMount", "CameraCover", "ChamberAdapter")  # add "ChamberAdapter2"
                                                                 # for the 6" viewport

# ---- Display ----------------------------------------------------------------
SEGMENTS = 128               # facets around the axis (keep it a multiple of 4)
EXPLODE = 0.0                # inches to pull the parts apart for viewing
CUTAWAY = True               # remove the -Y half of every part to show the cross-section
ADAPTER_COLOR = (0.50, 0.50, 0.50)   # ChamberAdapter: matte grey
MOUNT_COLOR = (0.20, 0.35, 0.65)     # CameraMount: matte blue
COVER_COLOR = (0.80, 0.45, 0.15)     # CameraCover: matte orange
ADAPTER2_COLOR = (0.50, 0.50, 0.50)  # ChamberAdapter2: matte grey
COLLECTION_NAME = "PLD Camera Connector"

MM_PER_INCH = 25.4
MIN_WALL = 1 / 32            # thinnest wall the dimension checks accept


# =============================================================================
# DERIVED GEOMETRY  (profiles are (radius, axial position) pairs, in inches)
# =============================================================================

ADAPTER_KEYS = ("FOCUS_DIAL_DIAMETER", "VIEWPORT_DIAMETER", "THICKNESS", "GLASS_DIAMETER",
                "RECESS_DEPTH", "FLANGE_HEIGHT", "FIT_CLEARANCE", "LIP_HEIGHT", "ADAPTER_LENGTH",
                "CONE_ANGLE", "RIM_LENGTH", "COLLAR_LENGTH", "PRONG_COUNT", "PRONG_WIDTH",
                "PRONG_LENGTH", "PRONG_ANGLE", "PRONG_SCREW_POSITION", "SCREW_HOLE_DIAMETER",
                "SCREW_COUNT", "SCREW_ANGLE", "SCREW_POSITION", "SCREW_PAD_DIAMETER",
                "SCREW_PAD_THICKNESS")


def param_name(prefix, key):
    """Global name of an adapter parameter. With a prefix, a leading ADAPTER_
    is dropped so ADAPTER_LENGTH becomes ADAPTER2_LENGTH."""
    if prefix and key.startswith("ADAPTER_"):
        key = key[len("ADAPTER_"):]
    return prefix + key


def adapter_geometry(prefix=""):
    """Radii and axial positions (from the front face) of an adapter built from
    the parameters named in ADAPTER_KEYS (with the given prefix)."""
    p = {k: globals()[param_name(prefix, k)] for k in ADAPTER_KEYS}
    if not 0 < p["CONE_ANGLE"] < 90:
        raise ValueError(f"{param_name(prefix, 'CONE_ANGLE')} must be between 0 and 90")
    t = math.radians(p["CONE_ANGLE"])
    c, wall = p["FIT_CLEARANCE"], p["THICKNESS"]
    a = {"prefix": prefix, "p": p}

    r_tube = p["FOCUS_DIAL_DIAMETER"] / 2 + c + wall  # outside of the mount tube
    a["bore"] = r_tube + c
    a["counterbore"] = r_tube + p["LIP_HEIGHT"] + c
    a["out"] = a["counterbore"] + wall
    a["prong_in"] = p["VIEWPORT_DIAMETER"] / 2 + c
    a["prong_out"] = a["prong_in"] + wall
    a["recess"] = p["GLASS_DIAMETER"] / 2 + c

    a["z_end"] = p["ADAPTER_LENGTH"]  # face that sits on the flange
    a["z_seat"] = a["z_end"] - p["RECESS_DEPTH"]
    a["z_tip"] = a["z_end"] + p["PRONG_LENGTH"]
    a["z_rim"] = a["z_end"] - p["RIM_LENGTH"]
    a["z_cone"] = a["z_rim"] - (a["prong_out"] - a["out"]) / math.tan(t)

    # The inner cone surface is the outer one moved THICKNESS into the
    # material, which is an axial shift of THICKNESS / sin(angle).
    def z_inner_cone(r):
        return a["z_cone"] + (r - a["out"]) / math.tan(t) + wall / math.sin(t)

    a["z_cone_in_start"] = z_inner_cone(a["counterbore"])
    a["z_cone_in_end"] = z_inner_cone(a["prong_in"])
    a["z_screw"] = p["COLLAR_LENGTH"] / 2 if p["SCREW_POSITION"] is None else p["SCREW_POSITION"]
    a["z_prong_screw"] = a["z_end"] + (p["PRONG_LENGTH"] / 2 if p["PRONG_SCREW_POSITION"] is None
                                       else p["PRONG_SCREW_POSITION"])
    r_mid = (a["prong_in"] + a["prong_out"]) / 2
    a["prong_half_angle"] = math.degrees(p["PRONG_WIDTH"] / 2 / r_mid)
    count = p["PRONG_COUNT"]
    a["prong_angles"] = [p["PRONG_ANGLE"] + 360.0 * i / count for i in range(count)]

    # Size when printed standing on end, for the printer checks and layout.
    pad = p["SCREW_PAD_THICKNESS"]
    a["max_r"] = max(a["prong_out"] + (pad if count else 0), a["out"] + (pad if p["SCREW_COUNT"] else 0))
    a["height"] = a["z_tip"] if count else a["z_end"]
    return a


def derived():
    """Every radius and axial position the parts are built from."""
    g = {}

    # CameraMount / CameraCover, axial position measured from the camera end
    g["r_neck"] = CAMERA_DIAMETER / 2 + FIT_CLEARANCE
    g["r_body"] = FOCUS_DIAL_DIAMETER / 2 + FIT_CLEARANCE
    g["r_out"] = g["r_body"] + THICKNESS
    g["r_pad"] = g["r_out"] + JOINT_PAD_THICKNESS
    # The tongue and groove sit in the middle of the padded wall at the joint.
    r_mid = (g["r_body"] + g["r_pad"]) / 2
    g["tongue_in"] = r_mid - TONGUE_THICKNESS / 2
    g["tongue_out"] = r_mid + TONGUE_THICKNESS / 2
    g["groove_in"] = g["tongue_in"] - FIT_CLEARANCE
    g["groove_out"] = g["tongue_out"] + FIT_CLEARANCE
    g["groove_depth"] = TONGUE_LENGTH + FIT_CLEARANCE
    g["pad_end"] = COVER_LENGTH + g["groove_depth"] + THICKNESS
    g["max_r"] = g["r_out"] + max(LIP_HEIGHT, JOINT_PAD_THICKNESS)

    g["adapter"] = adapter_geometry()
    g["adapter2"] = adapter_geometry("ADAPTER2_")
    return g


def check_dimensions(g):
    problems = []

    def need(ok, msg):
        if not ok:
            problems.append(msg)

    need(SCALE > 0, "SCALE must be greater than 0")
    need(CAMERA_DIAMETER > 0 and THICKNESS > 0, "CAMERA_DIAMETER and THICKNESS must be greater than 0")
    need(FOCUS_DIAL_DIAMETER >= CAMERA_DIAMETER, "FOCUS_DIAL_DIAMETER must be at least CAMERA_DIAMETER")
    need(0 < NECK_BORE_LENGTH < COVER_LENGTH, "NECK_BORE_LENGTH must be between 0 and COVER_LENGTH")
    need(JOINT_PAD_THICKNESS >= 0, "JOINT_PAD_THICKNESS can't be negative")
    need(g["tongue_out"] <= g["r_out"] + 1e-9,
         "TONGUE_THICKNESS + JOINT_PAD_THICKNESS must not be more than THICKNESS "
         "(the tongue has to sit on the cover's wall)")
    need(g["groove_in"] >= g["r_body"] + MIN_WALL and g["groove_out"] <= g["r_pad"] - MIN_WALL,
         "TONGUE_THICKNESS + 2 * FIT_CLEARANCE must fit inside THICKNESS + JOINT_PAD_THICKNESS with "
         f"{MIN_WALL:.3f} in of wall left on each side")
    need(g["pad_end"] <= MOUNT_LENGTH - LIP_THICKNESS,
         "COVER_LENGTH + TONGUE_LENGTH + THICKNESS must not be longer than MOUNT_LENGTH minus LIP_THICKNESS")

    for a in (g["adapter"], g["adapter2"]):
        p = a["p"]

        def n(key):
            return param_name(a["prefix"], key)

        hole = p["SCREW_HOLE_DIAMETER"]
        pad_r = p["SCREW_PAD_DIAMETER"] / 2
        need(p["SCREW_PAD_THICKNESS"] >= 0, f"{n('SCREW_PAD_THICKNESS')} can't be negative")
        need(pad_r >= hole / 2 + MIN_WALL,
             f"{n('SCREW_PAD_DIAMETER')} must be at least {hole + 2 * MIN_WALL:.3f} (wider than the hole)")
        if p["SCREW_COUNT"] > 0:
            need(pad_r <= a["z_screw"] and a["z_screw"] + pad_r <= p["COLLAR_LENGTH"],
                 f"the collar screw pads don't fit; make {n('COLLAR_LENGTH')} at least {2 * pad_r:.3f} "
                 f"or move {n('SCREW_POSITION')}")
            need(math.hypot(a["bore"] + 0.02, pad_r) < a["out"],
                 f"{n('SCREW_PAD_DIAMETER')} is too wide for the curve of the collar")
        need(a["recess"] <= a["prong_in"] - MIN_WALL,
             f"{n('GLASS_DIAMETER')} must be smaller than {n('VIEWPORT_DIAMETER')}")
        need(a["prong_out"] > a["out"] + MIN_WALL,
             f"{n('VIEWPORT_DIAMETER')} must be larger than {2 * a['out']:.2f} (the adapter's collar)")
        need(p["RECESS_DEPTH"] > 0, f"{n('RECESS_DEPTH')} must be greater than 0")
        need(a["z_cone_in_end"] <= a["z_seat"],
             f"{n('RIM_LENGTH')} must be at least "
             f"{p['RIM_LENGTH'] + a['z_cone_in_end'] - a['z_seat']:.3f} to fit the indent behind the cone")
        need(a["z_cone"] >= p["COLLAR_LENGTH"],
             f"{n('ADAPTER_LENGTH')} is too short for the cone; make it at least "
             f"{p['ADAPTER_LENGTH'] + p['COLLAR_LENGTH'] - a['z_cone']:.2f}")
        need(hole < p["COLLAR_LENGTH"], f"{n('SCREW_HOLE_DIAMETER')} is wider than {n('COLLAR_LENGTH')}")
        need(0 < p["PRONG_LENGTH"] <= p["FLANGE_HEIGHT"],
             f"{n('PRONG_LENGTH')} must be between 0 and {n('FLANGE_HEIGHT')} (prongs would hit the chamber)")
        need(isinstance(p["PRONG_COUNT"], int) and p["PRONG_COUNT"] >= 0,
             f"{n('PRONG_COUNT')} must be a whole number >= 0")
        if p["PRONG_COUNT"] > 0:
            need(2 * a["prong_half_angle"] * p["PRONG_COUNT"] < 360 - 5,
                 f"{n('PRONG_COUNT')} prongs of {n('PRONG_WIDTH')} don't fit around the flange")
            need(hole < p["PRONG_WIDTH"], f"{n('SCREW_HOLE_DIAMETER')} is wider than {n('PRONG_WIDTH')}")
            need(p["SCREW_PAD_DIAMETER"] <= p["PRONG_WIDTH"],
                 f"{n('SCREW_PAD_DIAMETER')} is wider than {n('PRONG_WIDTH')}")
            need(math.hypot(a["prong_in"] + 0.02, pad_r) < a["prong_out"],
                 f"{n('SCREW_PAD_DIAMETER')} is too wide for the curve of the prongs")
            need(a["z_end"] + pad_r <= a["z_prong_screw"] <= a["z_tip"] - pad_r,
                 f"the prong screw pads run off the prong; make {n('PRONG_LENGTH')} longer "
                 f"or move {n('PRONG_SCREW_POSITION')}")

    a = g["adapter"]
    need(INSERTION_DEPTH >= COLLAR_LENGTH + LIP_THICKNESS,
         "INSERTION_DEPTH must put the lip past the collar (>= COLLAR_LENGTH + LIP_THICKNESS)")
    need(INSERTION_DEPTH <= a["z_cone_in_start"],
         f"INSERTION_DEPTH must be <= {a['z_cone_in_start']:.2f} (where the inner cone starts)")
    need(INSERTION_DEPTH <= MOUNT_LENGTH - g["pad_end"],
         f"INSERTION_DEPTH must be <= {MOUNT_LENGTH - g['pad_end']:.2f} so the adapter clears the cover joint")

    # Each part printed standing on end.
    sizes = {"CameraMount": (MOUNT_LENGTH, g["max_r"]),
             "CameraCover": (COVER_LENGTH + TONGUE_LENGTH, g["r_out"]),
             "ChamberAdapter": (a["height"], a["max_r"]),
             "ChamberAdapter2": (g["adapter2"]["height"], g["adapter2"]["max_r"])}
    for name, (height, radius) in sizes.items():
        if PRINTER_MAX_HEIGHT is not None:
            need(height * SCALE <= PRINTER_MAX_HEIGHT,
                 f"{name} is {height * SCALE:.2f} in tall standing up; the printer fits {PRINTER_MAX_HEIGHT:.2f} in")
        if PRINTER_BED_SIZE is not None:
            need(2 * radius * SCALE <= PRINTER_BED_SIZE,
                 f"{name} is {2 * radius * SCALE:.2f} in across; the printer bed fits {PRINTER_BED_SIZE:.2f} in")
    if problems:
        raise ValueError("Dimension problems:\n  - " + "\n  - ".join(problems))


def clean(profile):
    """Drop points that repeat the one before (e.g. when a pad is 0 or the
    tongue is flush with the cover's outside)."""
    return [pt for i, pt in enumerate(profile)
            if abs(pt[0] - profile[i - 1][0]) > 1e-9 or abs(pt[1] - profile[i - 1][1]) > 1e-9]


def adapter_profile(a):
    """Full ring past the flange face; it is cut down to prongs afterwards."""
    collar = a["p"]["COLLAR_LENGTH"]
    return clean([
        (a["bore"], 0.0),
        (a["out"], 0.0),
        (a["out"], a["z_cone"]),
        (a["prong_out"], a["z_rim"]),
        (a["prong_out"], a["z_tip"]),
        (a["prong_in"], a["z_tip"]),
        (a["prong_in"], a["z_end"]),
        (a["recess"], a["z_end"]),
        (a["recess"], a["z_seat"]),
        (a["prong_in"], a["z_seat"]),
        (a["prong_in"], a["z_cone_in_end"]),
        (a["counterbore"], a["z_cone_in_start"]),
        (a["counterbore"], collar),
        (a["bore"], collar),
    ])


def prong_gap_profile(a):
    """Cross-section of the ring removed between prongs."""
    r_in, r_out = a["prong_in"] - 0.05, a["prong_out"] + 0.1
    return [(r_in, a["z_end"]), (r_out, a["z_end"]), (r_out, a["z_tip"] + 0.1), (r_in, a["z_tip"] + 0.1)]


def mount_profile(g):
    """Full-length tube; the top half of the camera end is cut away afterwards."""
    return clean([
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], COVER_LENGTH),
        (g["r_pad"], COVER_LENGTH),
        (g["r_pad"], g["pad_end"]),
        (g["r_out"], g["pad_end"]),
        (g["r_out"], MOUNT_LENGTH - LIP_THICKNESS),
        (g["r_out"] + LIP_HEIGHT, MOUNT_LENGTH - LIP_THICKNESS),
        (g["r_out"] + LIP_HEIGHT, MOUNT_LENGTH),
        (g["r_body"], MOUNT_LENGTH),
        (g["r_body"], NECK_BORE_LENGTH),
        (g["r_neck"], NECK_BORE_LENGTH),
    ])


def mount_cutter_profile(g):
    """Top-half region removed from the mount: the cover's space plus the groove."""
    r_in = g["r_neck"] / 2
    r_big = g["max_r"] + 0.1
    return [
        (r_in, -0.1),
        (r_big, -0.1),
        (r_big, COVER_LENGTH),
        (g["groove_out"], COVER_LENGTH),
        (g["groove_out"], COVER_LENGTH + g["groove_depth"]),
        (g["groove_in"], COVER_LENGTH + g["groove_depth"]),
        (g["groove_in"], COVER_LENGTH),
        (r_in, COVER_LENGTH),
    ]


def cover_profile(g):
    return clean([
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH + TONGUE_LENGTH),
        (g["tongue_in"], COVER_LENGTH + TONGUE_LENGTH),
        (g["tongue_in"], COVER_LENGTH),
        (g["r_body"], COVER_LENGTH),
        (g["r_body"], NECK_BORE_LENGTH),
        (g["r_neck"], NECK_BORE_LENGTH),
    ])


# =============================================================================
# BLENDER HELPERS
# =============================================================================

def setup_units():
    units = bpy.context.scene.unit_settings
    units.system = 'IMPERIAL'
    units.length_unit = 'INCHES'
    units.scale_length = 0.001  # 1 Blender unit = 1 mm, so STL exports are in mm
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

def add_radial_cylinders(bm, spots, r_in, r_out, diameter):
    """Cylinders running radially from r_in to r_out, one per (x, angle)."""
    r_mid = (r_in + r_out) / 2
    for x, angle in spots:
        ang = math.radians(angle)
        place = (Matrix.Translation((x, r_mid * math.cos(ang), r_mid * math.sin(ang)))
                 @ Matrix.Rotation(ang - math.pi / 2, 4, 'X'))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=diameter / 2,
                              radius2=diameter / 2, depth=r_out - r_in, matrix=place)


def build_chamber_adapter(name, a, coll):
    p = a["p"]
    adapter = revolve(name, adapter_profile(a), coll)

    # Cut the ring past the flange face down to the prongs.
    count = p["PRONG_COUNT"]
    if count == 0:
        boolean(adapter, revolve("ProngCutter", prong_gap_profile(a), coll))
    for angle in a["prong_angles"]:
        boolean(adapter, revolve("ProngCutter", prong_gap_profile(a), coll,
                                 start=angle + a["prong_half_angle"],
                                 sweep=360.0 / count - 2 * a["prong_half_angle"]))

    # Screw spots as (x, angle, inside radius, outside radius of the wall).
    spots = [(a["z_screw"], p["SCREW_ANGLE"] + 360.0 * i / p["SCREW_COUNT"], a["bore"], a["out"])
             for i in range(p["SCREW_COUNT"])]
    spots += [(a["z_prong_screw"], angle, a["prong_in"], a["prong_out"]) for angle in a["prong_angles"]]
    if not spots:
        return adapter

    # Raised pads on the outside, starting just outside the bore so they never
    # poke into it, then holes through pad and wall.
    pad = p["SCREW_PAD_THICKNESS"]
    if pad > 0:
        bm = bmesh.new()
        for x, angle, r_in, r_out in spots:
            add_radial_cylinders(bm, [(x, angle)], r_in + 0.02, r_out + pad, p["SCREW_PAD_DIAMETER"])
        boolean(adapter, finish_mesh("ScrewPads", bm, coll), 'UNION')
    bm = bmesh.new()
    for x, angle, r_in, r_out in spots:
        add_radial_cylinders(bm, [(x, angle)], r_in - 0.1, r_out + pad + 0.1, p["SCREW_HOLE_DIAMETER"])
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


# =============================================================================
# EXPORT
# =============================================================================

# Which end each part stands on when printed. The mount stands on its lip end
# (a full ring, and the cover's groove then opens upward); the adapter on its
# prong tips. Everything else stands on its camera end.
PRINT_CHAMBER_END_DOWN = {"CameraMount", "ChamberAdapter", "ChamberAdapter2"}


def script_folder():
    """Folder this script lives in. Run from Blender's text editor, __file__ is
    only the text's name, so the loaded text's own file path is used instead."""
    path = globals().get("__file__", "")
    if os.path.isfile(path):
        return os.path.dirname(os.path.abspath(path))
    text = bpy.data.texts.get(os.path.basename(path))
    if text is not None and text.filepath:
        return os.path.dirname(bpy.path.abspath(text.filepath))
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return None


def export_folder():
    folder = os.path.expanduser(EXPORT_FOLDER)
    if not os.path.isabs(folder):
        base = script_folder()
        if base is None:
            raise ValueError("Can't tell where this script is saved; set EXPORT_FOLDER to a full path")
        folder = os.path.join(base, folder)
    os.makedirs(folder, exist_ok=True)
    return folder


def write_stl(path, obj):
    """Binary STL of obj's mesh, stood on end for printing: its axis along Z,
    resting on Z = 0 and centred on the bed. Uses Blender's own triangles, and
    stands the part up by swapping axes exactly (a rotation matrix adds float
    noise that can make the triangles disagree along shared edges)."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    if obj.name in PRINT_CHAMBER_END_DOWN:
        def upright(co):  # chamber (+X) end down
            return (co[2], co[1], -co[0])
    else:
        def upright(co):  # camera (-X) end down
            return (-co[2], co[1], co[0])
    pts = [upright(v.co) for v in mesh.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    shift = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    pts = [(p[0] + shift[0], p[1] + shift[1], p[2] + shift[2]) for p in pts]
    with open(path, "wb") as f:
        f.write(obj.name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(mesh.loop_triangles)))
        for tri in mesh.loop_triangles:
            f.write(struct.pack("<3f", *upright(tri.normal)))
            for i in tri.vertices:
                f.write(struct.pack("<3f", *pts[i]))
            f.write(b"\0\0")


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

    # Built in inches; convert to millimetres (and apply SCALE).
    k = SCALE * MM_PER_INCH
    explode = EXPLODE * MM_PER_INCH
    for obj, _ in parts:
        obj.data.transform(Matrix.Scale(k, 4))
    adapter.location.x = (MOUNT_LENGTH - INSERTION_DEPTH) * k + explode
    cover.location = (-explode, 0.0, explode)
    # Directly below the ChamberAdapter, ADAPTER2_GAP clear of the assembly.
    assembly_radius = max(g["adapter"]["max_r"], g["max_r"])
    drop = assembly_radius + ADAPTER2_GAP + g["adapter2"]["max_r"]
    adapter2.location = (adapter.location.x, 0.0, -drop * k)

    # Export before any cutaway so the files are always whole parts.
    if EXPORT_FOLDER is not None:
        folder = export_folder()
        for obj, _ in parts:
            if obj.name in EXPORT_PARTS:
                write_stl(os.path.join(folder, obj.name + ".stl"), obj)
        print(f"Wrote {', '.join(n + '.stl' for n in EXPORT_PARTS)} to {folder}")

    for obj, color in parts:
        if CUTAWAY:
            cutaway(obj, coll)
        finish_object(obj, matte_material(f"{obj.name} Matte", color))
    a = g["adapter"]
    print(f"Built {COLLECTION_NAME}: mount OD {2 * g['r_out'] * SCALE:.3f} in, "
          f"adapter {2 * a['max_r'] * SCALE:.3f} in across x {a['height'] * SCALE:.2f} in tall, "
          f"camera end to flange face {(MOUNT_LENGTH - INSERTION_DEPTH + a['z_end']) * SCALE:.2f} in")


if __name__ == "__main__" and bpy is not None:
    main()
