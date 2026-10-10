"""All garage measurements (metres). Blender axes: +X forward, +Y left (non-drive side), +Z up, ground z = 0.

Layout copied from the approved web prototype (design/prototype/template.html, three.js Y-up):
three.js (x, y, z) -> Blender (x, -z, y). The prototype's back wall at z = -3.4 is Blender y = +3.4.
The app camera mostly looks at the bike's drive side, i.e. from -Y towards +Y.
"""
from mathutils import Vector

# room (inner faces of the walls)
X0, X1 = -4.5, 4.5          # left / right wall
Y0, Y1 = -5.6, 3.4          # front wall (door) / back wall (shutter, sign)
H = 3.6                     # ceiling height
WALL_T = 0.20               # wall / ceiling thickness (only seen from inside)

# turntable (the bike stands on it; the app spins it around its origin)
TT = Vector((0.133, 0.0, 0.0))
TT_R = 1.0                  # top radius
TT_R_BASE = 1.04            # bottom radius (slanted side)
TT_TOP = 0.035              # top surface height; the app puts the bike at z = 0.036
RING_R = 0.965              # neon ring radius (sits half sunk into the top edge)
RING_TUBE = 0.006

# floor: one 3.2 m slab texture; the centre slab is centred on the turntable, so the saw-cut joints
# run just outside the safety-stripe square
SLAB = 3.2
SLAB_ORIGIN = (TT.x - SLAB / 2, TT.y - SLAB / 2)

# safety stripes around the turntable bay (centre line of the stripe), stripe width, diagonal band period
BAY = 2.9
STRIPE_W = 0.09
STRIPE_PERIOD = 0.10
STRIPE_Z = 0.002

# shutter on the back wall
SHUTTER_X = (-1.40, 2.00)   # opening between the guide rails
SHUTTER_TOP = 2.70
SLAT = 0.075                # slat pitch

# neon
NEON_HEX = "#D2F500"        # the bike's neon yellow
LED_HEX = "#E8F2FF"         # cool white hexagon LEDs
SIGN_CORE_HEX = "#F1FF9E"   # yellow-white core of the sign letters
NEON_STRENGTH = 6.0         # glTF KHR_materials_emissive_strength
LED_STRENGTH = 4.0
SIGN_STRENGTH = 8.0
NEON_TUBE_R = 0.0125
NEON_BASE_Z = 0.05

# hexagon LED ceiling (prototype: r 0.42, cells whose centre is within 2.1 m of the turntable)
HEX_R = 0.42
HEX_LIMIT = 2.1
HEX_Z = H - 0.04
HEX_BAR = (0.032, 0.03)     # bar width, height

# "SCALE 980" sign on the back wall (prototype centre -2.55, moved 0.2 m left to clear the shutter box)
SIGN_CENTER = Vector((-2.75, Y1, 2.55))
SIGN_TEXT = "SCALE 980"
SIGN_WIDTH = 2.15
SIGN_FONT = "C:/Windows/Fonts/impact.ttf"   # condensed black; sheared below for the italic
SIGN_SHEAR = 0.22

# door on the front wall
DOOR_X = -2.4
DOOR_W, DOOR_H = 0.95, 2.10

# props (placed against the walls, all > 3 m from the turntable centre)
PEG_Y = (-0.40, 2.80)       # pegboard on the left wall
PEG_Z = (0.95, 2.55)
BENCH_Y = (-0.10, 2.50)     # workbench under the pegboard
BENCH_DEPTH = 0.70
BENCH_TOP = 0.95
CHEST_Y = (-1.35, -0.45)    # tool chest on the left wall
CHEST_DEPTH, CHEST_H = 0.55, 1.10
TYRES_AT = Vector((3.80, 2.40, 0.0))
DRUM_AT = Vector((3.90, 1.40, 0.0))
SHELF_Y = (-3.80, -2.00)    # shelving on the right wall
SHELF_DEPTH, SHELF_H = 0.45, 2.00
