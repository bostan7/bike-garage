package dev.toni.scalebike.garage

import android.view.SurfaceView
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner

/**
 * The 3D garage: a Filament SurfaceView that renders only while the screen is resumed.
 * It has no touch listener; the UI drives it through the [GarageController] given to [onReady]
 * (called once, right after creation; the model may still be loading, calls are queued).
 */
@Composable
fun GarageView(modifier: Modifier = Modifier, onReady: (GarageController) -> Unit = {}) {
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val currentOnReady by rememberUpdatedState(onReady)
    var garage by remember { mutableStateOf<GarageScene?>(null) }

    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            SurfaceView(ctx).also { surface ->
                garage = GarageScene(ctx, surface).also {
                    if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) it.resume()
                }
            }
        },
    )

    LaunchedEffect(garage) {
        garage?.let { currentOnReady(it) }
    }

    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> garage?.resume()
                Lifecycle.Event.ON_PAUSE -> garage?.pause()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            // stop drawing; the Filament objects are freed when the SurfaceView leaves the window
            garage?.pause()
            garage = null
        }
    }
}

/** Old entry point kept for `ui/BikeApp.kt`: the garage without UI control. */
@Composable
fun Garage3D(modifier: Modifier = Modifier) = GarageView(modifier)
