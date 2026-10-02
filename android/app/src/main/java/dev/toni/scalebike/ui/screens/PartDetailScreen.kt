package dev.toni.scalebike.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.EventType
import dev.toni.scalebike.data.Issue
import dev.toni.scalebike.data.ServiceEvent
import dev.toni.scalebike.data.deleteEvent
import dev.toni.scalebike.data.deleteIssue
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.kmOnPart
import dev.toni.scalebike.data.money
import dev.toni.scalebike.data.odometerKm
import dev.toni.scalebike.data.replacePart
import dev.toni.scalebike.data.statusOf
import dev.toni.scalebike.data.updatePart
import dev.toni.scalebike.data.upsertEvent
import dev.toni.scalebike.data.upsertIssue
import dev.toni.scalebike.ui.Bullet
import dev.toni.scalebike.ui.Dot
import dev.toni.scalebike.ui.EditPartDialog
import dev.toni.scalebike.ui.EventDialog
import dev.toni.scalebike.ui.InfoRow
import dev.toni.scalebike.ui.IssueDialog
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.ReplacePartDialog
import dev.toni.scalebike.ui.ScreenHeader
import dev.toni.scalebike.ui.SectionCard
import dev.toni.scalebike.ui.StatusDot
import dev.toni.scalebike.ui.theme.StatusColors
import dev.toni.scalebike.ui.theme.color

@Composable
fun PartDetailScreen(data: BikeData, partId: String, onBack: () -> Unit, onOpenPart: (String) -> Unit) {
    val repo = LocalRepo.current
    val part = data.parts.find { it.id == partId }
    if (part == null) {
        Column(Modifier.fillMaxSize()) { ScreenHeader("Not found", onBack = onBack) }
        return
    }
    val status = data.statusOf(part)
    val odo = data.odometerKm()
    val events = data.events.filter { it.partId == part.id }.sortedWith(compareByDescending<ServiceEvent> { it.date }.thenByDescending { it.odoKm })
    val issues = data.issues.filter { it.partId == part.id }.sortedWith(compareBy<Issue> { it.resolved }.thenByDescending { it.date })
    val previous = data.parts.filter { it.slot == part.slot && it.id != part.id }.sortedByDescending { it.installedDate }

    var editing by remember { mutableStateOf(false) }
    var replacing by remember { mutableStateOf(false) }
    var eventDialog by remember { mutableStateOf<Pair<ServiceEvent?, EventType>?>(null) }
    var issueDialog by remember { mutableStateOf<Issue?>(null) }
    var newIssue by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(part.name, "${part.brand} ${part.model}", onBack = onBack) {
            IconButton(onClick = { editing = true }) { Icon(Icons.Filled.Edit, "Edit") }
        }
        Column(
            Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Status banner
            Surface(shape = RoundedCornerShape(16.dp), color = status.health.color().copy(alpha = 0.15f)) {
                Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    StatusDot(status.health, 14.dp)
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text(if (part.retired) "Retired" else status.health.label, fontWeight = FontWeight.SemiBold)
                        Muted(
                            if (part.retired) "Removed ${Dates.format(part.retiredDate)} after ${data.kmOnPart(part).km()}"
                            else status.summary,
                        )
                    }
                }
            }

            if (!part.retired) {
                SectionCard("Maintenance") {
                    if (part.maintenance.isNotBlank()) Text(part.maintenance, style = MaterialTheme.typography.bodyMedium)
                    part.serviceIntervalKm?.let { iv ->
                        ProgressLine("${status.kmSince.km()} of $iv km", status.kmProgress ?: 0f)
                    }
                    part.serviceIntervalDays?.let { iv ->
                        ProgressLine(
                            status.daysSince?.let { "$it of $iv days" } ?: "Every $iv days — set install date",
                            status.dayProgress ?: 0f,
                        )
                    }
                    Muted("Last serviced / checked: ${Dates.format(status.lastServiceDate)}")
                    if (part.replaceHint.isNotBlank()) Muted("Replace: ${part.replaceHint}")
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { eventDialog = null to EventType.SERVICE }, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Filled.Build, null, Modifier.height(18.dp)); Spacer(Modifier.width(6.dp)); Text("Log service")
                        }
                        OutlinedButton(onClick = { replacing = true }, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Filled.SwapHoriz, null, Modifier.height(18.dp)); Spacer(Modifier.width(6.dp)); Text("Replace")
                        }
                    }
                }
            }

            SectionCard("Details") {
                InfoRow("Brand", part.brand)
                InfoRow("Model", part.model)
                if (part.spec.isNotBlank()) InfoRow("Spec", part.spec)
                InfoRow("Origin", if (part.stock) "Stock (came with bike)" else "Upgrade / replacement")
                InfoRow("Installed", Dates.format(part.installedDate) + if (part.installedDate != null) "  (${Dates.age(part.installedDate)} ago)" else "")
                InfoRow("Odometer then", part.installedOdoKm.km())
                InfoRow("Distance on part", data.kmOnPart(part).km())
                part.price?.let { InfoRow("Price", it.money()) }
                if (part.boughtFrom.isNotBlank()) InfoRow("Bought from", part.boughtFrom)
                val spent = events.mapNotNull { it.cost }.sum()
                if (spent > 0) InfoRow("Service spend", spent.money())
            }

            if (part.description.isNotBlank() || part.pros.isNotEmpty() || part.cons.isNotEmpty()) {
                SectionCard("About this part") {
                    if (part.description.isNotBlank()) Text(part.description, style = MaterialTheme.typography.bodyMedium)
                    if (part.pros.isNotEmpty()) {
                        Text("Advantages", style = MaterialTheme.typography.labelLarge, color = StatusColors.ok)
                        part.pros.forEach { Bullet(it, "+", StatusColors.ok) }
                    }
                    if (part.cons.isNotEmpty()) {
                        Text("Disadvantages", style = MaterialTheme.typography.labelLarge, color = StatusColors.over)
                        part.cons.forEach { Bullet(it, "−", StatusColors.over) }
                    }
                }
            }

            SectionCard(
                "Issues",
                action = { TextButton(onClick = { newIssue = true }) { Icon(Icons.Filled.Add, null); Text("Report") } },
            ) {
                if (issues.isEmpty()) Muted("No issues reported.")
                issues.forEach { i ->
                    Row(
                        Modifier.fillMaxWidth().clickable { issueDialog = i }.padding(vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Dot(if (i.resolved) StatusColors.ok else i.severity.color(), 10.dp)
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text(i.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                            Muted(
                                buildString {
                                    append(Dates.format(i.date)); append(" · "); append(i.odoKm.km())
                                    append(if (i.resolved) " · resolved ${Dates.format(i.resolvedDate)}" else " · ${i.severity.label.lowercase()} · open")
                                    if (i.photos.isNotEmpty()) append(" · 📷 ${i.photos.size}")
                                },
                            )
                        }
                    }
                }
            }

            SectionCard("History") {
                if (events.isEmpty()) Muted("Nothing logged yet.")
                events.forEach { e ->
                    Row(
                        Modifier.fillMaxWidth().clickable { eventDialog = e to e.type }.padding(vertical = 6.dp),
                        verticalAlignment = Alignment.Top,
                    ) {
                        Dot(eventColor(e.type), 10.dp, )
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text(e.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                            Muted(
                                buildString {
                                    append(Dates.format(e.date)); append(" · "); append(e.odoKm.km()); append(" · "); append(e.type.label)
                                    e.cost?.let { append(" · "); append(it.money()) }
                                    if (e.doneBy.isNotBlank()) { append(" · "); append(e.doneBy) }
                                },
                            )
                            if (e.notes.isNotBlank()) Text(e.notes, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }

            if (previous.isNotEmpty()) {
                SectionCard("Other parts in this slot") {
                    previous.forEach { p ->
                        Row(Modifier.fillMaxWidth().clickable { onOpenPart(p.id) }.padding(vertical = 6.dp)) {
                            Column(Modifier.weight(1f)) {
                                Text("${p.brand} ${p.model}", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                                Muted(
                                    "${Dates.format(p.installedDate)} → ${if (p.retired) Dates.format(p.retiredDate) else "now"} · ${data.kmOnPart(p).km()}",
                                )
                            }
                        }
                    }
                }
            }

            if (part.notes.isNotBlank()) {
                SectionCard("Notes") { Text(part.notes, style = MaterialTheme.typography.bodyMedium) }
            }
        }
    }

    if (editing) EditPartDialog(part, onDismiss = { editing = false }, onSave = { repo.updatePart(it) })
    if (replacing) {
        ReplacePartDialog(part, odo, onDismiss = { replacing = false }) { new, date, o, labour, note ->
            repo.replacePart(part, new, date, o, labour, note)
            onBack()
            onOpenPart(new.id)
        }
    }
    eventDialog?.let { (existing, type) ->
        EventDialog(
            partId = part.id, initial = existing, currentOdo = odo, defaultType = type,
            onDismiss = { eventDialog = null },
            onSave = { repo.upsertEvent(it) },
            onDelete = existing?.let { e -> { repo.deleteEvent(e.id); eventDialog = null } },
        )
    }
    if (newIssue || issueDialog != null) {
        val existing = issueDialog
        IssueDialog(
            partId = part.id, initial = existing, currentOdo = odo,
            onDismiss = { newIssue = false; issueDialog = null },
            onSave = { repo.upsertIssue(it) },
            onDelete = existing?.let { i -> { repo.deleteIssue(i); issueDialog = null } },
        )
    }
}

@Composable
private fun ProgressLine(label: String, progress: Float) {
    val c = when {
        progress >= 1f -> StatusColors.over
        progress >= 0.8f -> StatusColors.soon
        else -> StatusColors.ok
    }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Muted(label)
        LinearProgressIndicator(
            progress = { progress.coerceIn(0f, 1f) },
            color = c,
            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
            modifier = Modifier.fillMaxWidth().height(8.dp),
            drawStopIndicator = {},
        )
    }
}

fun eventColor(t: EventType): Color = when (t) {
    EventType.INSTALL -> Color(0xFF5AA9FF)
    EventType.SERVICE -> StatusColors.ok
    EventType.INSPECT -> Color(0xFF9EA3AB)
    EventType.REPAIR -> StatusColors.soon
    EventType.REMOVED -> Color(0xFFB07CFF)
}
