package dev.toni.scalebike.garage

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Choreographer
import android.view.Surface
import android.view.SurfaceView
import com.google.android.filament.Box
import com.google.android.filament.Camera
import com.google.android.filament.ColorGrading
import com.google.android.filament.Engine
import com.google.android.filament.EntityManager
import com.google.android.filament.IndirectLight
import com.google.android.filament.LightManager
import com.google.android.filament.Material
import com.google.android.filament.MaterialInstance
import com.google.android.filament.Skybox
import com.google.android.filament.SwapChain
import com.google.android.filament.Texture
import com.google.android.filament.ToneMapper
import com.google.android.filament.View
import com.google.android.filament.Viewport
import com.google.android.filament.android.DisplayHelper
import com.google.android.filament.android.UiHelper
import com.google.android.filament.gltfio.AssetLoader
import com.google.android.filament.gltfio.FilamentAsset
import com.google.android.filament.gltfio.ResourceLoader
import com.google.android.filament.gltfio.UbershaderProvider
import com.google.android.filament.utils.HDRLoader
import com.google.android.filament.utils.IBLPrefilterContext
import com.google.android.filament.utils.Utils
import dev.toni.scalebike.garage.GarageTuning as T
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * The 3D night garage on plain Filament: engine, swap chain (UiHelper), Choreographer frame loop,
 * gltfio loading of `bike.glb` + `garage.glb` (both Draco), spot lights + low IBL, bloom / SSAO / SSR / PCF
 * shadows / fog / ACES, an orbit camera with fly-to tweens, turntable, picking, part glow and the intro.
 *
 * Everything runs on the main thread. Files are read on a background thread; Filament calls stay on main.
 * Filament objects are freed when the SurfaceView is detached from the window (see [release]).
 */
class GarageScene(context: Context, private val surfaceView: SurfaceView) :
    GarageController, Choreographer.FrameCallback {

    companion object {
        init {
            Utils.init()  // loads filament, gltfio and filament-utils native libraries
        }

        private const val TAG = "GarageScene"

        /** Toni's accessories: node names in bike.glb and part slots (category Accessories); hideable as a group. */
        val ACCESSORY_SLOTS: Set<String> = setOf(
            "acc_mudguard_front", "acc_mudguard_rear", "acc_light_rear", "acc_light_front", "acc_light_clip",
            "acc_bell", "acc_lock", "acc_reflectors",
        )

        /** The 23 part slots (SeedData) plus the accessories: node names in bike.glb. */
        val SLOTS: Set<String> = setOf(
            "frame", "fork", "headset", "stem", "handlebar", "grips", "shifter", "brake_front", "brake_rear",
            "rotor_front", "rotor_rear", "crankset", "bottom_bracket", "chain", "cassette", "derailleur", "pedals",
            "wheel_front", "wheel_rear", "tire_front", "tire_rear", "seatpost", "saddle",
        ) + ACCESSORY_SLOTS

        private val NEON_GROUPS = setOf("neon_ring", "neon_strips", "sign")
        private const val HEX_GROUP = "hex_lights"
        private val GARAGE_GROUPS = NEON_GROUPS + setOf(HEX_GROUP, "turntable", "props", "floor", "walls", "shutter", "stripes")
        private val SHADOW_CASTERS = setOf("turntable", "props")

        private const val RATE_STATIC = 0
        private const val RATE_IDLE = 1
        private const val RATE_ACTIVE = 2
        private const val INTRO_EVENTS = 6  // 0 hex lights, 1 key, 2 front, 3 rim, 4 wall wash, 5 neon

        private val ZERO3 = floatArrayOf(0f, 0f, 0f)
        private val SEL = T.linear(T.SELECT_HEX)
        private val OK = T.linear(T.OK_HEX)
        private val SOON = T.linear(T.SOON_HEX)
        private val OVER = T.linear(T.OVER_HEX)

        private fun ease(t: Double) = if (t < 0.5) 4 * t * t * t else 1 - (-2 * t + 2).pow(3) / 2
        private fun ramp(x: Double) = x.coerceIn(0.0, 1.0).toFloat()
    }

    /** One material instance whose emissive we drive, with its original emissive colour. */
    private class Glow(val mi: MaterialInstance, val base: FloatArray, val factorType: Material.Parameter.Type?)

    private class ParamInfo(val factorType: Material.Parameter.Type?, val hasStrength: Boolean)

    private val assets = context.applicationContext.assets
    private val choreographer = Choreographer.getInstance()
    private val mainHandler = Handler(Looper.getMainLooper())

    // ---------------------------------------------------------------- Filament core
    private val engine: Engine = Engine.create()
    private val renderer = engine.createRenderer()
    private val scene = engine.createScene()
    private val view = engine.createView()
    private val cameraEntity = EntityManager.get().create()
    private val camera: Camera = engine.createCamera(cameraEntity)
    private val uiHelper = UiHelper(UiHelper.ContextErrorPolicy.DONT_CHECK)
    private val displayHelper = DisplayHelper(context)
    private var swapChain: SwapChain? = null

    private val materialProvider = UbershaderProvider(engine)
    private val assetLoader = AssetLoader(engine, materialProvider, EntityManager.get())
    private val resourceLoader = ResourceLoader(engine, true)

    private var bikeAsset: FilamentAsset? = null
    private var garageAsset: FilamentAsset? = null
    private val ownedInstances = ArrayList<MaterialInstance>()
    private var colorGrading: ColorGrading? = null
    private var skybox: Skybox? = null
    private var indirectLight: IndirectLight? = null
    private var iblTexture: Texture? = null

    // ---------------------------------------------------------------- lights (key, front, rim, wall)
    private val lightEntities = IntArray(4)
    private val lightFull = floatArrayOf(T.KEY_CD, T.FRONT_CD, T.RIM_CD, T.WALL_CD)
    private val lightLevel = floatArrayOf(1f, 1f, 1f, 1f)

    // ---------------------------------------------------------------- bike / garage bookkeeping
    private var bikeRoot = 0
    private var turntableEntity = 0
    private val turntableBase = FloatArray(16)
    private val entitySlot = HashMap<Int, String>()
    private val slotGlows = HashMap<String, ArrayList<Glow>>()
    private val slotBoxes = HashMap<String, FloatArray>()  // min xyz, max xyz at turntable yaw 0
    private val neonGlows = ArrayList<Glow>()
    private val neonRenderables = ArrayList<Int>()
    private val accessoryRenderables = ArrayList<Int>()
    private var accessoriesOn = true
    private val hexGlows = ArrayList<Glow>()
    private val hexRenderables = ArrayList<Int>()
    private val paramCache = HashMap<Long, ParamInfo>()
    private var neonLevel = 1f
    private var hexVisible = true

    // ---------------------------------------------------------------- state
    private var released = false
    private var running = false
    private var loaded = false
    private var dirty = true
    private var viewW = 0
    private var viewH = 0
    private var surfW = 0
    private var surfH = 0
    private var fixedW = 0
    private var fixedH = 0
    private var lastFrameNs = 0L
    private var lastRenderNs = 0L
    private var lastInteractionNs = 0L
    private var idleSinceNs = System.nanoTime()
    private var appliedRateHint = -1f
    private var lastMovingNs = 0L

    private var mode = GarageMode.GARAGE
    private var selected: String? = null
    private var statusOn = false
    private var health: Map<String, PartHealth> = emptyMap()
    private var pulse = 0.0
    private var pendingView: (() -> Unit)? = null

    // camera: position + target (glTF/world coordinates), turntable yaw
    private val camPos = doubleArrayOf(0.0, 0.0, 0.0)
    private val camTarget = doubleArrayOf(0.0, 0.0, 0.0)
    private var yaw = 0.0
    private var yawDirty = true

    private var tweenActive = false
    private var tweenStartNs = 0L
    private val fromPos = DoubleArray(3)
    private val fromTarget = DoubleArray(3)
    private val toPos = DoubleArray(3)
    private val toTarget = DoubleArray(3)
    private var fromYaw = 0.0
    private var toYaw = 0.0

    private var pendTheta = 0.0
    private var pendPhi = 0.0
    private var pendZoom = 0.0

    private var shift = 0.0
    private var shiftTarget = 0.0

    // intro
    private var introPending = false
    private var introRunning = false
    private var introStartNs = -1L
    private val introFired = BooleanArray(INTRO_EVENTS)
    private var introLightCb: ((Int) -> Unit)? = null
    private var introDoneCb: (() -> Unit)? = null

    // scratch (no per-frame allocations)
    private val rootMat = FloatArray(16)
    private val rotMat = FloatArray(16)
    private val tableMat = FloatArray(16)

    override var onPartTapped: ((String) -> Unit)? = null

    private val pickCallback = View.OnPickCallback { result ->
        if (released) return@OnPickCallback
        val slot = entitySlot[result.renderable] ?: return@OnPickCallback
        onPartTapped?.invoke(slot)
    }

    init {
        // Free everything when the view leaves the window (Compose removed it).
        surfaceView.addOnAttachStateChangeListener(object : android.view.View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(v: android.view.View) = Unit
            override fun onViewDetachedFromWindow(v: android.view.View) = release()
        })
        surfaceView.addOnLayoutChangeListener { _, l, t, r, b, _, _, _, _ -> onViewLayout(r - l, b - t) }
        uiHelper.renderCallback = SurfaceCallback()
        uiHelper.attachTo(surfaceView)

        view.scene = scene
        view.camera = camera
        camera.setExposure(T.APERTURE, T.SHUTTER, T.ISO)
        setupView()
        setupLights()
        // intensity = the IBL's: until the IBL is set, Filament lights the sky with its default 30000 and the dark
        // sky colour flashed light grey for ~0.2 s at start (seen in a screen recording 2026-10-11)
        skybox = Skybox.Builder().color(T.SKY[0], T.SKY[1], T.SKY[2], 1f).intensity(T.IBL_INTENSITY)
            .build(engine).also { scene.skybox = it }
        jumpToPreset()
        loadAsync()
    }

    // ================================================================= lifecycle

    fun resume() {
        if (running || released) return
        running = true
        lastFrameNs = 0L
        dirty = true
        choreographer.postFrameCallback(this)
    }

    fun pause() {
        running = false
        choreographer.removeFrameCallback(this)
    }

    /**
     * Release order matters: frames stop, the swap chain goes (UiHelper), then assets (which own their
     * renderables and material instances), then our duplicated material instances, the loaders and the
     * ubershader materials, our lights / IBL / skybox, and the engine last.
     */
    private fun release() {
        if (released) return
        released = true
        pause()
        uiHelper.detach()
        displayHelper.detach()
        swapChain?.let { engine.destroySwapChain(it); swapChain = null }
        engine.flushAndWait()

        resourceLoader.asyncCancelLoad()
        resourceLoader.evictResourceData()
        bikeAsset?.let { scene.removeEntities(it.entities); assetLoader.destroyAsset(it) }
        garageAsset?.let { scene.removeEntities(it.entities); assetLoader.destroyAsset(it) }
        bikeAsset = null
        garageAsset = null
        ownedInstances.forEach { engine.destroyMaterialInstance(it) }
        ownedInstances.clear()
        assetLoader.destroy()
        materialProvider.destroyMaterials()
        materialProvider.destroy()
        resourceLoader.destroy()

        scene.indirectLight = null
        scene.skybox = null
        indirectLight?.let { engine.destroyIndirectLight(it) }
        iblTexture?.let { engine.destroyTexture(it) }
        skybox?.let { engine.destroySkybox(it) }
        for (e in lightEntities) if (e != 0) {
            scene.removeEntity(e)
            engine.destroyEntity(e)
            EntityManager.get().destroy(e)
        }
        engine.destroyRenderer(renderer)
        engine.destroyView(view)
        engine.destroyScene(scene)
        engine.destroyCameraComponent(cameraEntity)
        EntityManager.get().destroy(cameraEntity)
        colorGrading?.let { engine.destroyColorGrading(it) }
        engine.destroy()
        onPartTapped = null
        introLightCb = null
        introDoneCb = null
    }

    private inner class SurfaceCallback : UiHelper.RendererCallback {
        override fun onNativeWindowChanged(surface: Surface) {
            if (released) return
            swapChain?.let { engine.destroySwapChain(it) }
            swapChain = engine.createSwapChain(surface, uiHelper.swapChainFlags)
            appliedRateHint = -1f
            surfaceView.display?.let { displayHelper.attach(renderer, it) }
            dirty = true
        }

        override fun onDetachedFromSurface() {
            displayHelper.detach()
            swapChain?.let {
                engine.destroySwapChain(it)
                engine.flushAndWait()  // the surface must not be used after this returns
                swapChain = null
            }
        }

        override fun onResized(width: Int, height: Int) {
            if (released || width <= 0 || height <= 0) return
            surfW = width
            surfH = height
            view.viewport = Viewport(0, 0, width, height)
            camera.setProjection(T.FOV_DEG, width.toDouble() / height, T.NEAR, T.FAR, Camera.Fov.VERTICAL)
            dirty = true
        }
    }

    private fun onViewLayout(w: Int, h: Int) {
        if (w <= 0 || h <= 0) return
        viewW = w
        viewH = h
        if (T.RENDER_SCALE < 0.999f) {
            val sw = (w * T.RENDER_SCALE).roundToInt()
            val sh = (h * T.RENDER_SCALE).roundToInt()
            if (sw != fixedW || sh != fixedH) {
                fixedW = sw
                fixedH = sh
                surfaceView.post { if (!released) surfaceView.holder.setFixedSize(sw, sh) }
            }
        }
    }

    // ================================================================= setup

    private fun setupView() {
        colorGrading = ColorGrading.Builder()
            .toneMapper(ToneMapper.ACESLegacy())
            .contrast(T.CONTRAST)
            .saturation(T.SATURATION)
            .build(engine)
        view.colorGrading = colorGrading
        view.antiAliasing = View.AntiAliasing.FXAA
        view.multiSampleAntiAliasingOptions = view.multiSampleAntiAliasingOptions.apply {
            enabled = T.MSAA_SAMPLES > 1; sampleCount = T.MSAA_SAMPLES
        }
        view.ambientOcclusionOptions = view.ambientOcclusionOptions.apply {
            enabled = true; radius = T.SSAO_RADIUS; intensity = T.SSAO_INTENSITY
        }
        view.bloomOptions = view.bloomOptions.apply {
            enabled = true
            strength = T.BLOOM_STRENGTH
            levels = T.BLOOM_LEVELS
            resolution = T.BLOOM_RESOLUTION
            threshold = true
            lensFlare = false
        }
        view.screenSpaceReflectionsOptions = view.screenSpaceReflectionsOptions.apply {
            enabled = true
            thickness = T.SSR_THICKNESS
            bias = T.SSR_BIAS
            maxDistance = T.SSR_MAX_DISTANCE
            stride = T.SSR_STRIDE
        }
        view.fogOptions = view.fogOptions.apply {
            enabled = true
            distance = T.FOG_START
            density = T.FOG_DENSITY
            height = 0f
            heightFalloff = T.FOG_HEIGHT_FALLOFF
            maximumOpacity = T.FOG_MAX_OPACITY
            color = floatArrayOf(T.SKY[0], T.SKY[1], T.SKY[2])
            fogColorFromIbl = false
        }
        view.vignetteOptions = view.vignetteOptions.apply {
            enabled = true; midPoint = T.VIGNETTE_MID; roundness = 0.6f; feather = 0.6f
        }
        view.dynamicResolutionOptions = view.dynamicResolutionOptions.apply {
            enabled = true; minScale = T.DYNAMIC_RES_MIN; maxScale = 1f; homogeneousScaling = true
            quality = View.QualityLevel.MEDIUM
        }
        // PCF, not VSM: on the Mali-G715 VSM (+ its blur) was one of the three biggest costs (phone test 2026-10-11)
        view.setShadowType(View.ShadowType.PCF)
    }

    private fun setupLights() {
        lightEntities[0] = spot(0xFFFFFF, 0.15f, 3.5f, 0.3f, 0.13f, 0.5f, 0f, 0.62f, T.KEY_CD, shadows = true)
        lightEntities[1] = spot(0xE8F0FF, 1.8f, 2.6f, 3.2f, 0.13f, 0.5f, 0f, 0.5f, T.FRONT_CD, shadows = false)
        // aimed above the turntable with a narrow cone: it outlines the bike without pooling lime light on the floor
        lightEntities[2] = spot(0xD2F500, -2.6f, 2.4f, -2.4f, 0.13f, 0.85f, 0f, 0.42f, T.RIM_CD, shadows = false)
        lightEntities[3] = spot(0x9FB8FF, 0.3f, 3.4f, -1.5f, 0.3f, 0.8f, -3.4f, 1.0f, T.WALL_CD, shadows = false)
    }

    private fun spot(
        hex: Int, px: Float, py: Float, pz: Float, tx: Float, ty: Float, tz: Float,
        outer: Float, candela: Float, shadows: Boolean,
    ): Int {
        val e = EntityManager.get().create()
        val c = T.linear(hex)
        var dx = tx - px
        var dy = ty - py
        var dz = tz - pz
        val len = sqrt(dx * dx + dy * dy + dz * dz)
        dx /= len; dy /= len; dz /= len
        val builder = LightManager.Builder(LightManager.Type.SPOT)
            .color(c[0], c[1], c[2])
            .intensityCandela(candela)
            .position(px, py, pz)
            .direction(dx, dy, dz)
            .spotLightCone(outer * 0.5f, outer)  // three.js penumbra 0.5
            .falloff(12f)
            .castShadows(shadows)
        if (shadows) {
            builder.shadowOptions(LightManager.ShadowOptions().apply {
                mapSize = T.SHADOW_MAP_SIZE
            })
        }
        builder.build(engine, e)
        scene.addEntity(e)
        return e
    }

    private fun setupIbl(hdr: ByteArray) {
        try {
            val equirect = HDRLoader.createTexture(engine, direct(hdr)) ?: return
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
            iblTexture = filtered
            indirectLight = IndirectLight.Builder().reflections(filtered).intensity(T.IBL_INTENSITY).build(engine)
            scene.indirectLight = indirectLight
        } catch (e: Exception) {
            Log.w(TAG, "IBL setup failed", e)
        }
    }

    // ================================================================= loading

    private fun loadAsync() {
        Thread({
            val bike = readAsset("bike.glb")
            val bikeInfo = bike?.let { GlbInfo.parse(it) }
            var garage = readAsset("garage.glb")
            if (garage == null) {
                Log.w(TAG, "assets/garage.glb missing: using the fallback floor")
                garage = FallbackGarage.build()
            }
            val garageInfo = GlbInfo.parse(garage)
            val hdr = readAsset("envs/garage.hdr")
            mainHandler.post {
                if (!released) onAssetsRead(bike, bikeInfo, garage, garageInfo, hdr)
            }
        }, "garage-load").start()
    }

    private fun readAsset(name: String): ByteArray? = try {
        assets.open(name).use { it.readBytes() }
    } catch (e: Exception) {
        null
    }

    private fun direct(bytes: ByteArray): ByteBuffer =
        ByteBuffer.allocateDirect(bytes.size).order(ByteOrder.nativeOrder()).apply { put(bytes); flip() }

    private fun onAssetsRead(bike: ByteArray?, bikeInfo: GlbInfo?, garage: ByteArray, garageInfo: GlbInfo?, hdr: ByteArray?) {
        hdr?.let { setupIbl(it) }
        garageAsset = loadGlb(garage, "garage.glb")?.also { setupGarage(it, garageInfo) }
        if (bike == null) Log.e(TAG, "assets/bike.glb missing")
        bikeAsset = bike?.let { loadGlb(it, "bike.glb") }?.also { setupBike(it, bikeInfo) }
        loaded = true
        repaintAll()
        if (introPending) {
            startIntro()
        } else {
            jumpToPreset()
            pendingView?.let { pendingView = null; it() }
        }
        dirty = true
    }

    private fun loadGlb(bytes: ByteArray, name: String): FilamentAsset? = try {
        val asset = assetLoader.createAsset(direct(bytes))
        if (asset == null) {
            Log.e(TAG, "could not parse $name")
            null
        } else {
            resourceLoader.loadResources(asset)
            asset.releaseSourceData()
            scene.addEntities(asset.entities)
            val lights = asset.lightEntities
            if (lights.isNotEmpty()) {
                // the engine owns the lighting; punctual lights inside the file are ignored
                scene.removeEntities(lights)
                Log.i(TAG, "$name: ignoring ${lights.size} glTF light(s)")
            }
            asset
        }
    } catch (e: Exception) {
        Log.e(TAG, "loading $name failed", e)
        null
    }

    /** Walks up the node tree until a node name matches (exact, or a prefix for garage groups). */
    private fun groupOf(asset: FilamentAsset, entity: Int, names: Set<String>, prefix: Boolean): String? {
        val tm = engine.transformManager
        var e = entity
        var guard = 0
        while (e != 0 && guard++ < 64) {
            val n = asset.getName(e)
            if (n != null) {
                if (n in names) return n
                if (prefix) for (g in names) if (n.startsWith(g)) return g
            }
            val ti = tm.getInstance(e)
            if (ti == 0) return null
            e = tm.getParent(ti)
        }
        return null
    }

    private fun setupGarage(asset: FilamentAsset, info: GlbInfo?) {
        val rm = engine.renderableManager
        val tm = engine.transformManager
        turntableEntity = asset.getFirstEntityByName("turntable")
        if (turntableEntity != 0) tm.getTransform(tm.getInstance(turntableEntity), turntableBase)
        for (e in asset.renderableEntities) {
            val group = groupOf(asset, e, GARAGE_GROUPS, prefix = true)
            val ri = rm.getInstance(e)
            val glowing = group != null && (group in NEON_GROUPS || group == HEX_GROUP)
            rm.setCastShadows(ri, group in SHADOW_CASTERS)
            rm.setReceiveShadows(ri, !glowing)
            if (!glowing) continue
            val glows = if (group == HEX_GROUP) hexGlows else neonGlows
            (if (group == HEX_GROUP) hexRenderables else neonRenderables).add(e)
            for (p in 0 until rm.getPrimitiveCount(ri)) {
                val mi = rm.getMaterialInstanceAt(ri, p)
                glows.add(makeGlow(mi, info?.emissive(asset.getName(e), p, mi.name)))
            }
        }
        if (turntableEntity == 0) Log.w(TAG, "garage.glb has no 'turntable' node")
    }

    private fun setupBike(asset: FilamentAsset, info: GlbInfo?) {
        val rm = engine.renderableManager
        val tm = engine.transformManager
        bikeRoot = asset.root
        val savedYaw = yaw
        yaw = 0.0
        applyYaw()  // part boxes are measured with the drive side facing +Z
        val owner = HashMap<Long, String>()
        val dupes = HashMap<String, HashMap<Long, MaterialInstance>>()
        val seen = HashMap<String, HashSet<Long>>()
        val box = Box()
        val world = FloatArray(16)
        for (e in asset.renderableEntities) {
            val slot = groupOf(asset, e, SLOTS, prefix = false) ?: continue
            entitySlot[e] = slot
            if (slot in ACCESSORY_SLOTS) accessoryRenderables.add(e)
            val ri = rm.getInstance(e)
            rm.setCastShadows(ri, true)
            rm.setReceiveShadows(ri, true)
            val glows = slotGlows.getOrPut(slot) { ArrayList() }
            val seenHere = seen.getOrPut(slot) { HashSet() }
            for (p in 0 until rm.getPrimitiveCount(ri)) {
                val mi = rm.getMaterialInstanceAt(ri, p)
                val key = mi.nativeObject
                val own = owner.getOrPut(key) { slot }
                // a material shared with another part gets its own copy, so each part can glow alone
                val use = if (own == slot) mi else dupes.getOrPut(slot) { HashMap() }.getOrPut(key) {
                    MaterialInstance.duplicate(mi, mi.name).also { ownedInstances.add(it) }
                }
                if (use !== mi) rm.setMaterialInstanceAt(ri, p, use)
                if (seenHere.add(use.nativeObject)) {
                    glows.add(makeGlow(use, info?.emissive(asset.getName(e), p, mi.name)))
                }
            }
            // world-space bounding box at yaw 0
            rm.getAxisAlignedBoundingBox(ri, box)
            tm.getWorldTransform(tm.getInstance(e), world)
            val c = box.center
            val h = box.halfExtent
            val b = slotBoxes.getOrPut(slot) {
                floatArrayOf(Float.MAX_VALUE, Float.MAX_VALUE, Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE)
            }
            for (i in 0 until 8) {
                val x = c[0] + if (i and 1 == 0) -h[0] else h[0]
                val y = c[1] + if (i and 2 == 0) -h[1] else h[1]
                val z = c[2] + if (i and 4 == 0) -h[2] else h[2]
                for (a in 0 until 3) {
                    val v = world[a] * x + world[4 + a] * y + world[8 + a] * z + world[12 + a]
                    if (v < b[a]) b[a] = v
                    if (v > b[3 + a]) b[3 + a] = v
                }
            }
        }
        val missing = SLOTS - slotGlows.keys
        if (missing.isNotEmpty()) Log.w(TAG, "bike.glb is missing slots: $missing")
        setVisible(accessoryRenderables, accessoriesOn)
        yaw = savedYaw
        yawDirty = true
    }

    private fun makeGlow(mi: MaterialInstance, base: FloatArray?): Glow {
        val material = mi.material
        val info = paramCache.getOrPut(material.nativeObject) {
            var type: Material.Parameter.Type? = null
            var strength = false
            for (p in material.parameters) {
                if (p.name == "emissiveFactor") type = p.type
                if (p.name == "emissiveStrength") strength = true
            }
            ParamInfo(type, strength)
        }
        // the strength is folded into the factor, so it is fixed at 1
        if (info.hasStrength) mi.setParameter("emissiveStrength", 1f)
        val glow = Glow(mi, base ?: ZERO3, info.factorType)
        setGlow(glow, glow.base[0], glow.base[1], glow.base[2])
        return glow
    }

    private fun setGlow(g: Glow, r: Float, gr: Float, b: Float) {
        when (g.factorType) {
            Material.Parameter.Type.FLOAT3 -> g.mi.setParameter("emissiveFactor", r, gr, b)
            Material.Parameter.Type.FLOAT4 -> g.mi.setParameter("emissiveFactor", r, gr, b, 1f)
            else -> Unit
        }
    }

    // ================================================================= GarageController

    override fun showMode(mode: GarageMode) {
        if (released) return
        this.mode = mode
        idleSinceNs = System.nanoTime()
        requestView { flyToPreset() }
    }

    override fun flyToArea(slots: List<String>) {
        if (released) return
        val list = slots.toList()
        requestView { boxView(list, T.AREA_K, T.AREA_MIN_D) }
    }

    override fun flyToPart(slot: String) {
        if (released) return
        requestView { boxView(listOf(slot), T.PART_K, T.PART_MIN_D) }
    }

    override fun setSelected(slot: String?) {
        if (released || slot == selected) return
        val old = selected
        selected = slot
        pulse = 0.0
        idleSinceNs = System.nanoTime()
        if (loaded) {
            old?.let { paintSlot(it) }
            slot?.let { paintSlot(it) }
        }
        dirty = true
    }

    override fun setAccessoriesVisible(visible: Boolean) {
        if (released) return
        accessoriesOn = visible
        setVisible(accessoryRenderables, visible)  // empty until the bike is loaded; applied again after loading
        dirty = true
    }

    override fun setStatusView(enabled: Boolean, health: Map<String, PartHealth>) {
        if (released) return
        statusOn = enabled
        this.health = HashMap(health)
        if (loaded) repaintAll()
        dirty = true
    }

    override fun setPanelInsets(leftFraction: Float, rightFraction: Float) {
        if (released) return
        val l = leftFraction.coerceIn(0f, 1f)
        val r = rightFraction.coerceIn(0f, 1f)
        // the centre of the free space, in viewport widths (Camera.setShift units)
        shiftTarget = (l - r) / 2.0
        dirty = true
    }

    override fun resetCamera() {
        if (released) return
        onUserInteraction()
        requestView { flyToPreset() }
    }

    override fun orbit(dxPx: Float, dyPx: Float) {
        if (released) return
        onUserInteraction()
        if (introRunning) return
        tweenActive = false
        val h = if (viewH > 0) viewH.toDouble() else 1000.0
        pendTheta -= 2 * Math.PI * dxPx / h * T.ROTATE_SPEED
        pendPhi -= 2 * Math.PI * dyPx / h * T.ROTATE_SPEED
    }

    override fun zoom(factor: Float) {
        if (released || factor <= 0f) return
        onUserInteraction()
        if (introRunning) return
        tweenActive = false
        pendZoom -= ln(factor.toDouble())
    }

    override fun tap(xPx: Float, yPx: Float) {
        if (released) return
        onUserInteraction()
        if (!loaded || introRunning || viewW <= 0 || viewH <= 0 || surfW <= 0 || surfH <= 0) return
        val sx = (xPx * surfW / viewW).toInt().coerceIn(0, surfW - 1)
        // Filament's pick origin is the bottom-left corner
        val sy = (surfH - 1 - (yPx * surfH / viewH).toInt()).coerceIn(0, surfH - 1)
        view.pick(sx, sy, mainHandler, pickCallback)
        dirty = true
    }

    override fun onUserInteraction() {
        val now = System.nanoTime()
        lastInteractionNs = now
        idleSinceNs = now
        dirty = true
    }

    override fun playIntro(onLightOn: (index: Int) -> Unit, onFinished: () -> Unit) {
        if (released) return
        introLightCb = onLightOn
        introDoneCb = onFinished
        introFired.fill(false)
        if (loaded) startIntro() else introPending = true
    }

    override fun skipIntro() {
        if (released) return
        when {
            introRunning -> endIntro()
            introPending -> {
                introPending = false
                finishIntroCallbacks()
            }
        }
    }

    // ================================================================= camera

    /** Runs a camera request now, or after loading / the intro. */
    private fun requestView(action: () -> Unit) {
        if (!loaded || introRunning || introPending) pendingView = action else action()
        dirty = true
    }

    private fun presetInto(pos: DoubleArray, target: DoubleArray, m: GarageMode) {
        val d = T.modeDist(m)
        pos[0] = T.PRESET_TARGET_X + sin(T.PRESET_ANGLE) * d
        pos[1] = T.PRESET_CAM_Y
        pos[2] = cos(T.PRESET_ANGLE) * d
        target[0] = T.PRESET_TARGET_X
        target[1] = T.PRESET_TARGET_Y
        target[2] = 0.0
    }

    private fun jumpToPreset() {
        presetInto(camPos, camTarget, mode)
        yaw = T.modeYaw(mode)
        yawDirty = true
        tweenActive = false
        pendTheta = 0.0; pendPhi = 0.0; pendZoom = 0.0
    }

    private fun flyToPreset() {
        presetInto(toPos, toTarget, mode)
        startTween(T.modeYaw(mode))
    }

    private fun boxView(slots: List<String>, k: Double, minD: Double) {
        var minX = Double.MAX_VALUE; var minY = Double.MAX_VALUE; var minZ = Double.MAX_VALUE
        var maxX = -Double.MAX_VALUE; var maxY = -Double.MAX_VALUE; var maxZ = -Double.MAX_VALUE
        var any = false
        for (s in slots) {
            val b = slotBoxes[s] ?: continue
            any = true
            minX = min(minX, b[0].toDouble()); minY = min(minY, b[1].toDouble()); minZ = min(minZ, b[2].toDouble())
            maxX = max(maxX, b[3].toDouble()); maxY = max(maxY, b[4].toDouble()); maxZ = max(maxZ, b[5].toDouble())
        }
        if (!any) return
        val cx = (minX + maxX) / 2
        val cy = (minY + maxY) / 2
        val cz = (minZ + maxZ) / 2
        val size = sqrt((maxX - minX).pow(2) + (maxY - minY).pow(2) + (maxZ - minZ).pow(2))
        val d = max(max(minD, size * k), T.MIN_DIST)
        val dl = sqrt(0.28 * 0.28 + 0.32 * 0.32 + 1.0)
        toTarget[0] = cx; toTarget[1] = cy; toTarget[2] = cz
        toPos[0] = cx + 0.28 / dl * d
        toPos[1] = cy + 0.32 / dl * d
        toPos[2] = cz + 1.0 / dl * d
        startTween(0.0)
    }

    private fun startTween(targetYaw: Double) {
        clampToRoom(toPos)
        for (i in 0 until 3) {
            fromPos[i] = camPos[i]
            fromTarget[i] = camTarget[i]
        }
        fromYaw = yaw
        var dy = targetYaw - yaw
        dy = atan2(sin(dy), cos(dy))
        toYaw = yaw + dy
        tweenStartNs = System.nanoTime()
        tweenActive = true
        pendTheta = 0.0; pendPhi = 0.0; pendZoom = 0.0
        idleSinceNs = tweenStartNs
        dirty = true
    }

    private fun stepTween(now: Long) {
        val k = ((now - tweenStartNs) / (T.FLY_MS * 1e6)).coerceIn(0.0, 1.0)
        val e = ease(k)
        for (i in 0 until 3) {
            camPos[i] = fromPos[i] + (toPos[i] - fromPos[i]) * e
            camTarget[i] = fromTarget[i] + (toTarget[i] - fromTarget[i]) * e
        }
        yaw = fromYaw + (toYaw - fromYaw) * e
        yawDirty = true
        if (k >= 1.0) {
            tweenActive = false
            yaw = Math.IEEEremainder(yaw, 2 * Math.PI)
        }
    }

    /** Damped orbit / zoom like three.js OrbitControls. Returns true while still moving. */
    private fun stepOrbit(dt: Double): Boolean {
        if (abs(pendTheta) < 1e-5 && abs(pendPhi) < 1e-5 && abs(pendZoom) < 1e-5) {
            pendTheta = 0.0; pendPhi = 0.0; pendZoom = 0.0
            return false
        }
        val f = 1 - (1 - T.DAMPING).pow(dt * 60)
        val dTheta = pendTheta * f
        val dPhi = pendPhi * f
        val dZoom = pendZoom * f
        pendTheta -= dTheta; pendPhi -= dPhi; pendZoom -= dZoom

        val ox = camPos[0] - camTarget[0]
        val oy = camPos[1] - camTarget[1]
        val oz = camPos[2] - camTarget[2]
        var r = sqrt(ox * ox + oy * oy + oz * oz).coerceAtLeast(1e-4)
        var theta = atan2(ox, oz)
        var phi = acos((oy / r).coerceIn(-1.0, 1.0))
        theta += dTheta
        phi += dPhi
        r = (r * exp(dZoom)).coerceIn(T.MIN_DIST, T.MAX_DIST)
        var maxPhi = T.MAX_POLAR
        // never under the floor
        val floorCos = (T.CAMERA_MIN_Y - camTarget[1]) / r
        if (floorCos > -1.0 && floorCos < 1.0) maxPhi = min(maxPhi, acos(floorCos))
        phi = phi.coerceIn(T.MIN_POLAR, max(T.MIN_POLAR, maxPhi))
        camPos[0] = camTarget[0] + r * sin(phi) * sin(theta)
        camPos[1] = camTarget[1] + r * cos(phi)
        camPos[2] = camTarget[2] + r * sin(phi) * cos(theta)
        clampToRoom(camPos)
        return true
    }

    private fun clampToRoom(p: DoubleArray) {
        p[0] = p[0].coerceIn(T.ROOM_MIN_X, T.ROOM_MAX_X)
        p[1] = p[1].coerceIn(T.CAMERA_MIN_Y, T.ROOM_MAX_Y)
        p[2] = p[2].coerceIn(T.ROOM_MIN_Z, T.ROOM_MAX_Z)
    }

    private fun stepShift(dt: Double): Boolean {
        val diff = shiftTarget - shift
        if (abs(diff) < 1e-4) {
            if (shift != shiftTarget) {
                shift = shiftTarget
                camera.setShift(shift, 0.0)
            }
            return false
        }
        shift += diff * min(1.0, dt * T.SHIFT_RATE)
        camera.setShift(shift, 0.0)
        return true
    }

    /** Bike and turntable rotate together around the turntable centre. */
    private fun applyYaw() {
        yawDirty = false
        val tm = engine.transformManager
        val c = cos(yaw).toFloat()
        val s = sin(yaw).toFloat()
        rotMat.fill(0f)
        rotMat[0] = c; rotMat[2] = -s; rotMat[5] = 1f; rotMat[8] = s; rotMat[10] = c; rotMat[15] = 1f
        if (bikeRoot != 0) {
            val cx = T.TURNTABLE_X.toFloat()
            System.arraycopy(rotMat, 0, rootMat, 0, 16)
            rootMat[12] = cx - c * cx
            rootMat[13] = T.BIKE_Y
            rootMat[14] = s * cx
            tm.setTransform(tm.getInstance(bikeRoot), rootMat)
        }
        if (turntableEntity != 0) {
            // tableMat = turntableBase * rotation (rotate about the node's own origin = turntable centre)
            for (col in 0 until 4) for (row in 0 until 4) {
                var v = 0f
                for (k in 0 until 4) v += turntableBase[k * 4 + row] * rotMat[col * 4 + k]
                tableMat[col * 4 + row] = v
            }
            tm.setTransform(tm.getInstance(turntableEntity), tableMat)
        }
    }

    // ================================================================= glow

    private fun repaintAll() {
        for (slot in slotGlows.keys) paintSlot(slot)
    }

    private fun paintSlot(slot: String) {
        val glows = slotGlows[slot] ?: return
        var col: FloatArray? = null
        var k = 0f
        if (slot == selected) {
            col = SEL
            k = (T.SELECT_GLOW_BASE + T.SELECT_GLOW_PULSE * sin(pulse).toFloat()) * T.GLOW_GAIN
        } else if (statusOn) {
            when (health[slot]) {
                PartHealth.OK -> { col = OK; k = T.STATUS_GLOW_OK * T.GLOW_GAIN }
                PartHealth.SOON -> { col = SOON; k = T.STATUS_GLOW_WARN * T.GLOW_GAIN }
                PartHealth.OVER -> { col = OVER; k = T.STATUS_GLOW_WARN * T.GLOW_GAIN }
                else -> Unit
            }
        }
        for (i in glows.indices) {
            val g = glows[i]
            if (col == null) setGlow(g, g.base[0], g.base[1], g.base[2])
            else setGlow(g, col[0] * k, col[1] * k, col[2] * k)
        }
    }

    private fun setNeon(level: Float) {
        if (level == neonLevel) return
        val wasOn = neonLevel > 0f
        neonLevel = level
        for (i in neonGlows.indices) {
            val g = neonGlows[i]
            setGlow(g, g.base[0] * level, g.base[1] * level, g.base[2] * level)
        }
        if (wasOn != (level > 0f)) setVisible(neonRenderables, level > 0f)
    }

    private fun setHexVisible(on: Boolean) {
        if (on == hexVisible) return
        hexVisible = on
        setVisible(hexRenderables, on)
    }

    private fun setVisible(entities: ArrayList<Int>, on: Boolean) {
        val rm = engine.renderableManager
        for (i in entities.indices) {
            val ri = rm.getInstance(entities[i])
            if (ri != 0) rm.setLayerMask(ri, 0xFF, if (on) 0x01 else 0x00)
        }
    }

    private fun setLightLevel(i: Int, level: Float) {
        if (lightLevel[i] == level) return
        lightLevel[i] = level
        val lm = engine.lightManager
        val li = lm.getInstance(lightEntities[i])
        if (li != 0) lm.setIntensityCandela(li, lightFull[i] * level)
    }

    // ================================================================= intro

    private fun startIntro() {
        introPending = false
        introRunning = true
        introStartNs = -1L
        tweenActive = false
        pendTheta = 0.0; pendPhi = 0.0; pendZoom = 0.0
        yaw = T.modeYaw(mode)
        yawDirty = true
        for (i in 0 until 4) setLightLevel(i, 0f)
        indirectLight?.intensity = 0f
        setHexVisible(false)
        setNeon(0f)
        introFrame(0.0)
        dirty = true
    }

    private fun fireIntro(i: Int) {
        if (introFired[i]) return
        introFired[i] = true
        introLightCb?.invoke(i)
    }

    private fun introFrame(t: Double) {
        // ceiling hex lights flicker on first, then the spots one by one, then the neon
        val hexOn = t > T.INTRO_HEX_ON && !(t > 0.62 && t < 0.72) && !(t > 0.85 && t < 0.9)
        setHexVisible(hexOn)
        if (t > T.INTRO_HEX_ON) fireIntro(0)
        indirectLight?.intensity = T.IBL_INTENSITY * ramp((t - T.INTRO_LIGHTS_START) / T.INTRO_LIGHT_RAMP)
        for (i in 0 until 4) {
            val k = ramp((t - T.INTRO_LIGHTS_START - (i + 1) * T.INTRO_LIGHT_STEP) / T.INTRO_LIGHT_RAMP)
            setLightLevel(i, k)
            if (k > 0f) fireIntro(i + 1)
        }
        val neon = ramp((t - T.INTRO_NEON_ON) / T.INTRO_NEON_RAMP)
        setNeon(neon)
        if (neon > 0f) fireIntro(5)

        // camera sweep from behind-left to the GARAGE preset
        val e = ease(min(1.0, t / T.INTRO_SWEEP))
        val ang = T.INTRO_START_ANGLE + e * (T.PRESET_ANGLE - T.INTRO_START_ANGLE)
        val endDist = T.modeDist(GarageMode.GARAGE)
        val d = T.INTRO_START_DIST + e * (endDist - T.INTRO_START_DIST)
        camPos[0] = T.PRESET_TARGET_X + sin(ang) * d
        camPos[1] = T.INTRO_START_Y + e * (T.PRESET_CAM_Y - T.INTRO_START_Y)
        camPos[2] = cos(ang) * d
        camTarget[0] = T.PRESET_TARGET_X
        camTarget[1] = T.PRESET_TARGET_Y
        camTarget[2] = 0.0
        if (t > T.INTRO_END) endIntro()
    }

    private fun endIntro() {
        if (!introRunning) return
        introRunning = false
        setHexVisible(true)
        for (i in 0 until 4) setLightLevel(i, 1f)
        indirectLight?.intensity = T.IBL_INTENSITY
        setNeon(1f)
        val pv = pendingView
        pendingView = null
        if (pv != null) pv() else flyToPreset()
        dirty = true
        finishIntroCallbacks()
    }

    private fun finishIntroCallbacks() {
        val done = introDoneCb
        introDoneCb = null
        introLightCb = null
        done?.invoke()
    }

    // ================================================================= frame loop

    override fun doFrame(frameTimeNanos: Long) {
        if (!running || released) return
        choreographer.postFrameCallback(this)
        val dt = if (lastFrameNs == 0L) 0.0 else ((frameTimeNanos - lastFrameNs) / 1e9).coerceIn(0.0, 0.05)
        lastFrameNs = frameTimeNanos

        val rate = if (loaded) update(frameTimeNanos, dt) else RATE_STATIC
        updateRateHint(rate)
        // When nothing moves, keep drawing for a short settle time (dynamic resolution climbs back to full
        // sharpness, reflections catch up), then stop: the last image stays on screen at zero GPU cost.
        if (rate != RATE_STATIC) lastMovingNs = frameTimeNanos
        val settling = frameTimeNanos - lastMovingNs < T.SETTLE_NS
        if (!dirty && rate == RATE_STATIC && !settling) return
        val interval = when (rate) {
            RATE_ACTIVE -> 0L
            else -> T.IDLE_FRAME_NS
        }
        if (!dirty && frameTimeNanos - lastRenderNs < interval) return
        val sc = swapChain ?: return
        if (!uiHelper.isReadyToRender) return
        if (renderer.beginFrame(sc, frameTimeNanos)) {
            // slow idle animation: show each frame at a fixed time after its vsync, so the 30 fps frames are evenly
            // spaced (without it some were shown one refresh late: 25 / 42 ms judder)
            if (rate == RATE_IDLE) renderer.setPresentationTime(frameTimeNanos + T.IDLE_PRESENT_DELAY_NS)
            renderer.render(view)
            renderer.endFrame()
            lastRenderNs = frameTimeNanos
            dirty = false
        }
    }

    private fun update(now: Long, dt: Double): Int {
        var rate = RATE_STATIC
        when {
            introRunning -> {
                if (introStartNs < 0) introStartNs = now
                introFrame((now - introStartNs) / 1e9)
                rate = RATE_ACTIVE
            }
            tweenActive -> {
                stepTween(now)
                rate = RATE_ACTIVE
            }
            mode == GarageMode.GARAGE && selected == null && now - idleSinceNs > T.IDLE_SPIN_DELAY_NS -> {
                yaw = Math.IEEEremainder(yaw + dt * T.IDLE_SPIN_SPEED, 2 * Math.PI)  // turntable spins when idle
                yawDirty = true
                rate = RATE_IDLE
            }
        }
        if (!introRunning && stepOrbit(dt)) rate = RATE_ACTIVE
        if (stepShift(dt)) rate = RATE_ACTIVE
        val sel = selected
        if (sel != null) {
            pulse += dt * T.SELECT_PULSE_SPEED
            paintSlot(sel)
            if (rate < RATE_IDLE) rate = RATE_IDLE
        }
        if (yawDirty) applyYaw()
        camera.lookAt(camPos[0], camPos[1], camPos[2], camTarget[0], camTarget[1], camTarget[2], 0.0, 1.0, 0.0)
        if (now - lastInteractionNs < T.ACTIVE_HOLD_NS) rate = RATE_ACTIVE
        return rate
    }

    /** Frame-rate vote for the 3D surface (120 Hz LTPO panel on the Pixel). */
    private fun updateRateHint(rate: Int) {
        // 120 Hz while the bike moves under the finger (0 = "no preference" left the panel at 60), 30 Hz for the
        // slow idle animations, no vote when nothing is drawn (the LTPO panel can drop further)
        val hint = when (rate) {
            RATE_ACTIVE -> 120f
            RATE_IDLE -> T.IDLE_HZ
            else -> 0f
        }
        if (hint == appliedRateHint) return
        val sc = swapChain ?: return
        appliedRateHint = hint
        try {
            if (sc.isFrameRateChangeSupported) {
                sc.setFrameRate(hint, SwapChain.FrameRateCompatibility.DEFAULT, SwapChain.ChangeFrameRateStrategy.ONLY_IF_SEAMLESS)
            }
        } catch (e: Throwable) {
            Log.w(TAG, "frame rate hint failed", e)
        }
    }
}
