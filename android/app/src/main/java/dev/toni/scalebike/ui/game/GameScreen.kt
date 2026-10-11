package dev.toni.scalebike.ui.game

import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.systemGestureExclusion
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.max
import androidx.compose.ui.unit.min
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Category
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.EventType
import dev.toni.scalebike.data.Issue
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.Ride
import dev.toni.scalebike.data.ServiceEvent
import dev.toni.scalebike.data.addRide
import dev.toni.scalebike.data.deleteEvent
import dev.toni.scalebike.data.deleteIssue
import dev.toni.scalebike.data.deleteRide
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.newId
import dev.toni.scalebike.data.odometerKm
import dev.toni.scalebike.data.replacePart
import dev.toni.scalebike.data.updatePart
import dev.toni.scalebike.data.upsertEvent
import dev.toni.scalebike.data.upsertIssue
import dev.toni.scalebike.garage.GarageController
import dev.toni.scalebike.garage.GarageMode
import dev.toni.scalebike.garage.PartHealth
import dev.toni.scalebike.ui.AddRideDialog
import dev.toni.scalebike.ui.BikeInfoDialog
import dev.toni.scalebike.ui.ConfirmDialog
import dev.toni.scalebike.ui.EditPartDialog
import dev.toni.scalebike.ui.FitNotesDialog
import dev.toni.scalebike.ui.EventDialog
import dev.toni.scalebike.ui.IssueDialog
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.OdometerDialog
import dev.toni.scalebike.ui.ReplacePartDialog
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.max

/**
 * UI state of the game garage and every action that changes it (port of the prototype's JS state machine).
 * The 3D view is only reached through [controller]; it may be null until the garage is ready (calls are skipped).
 */
@Stable
class GameUi(val fx: GameFx) {
    var controller: GarageController? = null
    var data: BikeData = BikeData()

    var mode by mutableStateOf(GarageMode.GARAGE)
        private set
    var area by mutableStateOf<Category?>(null)
        private set
    var selected by mutableStateOf<String?>(null)
        private set
    var statusOn by mutableStateOf(false)
        private set
    var introDone by mutableStateOf(false)
        private set
    var introStarted = false
    val introShownAt = SystemClock.uptimeMillis()

    /** -1 left edge held, 1 right edge held, 0 none (edge glow flash). */
    var edgeHeld by mutableIntStateOf(0)
    var wipeKey by mutableIntStateOf(0)
        private set
    var wipeDir = 1
        private set
    var banner by mutableStateOf<BannerMsg?>(null)
        private set

    /** Pre-ride check ticks survive switching modes. */
    val checked = mutableStateListOf<Int>()

    /** Part shown in the PARTS details panel (left), or null for the parts list. May be a retired part. */
    var detailsId by mutableStateOf<String?>(null)
        private set

    private val modes = GarageMode.entries

    fun touch() {
        controller?.onUserInteraction()
    }

    fun showBanner(text: String, sub: String) {
        banner = BannerMsg(text, sub)
    }

    private fun wipe(dir: Int) {
        if (fx.reducedMotion || dir == 0) return
        wipeDir = dir
        wipeKey++
    }

    /** Prototype `setMode(i, quiet)`; [rawIndex] may be -1 or 5 (wraps around). */
    fun setMode(rawIndex: Int, quiet: Boolean = false) {
        val target = modes[((rawIndex % modes.size) + modes.size) % modes.size]
        val dir = rawIndex - mode.ordinal
        val changed = target != mode
        mode = target
        if (target != GarageMode.PARTS || changed) {
            selected = null
            area = null
            detailsId = null
        }
        controller?.showMode(target)
        if (changed && !quiet) {
            fx.whoosh()
            wipe(dir)
        }
        touch()
    }

    fun step(delta: Int) = setMode(mode.ordinal + delta)

    fun select(m: GarageMode) = setMode(m.ordinal)

    fun openArea(a: Category) {
        area = a
        selected = null
        fx.tick()
        controller?.flyToArea(data.partsIn(a).map { it.slot })
        touch()
    }

    /** Tap on the bike, a parts-list row, ALERTS or a log entry: PARTS mode, its area, card, camera fly-to. */
    fun selectPart(slot: String) {
        val part = data.parts.firstOrNull { it.slot == slot && !it.retired } ?: return
        if (!introDone) return
        if (mode != GarageMode.PARTS) {
            val d = GarageMode.PARTS.ordinal - mode.ordinal
            mode = GarageMode.PARTS
            fx.whoosh()
            wipe(d)
        }
        area = part.category
        selected = slot
        if (detailsId != null) detailsId = part.id   // details open: follow the newly picked part
        fx.tick()
        controller?.flyToPart(slot)
        touch()
    }

    /** DETAILS on the card, or another part of the same slot inside the details panel. */
    fun openDetails(partId: String) {
        detailsId = partId
        fx.tick()
        touch()
    }

    /** Back: close details → close card → leave area → GARAGE. Returns false when there is nothing to go back to. */
    fun back(): Boolean {
        if (!introDone) {
            skipIntro()
            return true
        }
        if (detailsId != null) {
            detailsId = null
            fx.tick()
            return true
        }
        if (selected != null) {
            selected = null
            area?.let { a -> controller?.flyToArea(data.partsIn(a).map { it.slot }) }
            fx.tick()
            return true
        }
        if (area != null) {
            area = null
            controller?.showMode(mode)
            fx.tick()
            return true
        }
        if (mode != GarageMode.GARAGE) {
            setMode(GarageMode.GARAGE.ordinal)
            return true
        }
        return false
    }

    fun doubleTap() {
        selected = null
        area = null
        detailsId = null
        controller?.resetCamera()
    }

    fun toggleStatus() {
        statusOn = !statusOn
        fx.tick()
        if (statusOn) showBanner("Status view", "Parts glow by condition") else showBanner("Status view off", "Garage")
    }

    fun skipIntro() {
        if (introDone) return
        controller?.skipIntro()
        finishIntro()
    }

    fun finishIntro() {
        if (introDone) return
        introDone = true
        setMode(GarageMode.GARAGE.ordinal, quiet = true)
    }

    /** A (new) controller arrived after the intro: bring the 3D view to the UI's current state. */
    fun syncCamera(c: GarageController) {
        c.showMode(mode)
        val sel = selected
        val a = area
        when {
            sel != null -> c.flyToPart(sel)
            a != null -> c.flyToArea(data.partsIn(a).map { it.slot })
        }
    }
}

private val mainHandler = Handler(Looper.getMainLooper())

private fun onMain(block: () -> Unit) {
    if (Looper.myLooper() == Looper.getMainLooper()) block() else mainHandler.post(block)
}

private data class EventEdit(val part: Part, val initial: ServiceEvent?)

/**
 * The NFS-style game UI, drawn on top of the 3D garage (stack it over the 3D view in a Box).
 * Handles all touches: edge swipe = change mode, drag = orbit, pinch = zoom, tap = pick a part, double tap = reset.
 */
@Composable
fun GameScreen(data: BikeData, controller: GarageController?, modifier: Modifier = Modifier) {
    val repo = LocalRepo.current
    val fx = rememberGameFx()
    val ui = remember(fx) { GameUi(fx) }
    ui.controller = controller
    ui.data = data
    val scope = rememberCoroutineScope()
    val reduced = fx.reducedMotion

    val summary = remember(data) { data.gameSummary() }
    val log = remember(data) { data.logEntries() }
    val odo = data.odometerKm()

    // ---------------------------------------------------------------- dialogs + launchers
    var rideDialog by remember { mutableStateOf(false) }
    var bikeDialog by remember { mutableStateOf(false) }
    var odoDialog by remember { mutableStateOf(false) }
    var deleteRide by remember { mutableStateOf<Ride?>(null) }
    var issueFor by remember { mutableStateOf<Part?>(null) }
    var replaceFor by remember { mutableStateOf<Part?>(null) }
    var eventEdit by remember { mutableStateOf<EventEdit?>(null) }
    var issueEdit by remember { mutableStateOf<Issue?>(null) }
    var partEdit by remember { mutableStateOf<Part?>(null) }
    var fitDialog by remember { mutableStateOf(false) }
    var resetConfirm by remember { mutableStateOf(false) }
    var pendingImport by remember { mutableStateOf<android.net.Uri?>(null) }

    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) {
            runCatching { repo.exportTo(uri) }
                .onSuccess { ui.showBanner("Backup saved", "bike.json") }
                .onFailure { ui.showBanner("Backup failed", it.message ?: "error") }
        }
    }
    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> pendingImport = uri }

    // ---------------------------------------------------------------- 3D garage wiring
    DisposableEffect(controller) {
        controller?.onPartTapped = { slot -> onMain { ui.selectPart(slot) } }
        onDispose { controller?.onPartTapped = null }
    }
    LaunchedEffect(controller) {
        val c = controller ?: return@LaunchedEffect
        if (!ui.introStarted && !ui.introDone) {
            ui.introStarted = true
            if (reduced) {
                c.skipIntro()
                ui.finishIntro()
            } else {
                c.playIntro(
                    onLightOn = { i -> onMain { fx.lightOn(i) } },
                    onFinished = { onMain { ui.finishIntro() } },
                )
                delay(7000)          // safety net if onFinished never comes
                ui.finishIntro()
            }
        } else {
            c.skipIntro()
            ui.finishIntro()
            ui.syncCamera(c)
        }
    }
    LaunchedEffect(Unit) {
        delay(8000)                  // no 3D view yet: open the UI anyway
        if (ui.controller == null) ui.finishIntro()
    }
    LaunchedEffect(controller, ui.statusOn, summary.healthBySlot) {
        controller?.setStatusView(ui.statusOn, summary.healthBySlot)
    }
    LaunchedEffect(controller, ui.selected) {
        controller?.setSelected(ui.selected)
    }

    BackHandler(enabled = !ui.introDone || ui.detailsId != null || ui.selected != null || ui.area != null || ui.mode != GarageMode.GARAGE) {
        ui.back()
    }

    // ---------------------------------------------------------------- layout
    val density = LocalDensity.current
    val safe = WindowInsets.safeDrawing
    val insetL = with(density) { safe.getLeft(this, LayoutDirection.Ltr).toDp() }
    val insetR = with(density) { safe.getRight(this, LayoutDirection.Ltr).toDp() }
    val insetT = with(density) { safe.getTop(this).toDp() }
    val insetB = with(density) { safe.getBottom(this).toDp() }

    BoxWithConstraints(
        modifier
            .fillMaxSize()
            .pointerInput(ui) { detectEdgeSwipes(ui) },
    ) {
        val leftW = min(maxWidth * 0.38f, 360.dp)
        val cardW = min(maxWidth * 0.32f, 310.dp)
        val leftOpen = ui.introDone && ui.mode != GarageMode.GARAGE
        val cardSlot = ui.selected?.takeIf { ui.introDone && ui.mode == GarageMode.PARTS && it in summary.partBySlot }
        val leftFrac = if (leftOpen) ((leftW + insetL) / maxWidth).coerceIn(0f, 1f) else 0f
        val rightFrac = if (cardSlot != null) ((cardW + insetR) / maxWidth).coerceIn(0f, 1f) else 0f
        LaunchedEffect(controller, leftFrac, rightFrac) { controller?.setPanelInsets(leftFrac, rightFrac) }

        // 1. touch layer for the 3D garage (below everything else, so buttons and panels keep their touches)
        Box(Modifier.fillMaxSize().pointerInput(ui) { detectGarageGestures(ui) })
        // keep Android's back gesture off the middle of both edges, where the mode swipe lives
        // (Android honours at most 200 dp of exclusion per edge, the phone is ~412 dp tall in landscape)
        val edgeDp = max(40.dp, maxWidth * 0.09f)
        Box(Modifier.align(Alignment.CenterStart).width(edgeDp + insetL).fillMaxHeight(EDGE_ZONE).systemGestureExclusion())
        Box(Modifier.align(Alignment.CenterEnd).width(edgeDp + insetR).fillMaxHeight(EDGE_ZONE).systemGestureExclusion())

        // 2. HUD
        val hudK by animateFloatAsState(if (ui.introDone) 1f else 0f, tween(if (reduced) 0 else 500), label = "hud")
        val hud = Modifier.graphicsLayer { alpha = hudK; translationY = (1f - hudK) * -8.dp.toPx() }
        if (hudK > 0f) {
            Nameplate(
                sub = "Dark grey · size ${data.bike.size} · MY${data.bike.year}",
                odoKm = odo,
                showOdo = !leftOpen,
                modifier = hud.align(Alignment.TopStart).padding(start = 16.dp + insetL, top = 10.dp + insetT),
            )
            TopRightHud(
                alerts = summary.alerts,
                statusOn = ui.statusOn,
                soundOn = fx.soundOn,
                classLetter = summary.classLetter,
                score = summary.score,
                onAlerts = {
                    val worst = summary.worstSlot
                    if (worst != null) ui.selectPart(worst) else {
                        fx.tick()
                        ui.showBanner("All good", "No part needs service")
                    }
                },
                onStatus = ui::toggleStatus,
                onSound = fx::toggleSound,
                modifier = hud.align(Alignment.TopEnd).padding(end = 16.dp + insetR, top = 10.dp + insetT),
            )
            EdgeGlow(true, ui.edgeHeld < 0, hud.align(Alignment.CenterStart).fillMaxHeight(EDGE_ZONE))
            EdgeGlow(false, ui.edgeHeld > 0, hud.align(Alignment.CenterEnd).fillMaxHeight(EDGE_ZONE))
        }

        // 3. left NFS menus, one per mode
        val panelPad = Modifier.padding(top = 74.dp + insetT, bottom = 72.dp + insetB)
        val slide = with(density) { 40.dp.roundToPx() }
        val enterL = if (reduced) EnterTransition.None else fadeIn(tween(350)) + slideInHorizontally(tween(450, easing = easeOutQuint)) { -slide }
        val exitL = if (reduced) ExitTransition.None else fadeOut(tween(300)) + slideOutHorizontally(tween(450, easing = easeOutQuint)) { -slide }
        val enterR = if (reduced) EnterTransition.None else fadeIn(tween(350)) + slideInHorizontally(tween(450, easing = easeOutQuint)) { slide }
        val exitR = if (reduced) ExitTransition.None else fadeOut(tween(300)) + slideOutHorizontally(tween(450, easing = easeOutQuint)) { slide }

        AnimatedVisibility(leftOpen && ui.mode == GarageMode.SERVICE_LOG, panelPad.align(Alignment.TopStart), enterL, exitL) {
            LogPanel(
                log, leftW, insetL,
                onEntry = { e ->
                    val p = data.parts.firstOrNull { it.id == e.partId }
                    if (p != null && !p.retired) ui.selectPart(p.slot) else fx.tick()
                },
                onLogRide = { fx.tick(); rideDialog = true },
            )
        }
        val detailsPart = ui.detailsId?.let { id -> data.parts.firstOrNull { it.id == id } }
            ?.takeIf { ui.mode == GarageMode.PARTS }
        AnimatedVisibility(leftOpen && ui.mode == GarageMode.PARTS && detailsPart == null, panelPad.align(Alignment.TopStart), enterL, exitL) {
            PartsPanel(
                data, summary, ui.area, ui.selected, leftW, insetL,
                onArea = ui::openArea, onPart = ui::selectPart, onBack = { ui.back() },
            )
        }
        var lastDetails by remember { mutableStateOf<Part?>(null) }
        if (detailsPart != null) lastDetails = detailsPart
        AnimatedVisibility(leftOpen && detailsPart != null, panelPad.align(Alignment.TopStart), enterL, exitL) {
            lastDetails?.let { p ->
                DetailsPanel(
                    data, p, leftW, insetL,
                    onBack = { ui.back() },
                    onEdit = { fx.tick(); partEdit = p },
                    onEvent = { e -> fx.tick(); eventEdit = EventEdit(p, e) },
                    onIssue = { i -> fx.tick(); issueEdit = i },
                    onOtherPart = { o -> ui.openDetails(o.id) },
                )
            }
        }
        AnimatedVisibility(leftOpen && ui.mode == GarageMode.WORKSHOP, panelPad.align(Alignment.TopStart), enterL, exitL) {
            WorkshopPanel(
                data, ui.checked, leftW, insetL,
                onToggle = { i ->
                    if (i in ui.checked) ui.checked.remove(i) else ui.checked.add(i)
                    if (ui.checked.size == PRE_RIDE_CHECK.size) {
                        fx.confirm()
                        ui.showBanner("Ready to ride", "Pre-ride check complete")
                        repo.update { it.copy(lastChecklistDate = Dates.today()) }
                        scope.launch { delay(1500); ui.checked.clear() }
                    } else {
                        fx.tick()
                    }
                },
                onWeight = { w -> repo.update { it.copy(riderWeightKg = w.toDouble()) } },
                onTubeless = { v -> fx.tick(); repo.update { it.copy(tubeless = v) } },
                onFitNotes = { fx.tick(); fitDialog = true },
            )
        }
        AnimatedVisibility(leftOpen && ui.mode == GarageMode.BIKE, panelPad.align(Alignment.TopStart), enterL, exitL) {
            BikePanel(
                data, fx, leftW, insetL,
                onLogRide = { fx.tick(); rideDialog = true },
                onEditBike = { fx.tick(); bikeDialog = true },
                onCorrectOdo = { fx.tick(); odoDialog = true },
                onDeleteRide = { r -> fx.tick(); deleteRide = r },
                onExport = { exporter.launch("scale980-backup-${Dates.today()}.json") },
                onImport = { importer.launch(arrayOf("application/json", "text/plain", "application/octet-stream")) },
                onReset = { resetConfirm = true },
            )
        }

        // 4. part card (right)
        var lastCardSlot by remember { mutableStateOf<String?>(null) }
        if (cardSlot != null) lastCardSlot = cardSlot
        AnimatedVisibility(cardSlot != null, panelPad.align(Alignment.TopEnd), enterR, exitR) {
            val slot = lastCardSlot
            val part = slot?.let { summary.partBySlot[it] }
            val st = slot?.let { summary.statusBySlot[it] }
            if (part != null && st != null) {
                PartCard(
                    data, part, st, summary.healthBySlot[slot] ?: PartHealth.NONE, fx, cardW, insetR,
                    onLogService = {
                        val e = ServiceEvent(newId(), part.id, Dates.today(), odo, EventType.SERVICE, "Service")
                        repo.upsertEvent(e)
                        ui.showBanner("Service logged", "${part.name} · ${groupedKm(odo)} km")
                    },
                    onDetails = { ui.openDetails(part.id) },
                    onIssue = { fx.tick(); issueFor = part },
                    onReplace = { replaceFor = part },
                )
            }
        }

        // 5. mode tabs + control prompts
        if (hudK > 0f) {
            ControlPrompts(insetB, hud.align(Alignment.BottomCenter))
            ModeBar(
                current = ui.mode,
                onSelect = { m -> if (m != ui.mode) ui.select(m) else fx.tick() },
                onPrev = { ui.step(-1) },
                onNext = { ui.step(1) },
                modifier = hud.align(Alignment.BottomCenter).padding(bottom = 22.dp + insetB),
            )
        }

        // 6. speed-stripe wipe, banner, intro
        SpeedWipe(ui.wipeKey, ui.wipeDir, !reduced)
        Banner(ui.banner, insetL, reduced)
        IntroTitle(visible = !ui.introDone, loading = controller == null)
        if (!ui.introDone) {
            Box(
                Modifier.fillMaxSize().pointerInput(ui) {
                    awaitEachGesture {
                        awaitFirstDown().consume()
                        if (SystemClock.uptimeMillis() - ui.introShownAt > 300) ui.skipIntro()
                    }
                },
            )
        }
    }

    // ---------------------------------------------------------------- dialogs (existing Material dialogs, restyled later)
    if (rideDialog) {
        AddRideDialog(onDismiss = { rideDialog = false }, onSave = { r ->
            repo.addRide(r)
            fx.confirm()
            ui.showBanner("Ride logged", "+${r.km.km()}")
        })
    }
    if (bikeDialog) BikeInfoDialog(data.bike, onDismiss = { bikeDialog = false }, onSave = { b -> repo.update { it.copy(bike = b) } })
    if (odoDialog) {
        OdometerDialog(odo, onDismiss = { odoDialog = false }) { total ->
            repo.update { d -> d.copy(bike = d.bike.copy(startOdometerKm = total - d.rides.sumOf { it.km })) }
            ui.showBanner("Odometer set", "${groupedKm(total)} km")
        }
    }
    deleteRide?.let { r ->
        ConfirmDialog(
            "Delete ride?", "${r.km.km()} on ${Dates.format(r.date)}",
            onConfirm = { repo.deleteRide(r.id); ui.showBanner("Ride deleted", "-${r.km.km()}") },
            onDismiss = { deleteRide = null },
        )
    }
    issueFor?.let { p ->
        IssueDialog(p.id, null, odo, onDismiss = { issueFor = null }, onSave = { i ->
            repo.upsertIssue(i)
            ui.showBanner("Issue reported", p.name)
        })
    }
    issueEdit?.let { issue ->
        IssueDialog(
            issue.partId, issue, odo,
            onDismiss = { issueEdit = null },
            onSave = { i -> repo.upsertIssue(i); ui.showBanner(if (i.resolved) "Issue resolved" else "Issue saved", i.title) },
            onDelete = { repo.deleteIssue(issue); issueEdit = null },
        )
    }
    if (fitDialog) {
        FitNotesDialog(data.fitNotes, onDismiss = { fitDialog = false }, onSave = { t ->
            repo.update { it.copy(fitNotes = t) }
            ui.showBanner("Fit notes saved", "Workshop")
        })
    }
    if (resetConfirm) {
        ConfirmDialog(
            "Reset all data?", "Parts, history, issues and rides are deleted and the setup starts again. Export a backup first.",
            confirmLabel = "Reset",
            onConfirm = { repo.resetAll() },
            onDismiss = { resetConfirm = false },
        )
    }
    partEdit?.let { p ->
        EditPartDialog(p, onDismiss = { partEdit = null }, onSave = { np -> repo.updatePart(np); ui.showBanner("Part saved", np.name) })
    }
    replaceFor?.let { old ->
        ReplacePartDialog(old, odo, onDismiss = { replaceFor = null }) { new, d, o, labour, note ->
            repo.replacePart(old, new, d, o, labour, note)
            if (ui.detailsId == old.id) ui.openDetails(new.id)
            ui.showBanner("Part replaced", "${new.brand} ${new.model}")
        }
    }
    eventEdit?.let { (p, initial) ->
        EventDialog(
            p.id, initial, odo,
            onDismiss = { eventEdit = null },
            onSave = { e -> repo.upsertEvent(e); ui.showBanner("Saved", p.name) },
            onDelete = initial?.let { ev -> { repo.deleteEvent(ev.id); eventEdit = null } },
        )
    }
    pendingImport?.let { uri ->
        ConfirmDialog(
            "Import backup?", "This replaces everything currently in the app.", confirmLabel = "Import",
            onConfirm = {
                repo.importFrom(uri)
                    .onSuccess { ui.showBanner("Backup restored", "All data replaced") }
                    .onFailure { ui.showBanner("Not a valid backup", "Nothing changed") }
            },
            onDismiss = { pendingImport = null },
        )
    }
}

// ---------------------------------------------------------------- gestures

/** Height (fraction) of the edge-swipe zones in the middle of both sides: the glow and the back-gesture exclusion. */
private const val EDGE_ZONE = 0.46f

private fun inEdgeBand(y: Float, heightPx: Int): Boolean = abs(y - heightPx / 2f) <= heightPx * EDGE_ZONE / 2f

private fun edgeWidthPx(widthPx: Int, density: Float): Float = max(40f * density, widthPx * 0.09f)

/**
 * Edge swipe, seen before the panels (Initial pass): a touch that starts within max(40dp, 9 % width) of the left or
 * right edge, in the middle [EDGE_ZONE] of the height (outside it Android's back gesture wins), and then moves
 * mostly sideways becomes a mode change, and its events are consumed so lists and buttons under the finger don't react. A plain tap near the edge still reaches the button under it.
 */
private suspend fun androidx.compose.ui.input.pointer.PointerInputScope.detectEdgeSwipes(ui: GameUi) {
    awaitEachGesture {
        val down = awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
        if (!ui.introDone) return@awaitEachGesture
        if (!inEdgeBand(down.position.y, size.height)) return@awaitEachGesture
        val edge = edgeWidthPx(size.width, density)
        val side = when {
            down.position.x < edge -> -1
            down.position.x > size.width - edge -> 1
            else -> return@awaitEachGesture
        }
        ui.edgeHeld = side
        ui.touch()
        val slop = viewConfiguration.touchSlop
        val minSwipe = 50.dp.toPx()
        var decided = false
        try {
            while (true) {
                val ev = awaitPointerEvent(PointerEventPass.Initial)
                val c = ev.changes.firstOrNull { it.id == down.id } ?: break
                val d = c.position - down.position
                if (!decided && abs(d.x) > slop && abs(d.x) > abs(d.y) * 1.3f) decided = true
                if (decided) ev.changes.forEach { it.consume() }
                if (!c.pressed) {
                    if (decided && abs(d.x) > minSwipe && abs(d.x) > abs(d.y) * 1.3f) ui.step(if (d.x < 0) 1 else -1)
                    break
                }
            }
        } finally {
            ui.edgeHeld = 0
        }
    }
}

/** Drag = orbit, pinch = zoom, short tap = pick a part, double tap = reset (touches that reach the 3D garage). */
private suspend fun androidx.compose.ui.input.pointer.PointerInputScope.detectGarageGestures(ui: GameUi) {
    var lastTapAt = 0L
    awaitEachGesture {
        val down = awaitFirstDown(requireUnconsumed = false)
        ui.touch()
        val edge = edgeWidthPx(size.width, density)
        val atEdge = down.position.x < edge || down.position.x > size.width - edge
        if (atEdge && inEdgeBand(down.position.y, size.height)) return@awaitEachGesture   // edge swipe zone
        if (!ui.introDone) return@awaitEachGesture
        val slop = 8.dp.toPx()
        var moved = false
        var multi = false
        var total = Offset.Zero
        var upAt = down.uptimeMillis
        while (true) {
            val ev = awaitPointerEvent()
            val pressed = ev.changes.filter { it.pressed }
            if (pressed.isEmpty()) {
                upAt = ev.changes.maxOfOrNull { it.uptimeMillis } ?: upAt
                break
            }
            if (pressed.size >= 2) {
                multi = true
                val z = ev.calculateZoom()
                if (z.isFinite() && z > 0f && z != 1f) ui.controller?.zoom(z)
                ev.changes.forEach { it.consume() }
            } else if (!multi) {
                val c = pressed[0]
                val d = c.positionChange()
                total += d
                if (!moved && total.getDistance() > slop) moved = true
                if (moved && d != Offset.Zero) {
                    ui.controller?.orbit(d.x, d.y)
                    c.consume()
                }
            }
            ui.touch()
        }
        if (!moved && !multi && upAt - down.uptimeMillis < 350) {
            if (upAt - lastTapAt < 300) {
                lastTapAt = 0L
                ui.doubleTap()
            } else {
                lastTapAt = upAt
                ui.controller?.tap(down.position.x, down.position.y)
            }
        }
    }
}
