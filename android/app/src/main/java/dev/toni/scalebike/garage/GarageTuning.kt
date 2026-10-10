package dev.toni.scalebike.garage

/**
 * Every number worth adjusting on the phone, in one place. Units: metres, radians, seconds,
 * Filament light units (candela for the spots), linear RGB.
 * Values follow the approved web prototype (design/prototype/template.html).
 */
internal object GarageTuning {
    // ---------------------------------------------------------------- scene layout (glTF coordinates)
    /** Turntable centre (x) and the height the bike stands at (turntable top is 0.035). */
    const val TURNTABLE_X = 0.133
    const val BIKE_Y = 0.036f

    /** Room box the camera must stay inside (prototype: 9 x 9 x 3.6 m, back wall at z = -3.4). */
    const val ROOM_MIN_X = -4.25
    const val ROOM_MAX_X = 4.25
    const val ROOM_MIN_Z = -3.15
    const val ROOM_MAX_Z = 5.35
    const val ROOM_MAX_Y = 3.4
    const val CAMERA_MIN_Y = 0.06

    // ---------------------------------------------------------------- render quality / performance
    /** The surface is rendered at this fraction of the view size and scaled up by the compositor. */
    const val RENDER_SCALE = 0.8f
    const val DYNAMIC_RES_MIN = 0.6f
    const val MSAA_SAMPLES = 4

    /** Frames are drawn every vsync while active; at most every IDLE_FRAME_NS when only the turntable /
     * highlight animate (~60 fps on the 120 Hz panel), and every STATIC_FRAME_NS when nothing moves. */
    const val IDLE_FRAME_NS = 12_000_000L
    const val STATIC_FRAME_NS = 100_000_000L
    /** How long after the last touch the loop stays at full rate. */
    const val ACTIVE_HOLD_NS = 1_500_000_000L

    // ---------------------------------------------------------------- camera
    const val FOV_DEG = 34.0
    const val NEAR = 0.05
    const val FAR = 40.0
    /** Indoor exposure: f/2.8, 1/60 s, ISO 800 (EV100 ~5.9). Raise ISO to brighten everything. */
    const val APERTURE = 2.8f
    const val SHUTTER = 1f / 60f
    const val ISO = 800f

    const val MIN_DIST = 0.45
    const val MAX_DIST = 3.2
    const val MIN_POLAR = 0.08
    const val MAX_POLAR = Math.PI * 0.52
    /** Drag speed like three.js OrbitControls (2 pi * dx / viewHeight * speed). */
    const val ROTATE_SPEED = 0.7
    /** OrbitControls damping factor at 60 fps (fraction of the remaining motion applied per frame). */
    const val DAMPING = 0.08
    const val FLY_MS = 900.0
    const val IDLE_SPIN_DELAY_NS = 6_000_000_000L
    const val IDLE_SPIN_SPEED = 0.18  // rad/s
    /** Speed of the view shift when panels open/close (prototype: 8/s exponential). */
    const val SHIFT_RATE = 8.0

    /** Mode presets: turntable yaw and camera distance (camera at 0.13 + sin(0.35)*d, 1.0, cos(0.35)*d). */
    fun modeYaw(mode: GarageMode): Double = when (mode) {
        GarageMode.SERVICE_LOG -> -0.85
        GarageMode.GARAGE -> 0.55
        GarageMode.PARTS -> 0.0
        GarageMode.WORKSHOP -> 1.35
        GarageMode.BIKE -> 2.6
    }

    fun modeDist(mode: GarageMode): Double = when (mode) {
        // the menu modes share the screen with a ~40 % wide panel, so the bike must fit in the other 60 %
        GarageMode.SERVICE_LOG -> 3.0
        GarageMode.GARAGE -> 2.6
        GarageMode.PARTS -> 3.0
        GarageMode.WORKSHOP -> 2.9
        GarageMode.BIKE -> 2.9
    }

    const val PRESET_ANGLE = 0.35
    const val PRESET_CAM_Y = 0.95
    const val PRESET_TARGET_X = 0.13
    /** Below the bike's middle, so the wheels sit above the mode tabs (phone test 2026-10-10). */
    const val PRESET_TARGET_Y = 0.47

    /** Area / part framing: distance = max(minD, bbox diagonal * k), direction (0.28, 0.32, 1). */
    const val AREA_K = 1.25
    const val AREA_MIN_D = 0.55
    const val PART_K = 1.4
    const val PART_MIN_D = 0.42

    // ---------------------------------------------------------------- lights (candela; colours are sRGB hex)
    // phone test 2026-10-10: the rim washed the turntable lime and the dark-grey bike was hard to read,
    // so the rim is ~half and the front fill brighter
    const val KEY_CD = 4200f      // white, above the bike, casts the soft shadow
    const val FRONT_CD = 3800f    // cool white fill from the front-right
    const val RIM_CD = 2400f      // neon yellow #D2F500 from behind-left
    const val WALL_CD = 1800f     // cool blue wash on the back wall
    /** Image-based light from envs/garage.hdr, kept low so the blacks are not flat. */
    const val IBL_INTENSITY = 6f
    const val SHADOW_MAP_SIZE = 1024
    const val VSM_BLUR = 6f

    val SKY = floatArrayOf(0.0016f, 0.0018f, 0.0024f)  // ~#050608 in linear

    // ---------------------------------------------------------------- post-processing
    const val BLOOM_STRENGTH = 0.12f
    const val BLOOM_LEVELS = 6
    const val BLOOM_RESOLUTION = 384
    const val SSAO_RADIUS = 0.25f
    const val SSAO_INTENSITY = 1.0f
    const val SSR_THICKNESS = 0.1f
    const val SSR_BIAS = 0.01f
    const val SSR_MAX_DISTANCE = 3.0f
    const val SSR_STRIDE = 2.0f
    const val FOG_START = 3.5f
    const val FOG_DENSITY = 0.06f
    const val FOG_HEIGHT_FALLOFF = 0.4f
    const val FOG_MAX_OPACITY = 0.55f
    const val VIGNETTE_MID = 0.6f
    const val CONTRAST = 1.05f
    const val SATURATION = 1.05f

    // ---------------------------------------------------------------- part glow (emissive, linear RGB * gain)
    // phone test: 0.28 painted the whole part solid lime; these keep the real colour readable under the glow
    const val SELECT_GLOW_BASE = 0.08f
    const val SELECT_GLOW_PULSE = 0.05f
    const val SELECT_PULSE_SPEED = 4.0  // rad/s of the sine
    const val STATUS_GLOW_OK = 0.05f
    const val STATUS_GLOW_WARN = 0.15f
    /** Global multiplier on all part glows (raise if the highlight is too weak on the phone). */
    const val GLOW_GAIN = 1.0f

    const val SELECT_HEX = 0xD2F500
    const val OK_HEX = 0x3AD98B
    const val SOON_HEX = 0xFFB020
    const val OVER_HEX = 0xFF4D4F

    // ---------------------------------------------------------------- intro timeline (seconds)
    const val INTRO_HEX_ON = 0.5
    const val INTRO_LIGHTS_START = 0.9
    const val INTRO_LIGHT_STEP = 0.45
    const val INTRO_LIGHT_RAMP = 0.12
    const val INTRO_NEON_ON = 3.0
    const val INTRO_NEON_RAMP = 0.4
    const val INTRO_SWEEP = 4.6
    const val INTRO_END = 4.8
    const val INTRO_START_ANGLE = -1.9
    const val INTRO_START_DIST = 3.4
    const val INTRO_START_Y = 0.45

    /** sRGB hex -> linear RGB. */
    fun linear(hex: Int): FloatArray {
        fun ch(v: Int): Float {
            val c = v / 255f
            return if (c <= 0.04045f) c / 12.92f else Math.pow(((c + 0.055f) / 1.055f).toDouble(), 2.4).toFloat()
        }
        return floatArrayOf(ch(hex shr 16 and 0xFF), ch(hex shr 8 and 0xFF), ch(hex and 0xFF))
    }
}
