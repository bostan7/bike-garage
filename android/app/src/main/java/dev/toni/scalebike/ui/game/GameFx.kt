package dev.toni.scalebike.ui.game

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import android.os.Build
import android.provider.Settings
import android.view.HapticFeedbackConstants
import android.view.View
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import dev.toni.scalebike.R

/**
 * Menu sounds (SoundPool, small WAVs from `design/sounds/make_sounds.py`) and vibration (view haptics, so no
 * VIBRATE permission is needed). The SOUND toggle mutes the sounds only and is remembered in SharedPreferences.
 */
class GameFx(context: Context, private val view: View) {
    private val prefs = context.getSharedPreferences("game_ui", Context.MODE_PRIVATE)
    var soundOn by mutableStateOf(prefs.getBoolean(KEY_SOUND, true))
        private set

    private val pool = SoundPool.Builder()
        .setMaxStreams(4)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()
    private val loaded: MutableSet<Int> = java.util.concurrent.ConcurrentHashMap.newKeySet()
    private val whooshId: Int
    private val tickId: Int
    private val confirmId: Int
    private val holdId: Int
    private val lightId: Int
    private var holdStream = 0

    init {
        pool.setOnLoadCompleteListener { _, id, status -> if (status == 0) loaded += id }
        whooshId = pool.load(context, R.raw.whoosh, 1)
        tickId = pool.load(context, R.raw.tick, 1)
        confirmId = pool.load(context, R.raw.confirm, 1)
        holdId = pool.load(context, R.raw.hold, 1)
        lightId = pool.load(context, R.raw.light_on, 1)
    }

    /** True when the system "Remove animations" setting is on (animator duration scale 0). */
    val reducedMotion: Boolean = runCatching {
        Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f) == 0f
    }.getOrDefault(false)

    /** ACCESSORIES chip: show the mudguards, lights, lock… on the 3D bike (remembered like SOUND). */
    var accessoriesOn by mutableStateOf(prefs.getBoolean(KEY_ACCESSORIES, true))
        private set

    fun toggleAccessories() {
        accessoriesOn = !accessoriesOn
        prefs.edit().putBoolean(KEY_ACCESSORIES, accessoriesOn).apply()
        tick()
    }

    fun toggleSound() {
        soundOn = !soundOn
        prefs.edit().putBoolean(KEY_SOUND, soundOn).apply()
        if (soundOn) tick()
    }

    private fun play(id: Int, volume: Float = 1f, rate: Float = 1f): Int =
        if (soundOn && id in loaded) pool.play(id, volume, volume, 1, 0, rate) else 0

    private fun haptic(constant: Int) {
        view.performHapticFeedback(constant)
    }

    /** Mode change: whoosh + a firm click. */
    fun whoosh() {
        play(whooshId)
        haptic(HapticFeedbackConstants.CONTEXT_CLICK)
    }

    /** Menu move / small action. */
    fun tick() {
        play(tickId, 0.8f)
        haptic(if (Build.VERSION.SDK_INT >= 34) HapticFeedbackConstants.SEGMENT_TICK else HapticFeedbackConstants.CLOCK_TICK)
    }

    /** Hold-to-confirm finished. */
    fun confirm() {
        stopHold()
        play(confirmId)
        haptic(HapticFeedbackConstants.CONFIRM)
    }

    /** Rising tone while a hold button is pressed. */
    fun startHold() {
        stopHold()
        holdStream = play(holdId)
        haptic(if (Build.VERSION.SDK_INT >= 34) HapticFeedbackConstants.GESTURE_THRESHOLD_ACTIVATE else HapticFeedbackConstants.VIRTUAL_KEY)
    }

    fun stopHold() {
        if (holdStream != 0) pool.stop(holdStream)
        holdStream = 0
    }

    /** Intro: a light group switches on (index 0..4 → 80..120 Hz thunk like the prototype). */
    fun lightOn(index: Int) {
        play(lightId, 1f, ((80 + index.coerceIn(0, 4) * 10) / 100f))
        haptic(HapticFeedbackConstants.LONG_PRESS)
    }

    fun release() {
        stopHold()
        pool.release()
    }

    private companion object {
        const val KEY_SOUND = "sound_on"
        const val KEY_ACCESSORIES = "accessories_on"
    }
}

@Composable
fun rememberGameFx(): GameFx {
    val context = LocalContext.current
    val view = LocalView.current
    val fx = remember(view) { GameFx(context.applicationContext, view) }
    DisposableEffect(fx) { onDispose { fx.release() } }
    return fx
}
