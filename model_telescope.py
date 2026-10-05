"""
Model telescope - parametric model for Blender 5.2

Run it from Blender's Scripting workspace (open this file, then Text > Run Script),
or from a terminal:   blender --python model_telescope.py
Re-running the script rebuilds the model with the current parameter values.

A camera mount that telescopes out toward the PLD chamber. Every part is built
around the global X axis, with the camera on the left (X = 0) and the chamber on
the right. Numbers match the circled labels on the hand sketch:

  1    Telescope Mount     - bottom half-cylinder cradle the camera sits in, joined
                             to a full tube with an outward foot at its chamber end.
  1.5  Telescope Cover     - top half-cylinder over the camera. Its tongue slides
                             into a groove in the mount's tube.
  2    Telescope Segment N - tube with an inward lip at its camera end (catches the
                             foot of the part inside it) and an outward foot at its
                             chamber end. Repeated SEGMENT_COUNT times; each one is
                             sized to slide over the one before it.
  3    Telescope Base      - outermost tube with an inward lip at its camera end; its
                             chamber end sits against the PLD chamber.

All lengths are in millimetres.
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

# ---- Mount (1) and cover (1.5) ----------------------------------------------
MOUNT_OUTER_DIAMETER = 72.0  # outside diameter of the mount and cover
MOUNT_NECK_WALL = 15.0       # wall thickness around the camera's neck (camera end)
MOUNT_NECK_LENGTH = 30.0     # length of that thick-walled neck section
MOUNT_WALL = 10.0            # wall thickness of the rest of the mount and cover
MOUNT_LENGTH = 125.0         # overall length of the mount
MOUNT_FOOT_HEIGHT = 5.0      # radial height of the outward foot at the chamber end
MOUNT_FOOT_THICKNESS = 6.0   # axial thickness of that foot
COVER_LENGTH = 68.0          # length of the cover (= where the mount's full tube starts)
TONGUE_LENGTH = 33.3         # length of the cover's tongue that slides into the groove
TONGUE_THICKNESS = 5.0       # radial thickness of the tongue
JOINT_CLEARANCE = 0.3        # gap around the tongue inside the groove

# ---- Middle segments (2) ----------------------------------------------------
SEGMENT_COUNT = 2            # how many middle segments
SEGMENT_LENGTH = 70.0        # overall length of each segment
SEGMENT_WALL = 10.0          # wall thickness of each segment
SEGMENT_LIP_THICKNESS = 6.0  # axial thickness of the inward lip at the camera end
SEGMENT_FOOT_HEIGHT = 5.0    # radial height of the outward foot at the chamber end
SEGMENT_FOOT_THICKNESS = 6.0 # axial thickness of that foot

# ---- Base (3) ---------------------------------------------------------------
BASE_LENGTH = 75.0           # overall length of the base
BASE_WALL = 10.0             # wall thickness of the base
BASE_LIP_THICKNESS = 6.0     # axial thickness of the inward lip at the camera end

# ---- Fit and position -------------------------------------------------------
CLEARANCE = 0.5              # radial gap between each part and the one sliding inside it
EXTENSION = 1.0              # 1 = fully extended (each foot against the next lip), 0 = collapsed

# ---- Size -------------------------------------------------------------------
SCALE = 1.0                  # uniform scale for the whole finished model

# ---- Display ----------------------------------------------------------------
FACETS = 128                 # facets around the axis (keep it a multiple of 4)
EXPLODE = 0.0                # mm (after scaling) to pull the parts apart for viewing
CUTAWAY = True               # remove the -Y half of every part to show the cross-section
MOUNT_COLOR = (0.90, 0.35, 0.05)                         # orange
COVER_COLOR = (0.05, 0.15, 0.70)                         # blue
SEGMENT_COLORS = [(0.25, 0.55, 0.90), (0.60, 0.80, 1.00)]  # light blue, lighter blue (repeats)
BASE_COLOR = (0.15, 0.55, 0.15)                          # green
COLLECTION_NAME = "Model Telescope"


# =============================================================================
# DERIVED GEOMETRY  (profiles are (radius, axial position) pairs)
# =============================================================================

def derived():
    """Every radius and axial position the parts are built from."""
    g = {}
    g["r_out"] = MOUNT_OUTER_DIAMETER / 2
    g["r_neck"] = g["r_out"] - MOUNT_NECK_WALL
    g["r_bore"] = g["r_out"] - MOUNT_WALL
    g["r_foot"] = g["r_out"] + MOUNT_FOOT_HEIGHT
    r_mid = (g["r_bore"] + g["r_out"]) / 2
    g["tongue_in"] = r_mid - TONGUE_THICKNESS / 2
    g["tongue_out"] = r_mid + TONGUE_THICKNESS / 2
    g["groove_in"] = g["tongue_in"] - JOINT_CLEARANCE
    g["groove_out"] = g["tongue_out"] + JOINT_CLEARANCE
    g["groove_depth"] = TONGUE_LENGTH + JOINT_CLEARANCE

    # Each tube is sized from the part that slides inside it: its lip clears
    # that part's tube and its bore clears that part's foot.
    tubes = []
    inner_out, inner_foot, inner_foot_t = g["r_out"], g["r_foot"], MOUNT_FOOT_THICKNESS
    x_end = MOUNT_LENGTH  # chamber end of the part inside
    for i in range(SEGMENT_COUNT + 1):
        base = i == SEGMENT_COUNT
        t = {
            "name": "Telescope Base" if base else f"Telescope Segment {i + 1}",
            "base": base,
            "length": BASE_LENGTH if base else SEGMENT_LENGTH,
            "lip_t": BASE_LIP_THICKNESS if base else SEGMENT_LIP_THICKNESS,
            "foot_h": 0.0 if base else SEGMENT_FOOT_HEIGHT,
            "foot_t": 0.0 if base else SEGMENT_FOOT_THICKNESS,
            "r_lip": inner_out + CLEARANCE,
            "r_bore": inner_foot + CLEARANCE,
        }
        t["r_out"] = t["r_bore"] + (BASE_WALL if base else SEGMENT_WALL)
        t["r_foot"] = t["r_out"] + t["foot_h"]
        # How far the inner part's foot can slide between this lip and this end.
        t["travel"] = t["length"] - t["lip_t"] - inner_foot_t
        t["x"] = x_end - (t["lip_t"] + inner_foot_t + (1 - EXTENSION) * t["travel"])
        tubes.append(t)
        inner_out, inner_foot, inner_foot_t = t["r_out"], t["r_foot"], t["foot_t"]
        x_end = t["x"] + t["length"]
    g["tubes"] = tubes
    g["total_length"] = x_end
    return g


def check_dimensions(g):
    problems = []

    def need(ok, msg):
        if not ok:
            problems.append(msg)

    need(SCALE > 0, "SCALE must be greater than 0")
    need(0 <= EXTENSION <= 1, "EXTENSION must be between 0 and 1")
    need(isinstance(SEGMENT_COUNT, int) and SEGMENT_COUNT >= 0, "SEGMENT_COUNT must be a whole number >= 0")
    need(g["r_neck"] > 1 and g["r_bore"] > 1, "MOUNT_NECK_WALL and MOUNT_WALL must be smaller than the mount radius")
    need(MOUNT_NECK_LENGTH < COVER_LENGTH, "MOUNT_NECK_LENGTH must be shorter than COVER_LENGTH")
    need(g["groove_in"] > g["r_bore"] + 0.5 and g["groove_out"] < g["r_out"] - 0.5,
         "TONGUE_THICKNESS + 2 * JOINT_CLEARANCE must fit inside MOUNT_WALL with some material left")
    need(COVER_LENGTH + g["groove_depth"] < MOUNT_LENGTH - MOUNT_FOOT_THICKNESS,
         "COVER_LENGTH + TONGUE_LENGTH must be shorter than MOUNT_LENGTH minus the foot")
    positive = ("MOUNT_FOOT_HEIGHT", "MOUNT_FOOT_THICKNESS", "SEGMENT_WALL", "SEGMENT_LIP_THICKNESS",
                "SEGMENT_FOOT_HEIGHT", "SEGMENT_FOOT_THICKNESS", "BASE_WALL", "BASE_LIP_THICKNESS",
                "CLEARANCE", "TONGUE_THICKNESS", "TONGUE_LENGTH")
    for name in positive:
        need(globals()[name] > 0, f"{name} must be greater than 0")
    for t in g["tubes"]:
        need(t["lip_t"] + t["foot_t"] < t["length"], f"{t['name']}: lip + foot are longer than the part")
        need(t["travel"] >= 0, f"{t['name']}: length must be at least its lip plus the foot of the part inside it")
    if problems:
        raise ValueError("Dimension problems:\n  - " + "\n  - ".join(problems))


def clean(profile):
    """Drop repeated points (e.g. when MOUNT_WALL == MOUNT_NECK_WALL)."""
    return [p for i, p in enumerate(profile) if p != profile[i - 1]]


def mount_profile(g):
    """Full-length mount; the top half of the camera end is cut away afterwards."""
    return clean([
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], MOUNT_LENGTH - MOUNT_FOOT_THICKNESS),
        (g["r_foot"], MOUNT_LENGTH - MOUNT_FOOT_THICKNESS),
        (g["r_foot"], MOUNT_LENGTH),
        (g["r_bore"], MOUNT_LENGTH),
        (g["r_bore"], MOUNT_NECK_LENGTH),
        (g["r_neck"], MOUNT_NECK_LENGTH),
    ])


def mount_cutter_profile(g):
    """Top-half region removed from the mount: the cover's space plus the groove."""
    r_in = g["r_neck"] / 2
    r_big = g["r_foot"] + 1
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
    return clean([
        (g["r_neck"], 0.0),
        (g["r_out"], 0.0),
        (g["r_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH),
        (g["tongue_out"], COVER_LENGTH + TONGUE_LENGTH),
        (g["tongue_in"], COVER_LENGTH + TONGUE_LENGTH),
        (g["tongue_in"], COVER_LENGTH),
        (g["r_bore"], COVER_LENGTH),
        (g["r_bore"], MOUNT_NECK_LENGTH),
        (g["r_neck"], MOUNT_NECK_LENGTH),
    ])


def tube_profile(t):
    """Segment or base, axial position measured from its own camera-side face."""
    end = t["length"]
    if t["base"]:
        outside = [(t["r_out"], 0.0), (t["r_out"], end)]
    else:
        outside = [(t["r_out"], 0.0), (t["r_out"], end - t["foot_t"]),
                   (t["r_foot"], end - t["foot_t"]), (t["r_foot"], end)]
    return [(t["r_lip"], 0.0)] + outside + [(t["r_bore"], end), (t["r_bore"], t["lip_t"]),
                                             (t["r_lip"], t["lip_t"])]


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
    steps = FACETS if full else max(2, round(FACETS * sweep / 360.0))
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
# BUILD
# =============================================================================

def main():
    g = derived()
    check_dimensions(g)
    setup_units()
    coll = clean_collection(COLLECTION_NAME)

    mount = revolve("Telescope Mount", mount_profile(g), coll)
    boolean(mount, revolve("CoverCutter", mount_cutter_profile(g), coll, start=0, sweep=180))
    cover = revolve("Telescope Cover", cover_profile(g), coll, start=0, sweep=180)

    # (object, colour, axial position before scaling, explode step)
    parts = [(mount, MOUNT_COLOR, 0.0, 0), (cover, COVER_COLOR, 0.0, -1)]
    for i, t in enumerate(g["tubes"]):
        color = BASE_COLOR if t["base"] else SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
        parts.append((revolve(t["name"], tube_profile(t), coll), color, t["x"], i + 1))

    for obj, color, x, step in parts:
        obj.data.transform(Matrix.Scale(SCALE, 4))
        obj.location.x = x * SCALE + step * EXPLODE
    cover.location.z = EXPLODE

    for obj, color, _, _ in parts:
        if CUTAWAY:
            cutaway(obj, coll)
        finish_object(obj, matte_material(f"{obj.name} Matte", color))
    print(f"Built {COLLECTION_NAME}: length {g['total_length'] * SCALE:.1f} mm, "
          f"largest OD {2 * g['tubes'][-1]['r_out'] * SCALE:.1f} mm")


if __name__ == "__main__" and bpy is not None:
    main()
