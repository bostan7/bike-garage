package dev.toni.scalebike.garage

/**
 * Contract between the 3D garage (Filament, `GarageScene`) and the game UI (`ui/game`).
 *
 * All touch handling lives in the UI: it decides what is an edge swipe (change mode), a drag (orbit),
 * a pinch (zoom) or a tap, and calls the matching method here. The garage never installs its own touch listener.
 * Part names are the 23 slot names shared with `SeedData` and `bike.glb` (see "Part slots" in the root README.md).
 * Every method must be safe to call from the main thread at any time, also before the model has loaded
 * (calls made before loading are applied once it is ready).
 */
interface GarageController {
    /** Turn the turntable and move the camera to the preset of a mode (smooth fly, ~0.9 s). */
    fun showMode(mode: GarageMode)

    /** Fly the camera to frame a group of parts (a PARTS area such as "Brakes"); the turntable goes to 0 (drive side). */
    fun flyToArea(slots: List<String>)

    /** Fly the camera close to one part. */
    fun flyToPart(slot: String)

    /** Pulsing neon-yellow highlight on one part, or none. */
    fun setSelected(slot: String?)

    /** Shows or hides every accessory (`acc_*` nodes: mudguards, lights, bell, lock, reflectors). */
    fun setAccessoriesVisible(visible: Boolean)

    /** Status view: every part glows by its condition (green / amber / red); off = no glow. */
    fun setStatusView(enabled: Boolean, health: Map<String, PartHealth>)

    /**
     * How much of the screen width the open menus cover on the left and right (0..1), so the bike is shifted
     * into the free space between them (camera shift, not a move).
     */
    fun setPanelInsets(leftFraction: Float, rightFraction: Float)

    /** Double-tap: back to the current mode's camera preset. */
    fun resetCamera()

    /** Drag on the bike (pixels since the last call): orbit around the bike. */
    fun orbit(dxPx: Float, dyPx: Float)

    /** Pinch: zoom by this factor (>1 = closer). */
    fun zoom(factor: Float)

    /** Tap at a screen point (pixels): picks a part and reports it through [onPartTapped]. */
    fun tap(xPx: Float, yPx: Float)

    /** Any touch: restarts the idle timer (the turntable spins slowly after ~6 s without touches in GARAGE). */
    fun onUserInteraction()

    /**
     * Intro: garage dark, ceiling hex lights flicker on, then the spotlights one by one, then the neon, while the
     * camera sweeps around the bike (~4.8 s). [onLightOn] fires as each light group switches on (for sound and
     * vibration); [onFinished] at the end. [skipIntro] jumps to the end state.
     */
    fun playIntro(onLightOn: (index: Int) -> Unit, onFinished: () -> Unit)
    fun skipIntro()

    /** Set by the UI: called with the slot name when [tap] hits a part. */
    var onPartTapped: ((String) -> Unit)?
}

enum class GarageMode { SERVICE_LOG, GARAGE, PARTS, WORKSHOP, BIKE }

enum class PartHealth { OK, SOON, OVER, NONE }
