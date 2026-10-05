package dev.toni.scalebike.garage

import android.view.SurfaceView
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner

/** The 3D garage view: a Filament SurfaceView that renders only while the screen is resumed. */
@Composable
fun Garage3D(modifier: Modifier = Modifier) {
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var renderer by remember { mutableStateOf<GarageRenderer?>(null) }

    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            SurfaceView(ctx).also { surface ->
                renderer = GarageRenderer(ctx, surface).also {
                    if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) it.resume()
                }
            }
        },
    )

    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> renderer?.resume()
                Lifecycle.Event.ON_PAUSE -> renderer?.pause()
                else -> Unit
            }
        }
        lifecycle.addObserver(observer)
        onDispose {
            lifecycle.removeObserver(observer)
            renderer?.destroy()
            renderer = null
        }
    }
}
