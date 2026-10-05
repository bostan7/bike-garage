package dev.toni.scalebike.garage

import android.content.Context
import android.view.Choreographer
import android.view.SurfaceView
import android.view.View as AndroidView
import com.google.android.filament.IndirectLight
import com.google.android.filament.Skybox
import com.google.android.filament.Texture
import com.google.android.filament.View
import com.google.android.filament.utils.HDRLoader
import com.google.android.filament.utils.IBLPrefilterContext
import com.google.android.filament.utils.ModelViewer
import com.google.android.filament.utils.Utils
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Filament renderer for the 3D garage: loads the bike (Draco-compressed bike.glb from the assets),
 * lights it with an image-based light made on the phone from a garage HDR, and draws frames while the
 * screen is visible. ModelViewer gives the orbit / zoom camera.
 */
class GarageRenderer(context: Context, surfaceView: SurfaceView) : Choreographer.FrameCallback {

    companion object {
        init {
            Utils.init()
        }

        private const val IBL_INTENSITY = 35_000f
    }

    private val choreographer = Choreographer.getInstance()
    private var released = false

    init {
        // ModelViewer frees itself (model, loaders, engine) when the view is detached. Our own Filament
        // objects must go first, while the engine still exists, so this hook is added before ModelViewer's.
        surfaceView.addOnAttachStateChangeListener(object : AndroidView.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(v: AndroidView) = Unit
            override fun onViewDetachedFromWindow(v: AndroidView) = releaseOwnResources()
        })
    }

    val viewer = ModelViewer(surfaceView)
    private var reflections: Texture? = null
    private var indirectLight: IndirectLight? = null
    private var skybox: Skybox? = null
    private var running = false

    init {
        surfaceView.setOnTouchListener(viewer)
        viewer.loadModelGlb(readAsset(context, "bike.glb"))
        viewer.transformToUnitCube()
        setupEnvironment(context)
        setupView()
    }

    private fun setupEnvironment(context: Context) {
        val engine = viewer.engine
        val equirect = HDRLoader.createTexture(engine, readAsset(context, "envs/garage.hdr"))
            ?: error("could not decode envs/garage.hdr")
        val prefilter = IBLPrefilterContext(engine)
        val toCubemap = IBLPrefilterContext.EquirectangularToCubemap(prefilter)
        val specular = IBLPrefilterContext.SpecularFilter(prefilter)
        val cubemap = toCubemap.run(equirect)
        val filtered = specular.run(cubemap)
        engine.destroyTexture(equirect)
        engine.destroyTexture(cubemap)
        toCubemap.destroy()
        specular.destroy()
        prefilter.destroy()

        reflections = filtered
        indirectLight = IndirectLight.Builder()
            .reflections(filtered)
            .intensity(IBL_INTENSITY)
            .build(engine)
        viewer.scene.indirectLight = indirectLight
        // dark studio background (the garage HDR only lights and reflects, it is not shown)
        skybox = Skybox.Builder().color(0.012f, 0.013f, 0.016f, 1.0f).build(engine)
        viewer.scene.skybox = skybox
    }

    private fun setupView() {
        viewer.view.apply {
            antiAliasing = View.AntiAliasing.FXAA
            multiSampleAntiAliasingOptions = multiSampleAntiAliasingOptions.apply { enabled = true; sampleCount = 4 }
            ambientOcclusionOptions = ambientOcclusionOptions.apply { enabled = true }
            bloomOptions = bloomOptions.apply { enabled = true; strength = 0.12f }
        }
    }

    fun resume() {
        if (running || released) return
        running = true
        choreographer.postFrameCallback(this)
    }

    fun pause() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    override fun doFrame(frameTimeNanos: Long) {
        if (!running || released) return
        choreographer.postFrameCallback(this)
        viewer.render(frameTimeNanos)
    }

    /** Called when the composable leaves: stop drawing. The detach hooks free the Filament objects. */
    fun destroy() = pause()

    private fun releaseOwnResources() {
        if (released) return
        released = true
        pause()
        val engine = viewer.engine
        viewer.scene.indirectLight = null
        viewer.scene.skybox = null
        indirectLight?.let { engine.destroyIndirectLight(it) }
        reflections?.let { engine.destroyTexture(it) }
        skybox?.let { engine.destroySkybox(it) }
        indirectLight = null
        reflections = null
        skybox = null
    }

    private fun readAsset(context: Context, name: String): ByteBuffer {
        val bytes = context.assets.open(name).use { it.readBytes() }
        return ByteBuffer.allocateDirect(bytes.size).order(ByteOrder.nativeOrder()).apply {
            put(bytes)
            flip()
        }
    }
}
