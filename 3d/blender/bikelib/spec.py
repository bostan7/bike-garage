"""Measurements of Toni's SCOTT Scale 980 (Dark Grey, size L, article 280483).

Sources: docs/BIKE-SPECS.md and docs/research/COMPONENTS.md.
Blender axes: +X forward, +Y = left / non-drive side, +Z up. Ground at z = 0. Units: metres.
"""
from math import radians, sin, cos, sqrt
from mathutils import Vector

MM = 0.001

# --- Mesh detail ----------------------------------------------------------------------------
# Segment counts in bikelib are written for DETAIL = 1.0 (model v3, ~580k triangles).
# Raise or lower it for the whole bike, or for single parts in DETAIL_PER_PART (e.g. {"tire_front": 1.5}).
DETAIL = 1.0
DETAIL_PER_PART = {}


def seg(part_name, n, minimum=3):
    """Segment count n scaled by the detail setting of this part."""
    return max(minimum, int(round(n * DETAIL_PER_PART.get(part_name, DETAIL))))


# --- Official SCOTT "Scale Alloy" geometry, size L ---------------------------------------
HTA = 69.5            # head tube angle (deg)
STA = 73.6            # seat tube angle (deg)
HT_LEN = 115.0
REACH = 437.7
STACK = 619.4
BB_DROP = 58.0
BB_HEIGHT = 312.0
CHAINSTAY = 440.0
WHEELBASE = 1138.2
SEAT_TUBE = 480.0


STOCK_TYRE_R = 370.0     # mm, = BB_HEIGHT + BB_DROP with the stock 29 x 2.25 tyres
TYRE_R_MM = 372.0        # Toni's Rekon Race 29 x 2.35: ~2 mm taller (📐 estimate)
GROUND_LIFT = TYRE_R_MM - STOCK_TYRE_R    # the whole bike sits this much higher on the bigger tyres


def P(x, z, y=0.0):
    """Bike-plane millimetres (origin = BB centre, +x forward, +z up, +y left) -> Blender metres."""
    return Vector((x * MM, y * MM, (z + BB_HEIGHT + GROUND_LIFT) * MM))


REAR_X = -sqrt(CHAINSTAY ** 2 - BB_DROP ** 2)        # -436.2
FRONT_X = WHEELBASE + REAR_X                          # 702.0

BB = P(0, 0)
REAR_AXLE = P(REAR_X, BB_DROP)
FRONT_AXLE = P(FRONT_X, BB_DROP)
HT_TOP = P(REACH, STACK)
AXIS_DOWN = Vector((cos(radians(HTA)), 0.0, -sin(radians(HTA))))   # steering axis, pointing down
AXIS_UP = -AXIS_DOWN
AXIS_FWD = Vector((sin(radians(HTA)), 0.0, cos(radians(HTA))))     # perpendicular to the axis, forward
HT_BOT = HT_TOP + AXIS_DOWN * (HT_LEN * MM)
SEAT_DIR = Vector((-cos(radians(STA)), 0.0, sin(radians(STA))))    # up the seat tube
ST_TOP = BB + SEAT_DIR * (SEAT_TUBE * MM)


def on_axis(dist_mm_from_ht_top):
    """Point on the steering axis, measured downwards from the head tube top (negative = above)."""
    return HT_TOP + AXIS_DOWN * (dist_mm_from_ht_top * MM)


def on_seat_axis(dist_mm_from_bb):
    return BB + SEAT_DIR * (dist_mm_from_bb * MM)


# --- Frame junctions (calibrated against the official studio photo) -------------------------
TT_AT_ST = 95.0       # top tube meets the seat tube this far below the seat tube top (mm)
TT_AT_HT = 22.0       # top tube centre this far below the head tube top
DT_AT_HT = 88.0       # down tube centre meets the head tube this far below its top
SS_AT_ST = 105.0      # seat stays meet the seat tube this far below its top

# --- Wheels & tyres (stock wheels; Toni's Maxxis Rekon Race 29 x 2.35 EXO TR, ETRTO 60-622) ---
TYRE_R = TYRE_R_MM * MM                    # outer radius over the centre knobs
TYRE_HALF_W = 0.0295                       # ~59 mm casing on the stock rim (📐)
RIM_BEAD_R = 0.311                         # 622 mm BSD
SPOKES = 32
FRONT_FLANGE_Y = (0.034, -0.034)           # (disc side, other side)
REAR_FLANGE_Y = (0.035, -0.020)            # (disc side, drive side)
FRONT_OLD = 0.100
REAR_OLD = 0.141
FRONT_ROTOR_R = 0.090                      # 180 mm
REAR_ROTOR_R = 0.080                       # 160 mm
FRONT_ROTOR_Y = 0.044
REAR_ROTOR_Y = 0.054

# --- Fork (Suntour XCR32 RL-R, 100 mm) --------------------------------------------------------
FORK_OFFSET = 51.0         # implied by the official geometry
FORK_LEG_Y = 0.0625        # half of the leg spacing
STANCHION_R = 0.016
FORK_SEAL_FROM_AXLE = 0.352
LOWER_CUP = 2.5            # mm, lower headset cup below the head tube

# --- Drivetrain --------------------------------------------------------------------------------
CHAIN_PITCH = 0.0127
CHAINRING_T = 32
CHAINLINE_Y = -0.052
CASSETTE = [51, 45, 39, 33, 28, 24, 21, 18, 16, 14, 12, 10]
COG_PITCH_Y = 0.00376
LARGEST_COG_Y = -0.0236
CHAIN_ON = 10              # cog the chain sits on (as in SCOTT's studio photo)
CRANK_LEN = 0.175          # to verify on the bike (stamped inside the arm)
CRANK_ANGLE = -8.0         # drive arm angle in degrees (0 = pointing forward), as in the photo

# Rear derailleur positions relative to the rear axle (x, z in metres), measured on the studio photo
# (1.0415 px/mm) with the chain on the 10T cog.
RD_UPPER_PULLEY = (-0.0125, -0.1104)
RD_LOWER_PULLEY = (-0.0487, -0.1890)
RD_CLUTCH = (0.0278, -0.1075)
RD_MOUNT_BOLT = (-0.0220, -0.0340)
Q_HALF = 0.0892            # half of the 178.5 mm Q-factor
PULLEY_T = 13


def pitch_r(teeth):
    return CHAIN_PITCH / (2.0 * sin(3.141592653589793 / teeth))


def cog_y(teeth):
    return LARGEST_COG_Y - CASSETTE.index(teeth) * COG_PITCH_Y


# --- Cockpit -----------------------------------------------------------------------------------
HEADSET_COVER = 8.0        # mm above the head tube
SPACERS = 15.0             # mm of spacers under the stem (count on the bike)
STEM_STACK = 40.0          # stem clamp height on the steerer
STEM_LEN = 0.075           # to verify (printed on the stem)
STEM_ANGLE = 6.0
BAR_HALF = 0.370           # 740 mm bar
BAR_SWEEP = 9.0
GRIP_LEN = 0.130

# --- Seat --------------------------------------------------------------------------------------
SADDLE_HEIGHT = 750.0      # BB centre -> top of saddle along the seat axis (mm), rider ~185 cm
SEATPOST_R = 0.0158        # 31.6 mm
