package dev.toni.scalebike.ui.game

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Category
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.PartStatus
import dev.toni.scalebike.data.Ride
import dev.toni.scalebike.data.TimelineImport
import dev.toni.scalebike.data.kmOnPart
import dev.toni.scalebike.data.money
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.odometerKm
import dev.toni.scalebike.garage.PartHealth
import java.util.Locale
import kotlin.math.roundToInt

// ---------------------------------------------------------------- panel frames

/** Left NFS menu frame: dark fade from the left edge, header, scrolling body, actions at the bottom. */
@Composable
fun LeftPanel(
    width: Dp,
    leftInset: Dp,
    modifier: Modifier = Modifier,
    header: @Composable () -> Unit,
    actions: (@Composable ColumnScope.() -> Unit)? = null,
    body: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .fillMaxHeight()
            .width(width + leftInset)
            .background(Brush.horizontalGradient(0f to G.fade, 0.72f to G.fade, 1f to Color.Transparent))
            .blockTouches()
            .padding(start = 16.dp + leftInset),
    ) {
        header()
        Column(
            Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(top = 4.dp, end = 34.dp, bottom = 10.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
            content = body,
        )
        if (actions != null) Actions(Modifier.padding(end = 30.dp), actions)
    }
}

/** Right part card frame: fade from the right edge. */
@Composable
fun RightPanel(width: Dp, rightInset: Dp, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier
            .fillMaxHeight()
            .width(width + rightInset)
            .background(Brush.horizontalGradient(0f to Color.Transparent, 0.22f to G.fade, 1f to G.fade))
            .blockTouches()
            .padding(start = 26.dp, end = 16.dp + rightInset),
        content = content,
    )
}

@Composable
internal fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), style = capsLabel(12.sp, G.neon, FontWeight.SemiBold, 0.22.em), modifier = modifier.padding(start = 6.dp, top = 12.dp, bottom = 4.dp))
}

private fun toneColor(t: LogTone) = when (t) {
    LogTone.OK -> G.ok
    LogTone.SOON -> G.soon
    LogTone.OVER -> G.over
    LogTone.NONE -> G.none
    LogTone.RIDE -> G.neon
}

// ---------------------------------------------------------------- SERVICE LOG

@Composable
fun LogPanel(entries: List<LogEntry>, width: Dp, leftInset: Dp, onEntry: (LogEntry) -> Unit, onLogRide: () -> Unit) {
    LeftPanel(
        width, leftInset,
        header = { PanelHeader("Service log", "${entries.size} entries · newest first") },
        actions = { ActButton("Log a ride", "Opens the ride form", onLogRide, Modifier.fillMaxWidth(), primary = true) },
    ) {
        if (entries.isEmpty()) ListNote("Nothing here yet. Log a ride, a service or an issue and it shows up here.")
        entries.forEach { e ->
            Row(
                Modifier.fillMaxWidth().heightIn(min = 44.dp)
                    .gameClick(enabled = e.partId != null) { onEntry(e) }
                    .padding(horizontal = 6.dp, vertical = 7.dp),
                verticalAlignment = Alignment.Top,
            ) {
                Box(Modifier.width(12.dp).padding(top = 5.dp)) {
                    StatusDot(toneColor(e.tone), glow = e.tone == LogTone.SOON || e.tone == LogTone.OVER)
                }
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(e.title.uppercase(), style = italicDisplay(17.sp, weight = FontWeight.Bold).copy(lineHeight = 18.sp), maxLines = 2, overflow = TextOverflow.Ellipsis)
                    if (e.subtitle.isNotBlank()) Text(e.subtitle, style = bodyText(12.sp, G.muted), maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
                Spacer(Modifier.width(10.dp))
                Text(shortDate(e.date), style = numText(12.sp, G.muted, FontWeight.Medium))
            }
        }
    }
}

// ---------------------------------------------------------------- PARTS (areas → parts)

@Composable
fun PartsPanel(
    data: BikeData,
    summary: GameSummary,
    area: Category?,
    selected: String?,
    width: Dp,
    leftInset: Dp,
    onArea: (Category) -> Unit,
    onPart: (String) -> Unit,
    onBack: () -> Unit,
) {
    val total = summary.partBySlot.size
    LeftPanel(
        width, leftInset,
        header = {
            if (area == null) PanelHeader("Parts", "${GAME_AREAS.size} areas · $total parts")
            else PanelHeader(area.label, "${data.partsIn(area).size} parts", onBack = onBack)
        },
    ) {
        if (area == null) {
            GAME_AREAS.forEachIndexed { i, a ->
                val parts = data.partsIn(a)
                MenuItem(i + 1, a.label, "${parts.size} parts", current = false, onClick = { onArea(a) }) {
                    parts.forEach { HealthDot(summary.healthBySlot[it.slot] ?: PartHealth.NONE) }
                }
            }
            ListNote("Pick an area, or tap a part on the bike.")
        } else {
            data.partsIn(area).forEachIndexed { i, p ->
                MenuItem(i + 1, p.name, "${p.brand} ${p.model}".trim(), current = p.slot == selected, onClick = { onPart(p.slot) }) {
                    HealthDot(summary.healthBySlot[p.slot] ?: PartHealth.NONE)
                }
            }
        }
    }
}

// ---------------------------------------------------------------- part card (right)

@Composable
fun PartCard(
    data: BikeData,
    part: Part,
    status: PartStatus,
    health: PartHealth,
    fx: GameFx,
    width: Dp,
    rightInset: Dp,
    onLogService: () -> Unit,
    onDetails: () -> Unit,
    onIssue: () -> Unit,
    onReplace: () -> Unit,
) {
    val col = healthColor(health).let { if (health == PartHealth.NONE) G.muted else it }
    RightPanel(width, rightInset) {
        // header and stats scroll together (the landscape card is only ~270 dp tall); the actions stay pinned below
        Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()).padding(top = 4.dp, bottom = 6.dp)) {
            Text(part.category.label.uppercase(), style = capsLabel(12.sp, G.neon, FontWeight.SemiBold, 0.22.em))
            Text(part.name.uppercase(), style = italicDisplay(26.sp).copy(lineHeight = 25.sp), maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 2.dp))
            Text("${part.brand} ${part.model}".trim(), style = bodyText(14.sp, G.fg, FontWeight.SemiBold), maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 3.dp))
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 6.dp)) {
                HealthDot(health)
                Spacer(Modifier.width(8.dp))
                Text(healthWord(health).uppercase(), style = italicDisplay(16.sp, col, spacing = 0.04.em))
            }
            val cond = condition(status)
            StatRow("Condition", cond?.let { (it * 100).roundToInt().toString() } ?: "—", cond ?: 0f, col)
            val w = wear(status)
            StatRow("Wear since service", w?.let { "${(it * 100).roundToInt()}%" } ?: "—", w ?: 0f, col)
            val kmOn = data.kmOnPart(part)
            StatRow("Distance on part", kmOn.km(), (kmOn / 3000.0).toFloat(), G.fg)
            Column(Modifier.padding(top = 8.dp)) {
                KeyValue("Next", status.summary)
                KeyValue(
                    "Last service",
                    status.lastServiceDate?.let { "${Dates.format(it)} · ${status.kmSince.km()} ago" } ?: "Not logged yet",
                )
                if (status.openIssues.isNotEmpty()) KeyValue("Issues", status.openIssues.joinToString("\n") { "${it.title} (${it.severity.label.lowercase()})" }, bodyText(13.sp, G.soon))
                if (part.spec.isNotBlank()) KeyValue("Spec", part.spec, bodyText(12.sp, G.muted))
                if (part.maintenance.isNotBlank()) KeyValue("Service", part.maintenance, bodyText(12.sp, G.muted))
            }
        }
        Actions {
            HoldButton("Log service", fx, onLogService, Modifier.fillMaxWidth(), hint = "Hold to confirm · today", primary = true) {
                MiniButton("Details", onDetails)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                ActButton("Report issue", "Opens the form", onIssue, Modifier.weight(1f))
                HoldButton("Replace", fx, onReplace, Modifier.weight(1f))
            }
        }
    }
}

// ---------------------------------------------------------------- WORKSHOP

@Composable
fun WorkshopPanel(
    data: BikeData,
    checked: SnapshotStateList<Int>,
    width: Dp,
    leftInset: Dp,
    onToggle: (Int) -> Unit,
    onWeight: (Int) -> Unit,
    onTubeless: (Boolean) -> Unit,
    onFitNotes: () -> Unit,
) {
    LeftPanel(width, leftInset, header = { PanelHeader("Workshop", "Pre-ride check · tyre pressure · torque · fit") }) {
        ListNote("Last pre-ride check: ${Dates.format(data.lastChecklistDate)} · ${checked.size}/${PRE_RIDE_CHECK.size}")
        PRE_RIDE_CHECK.forEachIndexed { i, (title, detail) ->
            CheckRow(title, detail, i in checked) { onToggle(i) }
        }

        SectionLabel("Tyre pressure")
        var weight by remember(data.riderWeightKg) { mutableFloatStateOf(data.riderWeightKg.toFloat()) }
        Text("RIDER + KIT ${weight.roundToInt()} KG", style = capsLabel(12.sp, G.muted, FontWeight.SemiBold, 0.14.em), modifier = Modifier.padding(start = 6.dp))
        Slider(
            value = weight, onValueChange = { weight = it }, valueRange = 45f..130f,
            onValueChangeFinished = { onWeight(weight.roundToInt()) },
            colors = SliderDefaults.colors(thumbColor = G.neon, activeTrackColor = G.neon, inactiveTrackColor = G.segOff),
            modifier = Modifier.padding(horizontal = 6.dp),
        )
        val (front, rear) = tyrePressurePsi(weight, data.tubeless)
        Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp), horizontalArrangement = Arrangement.spacedBy(22.dp), verticalAlignment = Alignment.Bottom) {
            PressureBig("Front", front)
            PressureBig("Rear", rear)
            Spacer(Modifier.weight(1f))
            ChipButton(if (data.tubeless) "Tubeless" else "Tubes", data.tubeless, { onTubeless(!data.tubeless) }, toggle = true)
        }
        ListNote("psi · Maxxis Rekon Race 29×2.25. Starting point, adjust ±2 psi for terrain and feel.")

        SectionLabel("Torque reference")
        TORQUE.forEach { (what, nm) ->
            Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(what, style = bodyText(13.sp), modifier = Modifier.weight(1f))
                Text(nm, style = numText(13.sp, G.neon))
            }
        }
        ListNote("Typical values. Use the number printed on the part or frame if it differs.")

        SectionLabel("Fit & setup notes")
        Text(data.fitNotes.ifBlank { "No notes yet." }, style = bodyText(13.sp), modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
        Spacer(Modifier.height(4.dp))
        ActButton("Edit fit notes", "Saddle height, spacers, fork clicks, pressures", onFitNotes, Modifier.fillMaxWidth())
    }
}

@Composable
private fun PressureBig(label: String, psi: Float) {
    Column {
        Text(label.uppercase(), style = capsLabel(12.sp))
        Text(psi.roundToInt().toString(), style = numText(36.sp))
        Text(String.format(Locale.UK, "%.2f bar", psi * 0.0689476f), style = numText(12.sp, G.muted, FontWeight.Medium))
    }
}

/** Pre-ride check row (prototype `.check`): skewed box, italic label; ticked = neon box, muted label. */
@Composable
private fun CheckRow(title: String, detail: String, checked: Boolean, onToggle: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 44.dp).gameClick(role = Role.Checkbox, onClick = onToggle).padding(horizontal = 6.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Canvas(Modifier.size(22.dp, 16.dp)) {
            val p = skewedPath(2.dp.toPx(), 18.dp.toPx(), 0f, size.height, 14f)
            if (checked) {
                drawGlow(p, G.neonDim, 10.dp.toPx())
                drawPath(p, G.neon)
            } else {
                drawPath(p, G.muted, style = Stroke(2.dp.toPx()))
            }
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(title.uppercase(), style = italicDisplay(17.sp, if (checked) G.muted else G.fg, FontWeight.Bold))
            Text(detail, style = bodyText(12.sp, G.muted), maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

// ---------------------------------------------------------------- BIKE

@Composable
fun BikePanel(
    data: BikeData,
    fx: GameFx,
    width: Dp,
    leftInset: Dp,
    onLogRide: () -> Unit,
    onEditBike: () -> Unit,
    onCorrectOdo: () -> Unit,
    onDeleteRide: (Ride) -> Unit,
    onExport: () -> Unit,
    onImport: () -> Unit,
    onReset: () -> Unit,
    onTimeline: () -> Unit,
) {
    LeftPanel(width, leftInset, header = { PanelHeader("Bike", "Info · rides · costs · backup") }) {
        Column(Modifier.padding(start = 6.dp, end = 6.dp, top = 4.dp, bottom = 4.dp)) {
            KeyValue("Model", "${data.bike.name} (${data.bike.year}) · art. 280483")
            KeyValue("Size / colour", "${data.bike.size} · ${data.bike.color}")
            KeyValue(
                "Purchased",
                Dates.format(data.bike.purchaseDate) + if (data.bike.purchaseDate != null) " (${Dates.age(data.bike.purchaseDate)} ago)" else "",
            )
        }
        ActButton("Edit bike info", null, onEditBike, Modifier.fillMaxWidth())

        SectionLabel("Odometer")
        Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(groupedKm(data.odometerKm()), style = numText(36.sp))
                    Text(" KM", style = numText(14.sp, G.muted), modifier = Modifier.padding(bottom = 4.dp))
                }
                Text("${data.rides.size} rides · ${data.rides.sumOf { it.km }.km()} logged", style = bodyText(12.sp, G.muted))
            }
            MiniButton("Correct", onCorrectOdo)
        }
        Spacer(Modifier.height(4.dp))
        ActButton("Log a ride", "Opens the ride form", onLogRide, Modifier.fillMaxWidth(), primary = true)

        // ride km from a Google Maps Timeline export (data/TimelineImport.kt)
        SectionLabel("From Google Timeline")
        val tlDays = data.rides.count { it.id.startsWith(TimelineImport.ID_PREFIX) }
        ListNote(
            data.lastTimelineImport?.let { "Last import ${Dates.format(it)} · $tlDays days from Timeline. Export a fresh file and import again any time: days are never counted twice." }
                ?: "Phone Settings → Location → Location services → Timeline → Export Timeline data, then hold below. Only bike trips are used, one ride per day.",
        )
        HoldButton("Import rides from Timeline", fx, onTimeline, Modifier.fillMaxWidth(), hint = "Hold · pick Timeline.json")

        val recent = data.rides.sortedByDescending { it.date }.take(15)
        if (recent.isNotEmpty()) SectionLabel("Recent rides")
        recent.forEach { r ->
            Row(Modifier.fillMaxWidth().padding(start = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f).padding(vertical = 4.dp)) {
                    Text(r.km.km().uppercase(), style = italicDisplay(17.sp, weight = FontWeight.Bold))
                    Text(Dates.format(r.date) + if (r.note.isNotBlank()) " · ${r.note}" else "", style = bodyText(12.sp, G.muted), maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                MiniButton("✕") { onDeleteRide(r) }
            }
        }

        // costs (bike + new parts + service/labour, running cost without the bike itself)
        val bikePrice = data.bike.purchasePrice ?: 0.0
        val upgrades = data.parts.filter { !it.stock }.mapNotNull { it.price }.sum()
        val service = data.events.mapNotNull { it.cost }.sum()
        val odo = data.odometerKm()
        SectionLabel("Costs")
        Column(Modifier.padding(horizontal = 6.dp)) {
            KeyValue("Bike", bikePrice.money())
            KeyValue("New parts", upgrades.money())
            KeyValue("Service", service.money())
            KeyValue("Total", (bikePrice + upgrades + service).money(), numText(14.sp, G.neon))
            if (odo > 0) KeyValue("Per km", "${((upgrades + service) / odo).money()} (parts + service)")
        }

        SectionLabel("Backup")
        ListNote("Saves parts, history, issues and rides to a file (photos are not included). Keep a copy in Google Drive.")
        HoldButton("Export backup", fx, onExport, Modifier.fillMaxWidth(), hint = "Hold · choose where to save")
        Spacer(Modifier.height(5.dp))
        HoldButton("Import backup", fx, onImport, Modifier.fillMaxWidth(), hint = "Hold · replaces all data after a check")

        SectionLabel("Danger zone")
        HoldButton("Reset all data", fx, onReset, Modifier.fillMaxWidth(), hint = "Hold · then confirm · starts the setup again")
    }
}
