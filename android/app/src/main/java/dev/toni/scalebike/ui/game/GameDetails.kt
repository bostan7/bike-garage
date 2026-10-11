package dev.toni.scalebike.ui.game

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.EventType
import dev.toni.scalebike.data.Issue
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.ServiceEvent
import dev.toni.scalebike.data.Severity
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.kmOnPart
import dev.toni.scalebike.data.money
import dev.toni.scalebike.data.statusOf

// ---------------------------------------------------------------- PART DETAILS (left panel, opened from the card)

/**
 * Everything about one part (port of the old 2D part page): maintenance progress, about + pros/cons, ownership,
 * issues, history, other parts that sat in the same slot, notes. Rows open the existing edit dialogs.
 * [part] may be a retired part (opened from "other parts in this slot").
 */
@Composable
fun DetailsPanel(
    data: BikeData,
    part: Part,
    width: Dp,
    leftInset: Dp,
    onBack: () -> Unit,
    onEdit: () -> Unit,
    onEvent: (ServiceEvent) -> Unit,
    onIssue: (Issue) -> Unit,
    onOtherPart: (Part) -> Unit,
) {
    val status = data.statusOf(part)
    val events = data.events.filter { it.partId == part.id }
        .sortedWith(compareByDescending<ServiceEvent> { it.date }.thenByDescending { it.odoKm })
    val issues = data.issues.filter { it.partId == part.id }
        .sortedWith(compareBy<Issue> { it.resolved }.thenByDescending { it.date })
    val others = data.parts.filter { it.slot == part.slot && it.id != part.id }.sortedByDescending { it.installedDate }
    val kmOn = data.kmOnPart(part)

    // compact header and the Edit button at the end of the list: the landscape panel is only ~270 dp tall, and the
    // big name already shows on the card at the right (phone test: a full header left room for ~4 lines)
    LeftPanel(
        width, leftInset,
        header = {
            Column(Modifier.fillMaxWidth().padding(end = 30.dp, bottom = 4.dp)) {
                Box(Modifier.heightIn(min = 36.dp).gameClick(onClick = onBack), contentAlignment = Alignment.CenterStart) {
                    Text("‹ BACK", style = capsLabel(12.sp, G.muted, FontWeight.Bold))
                }
                Text(
                    "${part.name} · details".uppercase(), style = italicDisplay(20.sp).copy(lineHeight = 20.sp),
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
            }
        },
    ) {
        if (part.retired) {
            ListNote("Retired ${Dates.format(part.retiredDate)} after ${kmOn.km()}. The part on the bike now is shown on the right.")
        }

        // maintenance
        if (!part.retired) {
            SectionLabel("Maintenance")
            if (part.maintenance.isNotBlank()) DetailText(part.maintenance)
            part.serviceIntervalKm?.let { iv ->
                val p = status.kmProgress ?: 0f
                StatRow("Distance since service", "${groupedKm(status.kmSince)} / $iv km", p, progressColor(p))
            }
            part.serviceIntervalDays?.let { iv ->
                val p = status.dayProgress ?: 0f
                StatRow("Days since service", status.daysSince?.let { "$it / $iv" } ?: "set install date", p, progressColor(p))
            }
            Column(Modifier.padding(horizontal = 6.dp)) {
                KeyValue("Last service", status.lastServiceDate?.let { Dates.format(it) } ?: "Not logged yet")
                if (part.replaceHint.isNotBlank()) KeyValue("Replace", part.replaceHint)
            }
        }

        // about + pros / cons
        if (part.description.isNotBlank() || part.pros.isNotEmpty() || part.cons.isNotEmpty()) {
            SectionLabel("About")
            if (part.description.isNotBlank()) DetailText(part.description)
            part.pros.forEach { Bullet("+", it, G.ok) }
            part.cons.forEach { Bullet("−", it, G.over) }
        }

        // ownership
        SectionLabel("Ownership")
        Column(Modifier.padding(horizontal = 6.dp)) {
            if (part.spec.isNotBlank()) KeyValue("Spec", part.spec, bodyText(12.sp, G.muted))
            KeyValue("Origin", if (part.stock) "Stock, came with the bike" else "Upgrade / replacement")
            KeyValue(
                "Installed",
                Dates.format(part.installedDate) + (part.installedDate?.let { "  (${Dates.age(it)} ago)" } ?: ""),
            )
            KeyValue("Odo then", part.installedOdoKm.km())
            KeyValue("On this part", kmOn.km())
            part.price?.let { KeyValue("Price", it.money()) }
            if (part.boughtFrom.isNotBlank()) KeyValue("Bought from", part.boughtFrom)
            val spent = events.mapNotNull { it.cost }.sum()
            if (spent > 0) KeyValue("Service spend", spent.money())
        }

        // issues
        SectionLabel("Issues · ${issues.count { !it.resolved }} open")
        if (issues.isEmpty()) ListNote("No issues reported. REPORT ISSUE on the card adds one.")
        issues.forEach { i ->
            DetailRow(
                dot = if (i.resolved) G.ok else severityColor(i.severity),
                glow = !i.resolved,
                title = i.title,
                sub = buildString {
                    append(Dates.format(i.date)); append(" · "); append(i.odoKm.km())
                    append(if (i.resolved) " · resolved ${Dates.format(i.resolvedDate)}" else " · ${i.severity.label.lowercase()} · open")
                    if (i.photos.isNotEmpty()) append(" · ${i.photos.size} photo${if (i.photos.size == 1) "" else "s"}")
                },
                onClick = { onIssue(i) },
            )
        }

        // history
        SectionLabel("History")
        if (events.isEmpty()) ListNote("Nothing logged yet.")
        events.forEach { e ->
            DetailRow(
                dot = eventColor(e.type),
                glow = false,
                title = e.title,
                sub = buildString {
                    append(Dates.format(e.date)); append(" · "); append(e.odoKm.km()); append(" · "); append(e.type.label)
                    e.cost?.let { append(" · "); append(it.money()) }
                    if (e.doneBy.isNotBlank()) { append(" · "); append(e.doneBy) }
                    if (e.notes.isNotBlank()) { append("\n"); append(e.notes) }
                },
                onClick = { onEvent(e) },
            )
        }

        // earlier / later parts in the same slot
        if (others.isNotEmpty()) {
            SectionLabel("Other parts in this slot")
            others.forEach { p ->
                DetailRow(
                    dot = if (p.retired) G.none else G.neon,
                    glow = false,
                    title = "${p.brand} ${p.model}".trim(),
                    sub = "${Dates.format(p.installedDate)} → ${if (p.retired) Dates.format(p.retiredDate) else "now"} · ${data.kmOnPart(p).km()}",
                    onClick = { onOtherPart(p) },
                )
            }
        }

        if (part.notes.isNotBlank()) {
            SectionLabel("Notes")
            DetailText(part.notes)
        }

        Spacer(Modifier.heightIn(min = 10.dp))
        ActButton("Edit part", "Brand, model, dates, price, notes", onEdit, Modifier.fillMaxWidth())
    }
}

@Composable
private fun DetailText(text: String) {
    Text(text, style = bodyText(13.sp), modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp))
}

@Composable
private fun Bullet(mark: String, text: String, color: Color) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 2.dp)) {
        Text(mark, style = italicDisplay(15.sp, color), modifier = Modifier.width(16.dp))
        Text(text, style = bodyText(13.sp))
    }
}

/** List row like the service log: dot, italic title, muted sub-line; tap opens the edit dialog. */
@Composable
private fun DetailRow(dot: Color, glow: Boolean, title: String, sub: String, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 44.dp).gameClick(onClick = onClick).padding(horizontal = 6.dp, vertical = 6.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Box(Modifier.width(12.dp).padding(top = 5.dp)) { StatusDot(dot, glow = glow) }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(title.uppercase(), style = italicDisplay(16.sp, weight = FontWeight.Bold).copy(lineHeight = 17.sp), maxLines = 2, overflow = TextOverflow.Ellipsis)
            Text(sub, style = bodyText(12.sp, G.muted), maxLines = 4, overflow = TextOverflow.Ellipsis)
        }
    }
}

private fun progressColor(p: Float): Color = when {
    p >= 1f -> G.over
    p >= 0.8f -> G.soon
    else -> G.ok
}

private fun severityColor(s: Severity): Color = when (s) {
    Severity.HIGH -> G.over
    Severity.MEDIUM -> G.soon
    Severity.LOW -> G.muted
}

private fun eventColor(t: EventType): Color = when (t) {
    EventType.INSTALL -> G.neon
    EventType.SERVICE -> G.ok
    EventType.INSPECT -> G.muted
    EventType.REPAIR -> G.soon
    EventType.REMOVED -> G.none
}
