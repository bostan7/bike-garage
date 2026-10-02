package dev.toni.scalebike.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.money
import dev.toni.scalebike.ui.Dot
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.ScreenHeader
import dev.toni.scalebike.ui.theme.Orange
import dev.toni.scalebike.ui.theme.StatusColors
import dev.toni.scalebike.ui.theme.color

private enum class Kind(val label: String) { SERVICE("Maintenance"), ISSUE("Issues"), RIDE("Rides") }

private data class Entry(
    val key: String,
    val date: String,
    val title: String,
    val subtitle: String,
    val kind: Kind,
    val color: Color,
    val partId: String?,
)

@Composable
fun TimelineScreen(data: BikeData, onOpenPart: (String) -> Unit) {
    var filter by rememberSaveable { mutableStateOf<Kind?>(null) }
    val partsById = remember(data) { data.parts.associateBy { it.id } }
    val entries = remember(data) {
        buildList {
            data.events.forEach { e ->
                val p = partsById[e.partId]
                add(
                    Entry(
                        "e" + e.id, e.date, "${p?.name ?: "Part"} — ${e.title}",
                        listOfNotNull(e.type.label, e.odoKm.km(), e.cost?.money(), e.doneBy.takeIf { it.isNotBlank() }).joinToString(" · "),
                        Kind.SERVICE, eventColor(e.type), e.partId,
                    ),
                )
            }
            data.issues.forEach { i ->
                val p = partsById[i.partId]
                add(Entry("i" + i.id, i.date, "⚠ ${p?.name ?: "Part"}: ${i.title}", "Reported · ${i.severity.label} · ${i.odoKm.km()}", Kind.ISSUE, i.severity.color(), i.partId))
                if (i.resolved && i.resolvedDate != null) {
                    add(Entry("r" + i.id, i.resolvedDate, "✓ ${p?.name ?: "Part"}: ${i.title}", "Resolved" + if (i.resolution.isNotBlank()) " · ${i.resolution}" else "", Kind.ISSUE, StatusColors.ok, i.partId))
                }
            }
            data.rides.forEach { r ->
                add(Entry("d" + r.id, r.date, "Ride · ${r.km.km()}", r.note, Kind.RIDE, Orange, null))
            }
            data.bike.purchaseDate?.let { add(Entry("purchase", it, "🚲 Got the ${data.bike.name}", "Day one", Kind.SERVICE, Orange, null)) }
        }.sortedByDescending { it.date }
    }
    val shown = entries.filter { filter == null || it.kind == filter }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader("Timeline", "${entries.size} entries")
        Row(Modifier.horizontalScroll(rememberScrollState()).padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(filter == null, { filter = null }, label = { Text("All") })
            Kind.entries.forEach { k -> FilterChip(filter == k, { filter = if (filter == k) null else k }, label = { Text(k.label) }) }
        }
        LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            if (shown.isEmpty()) item { Muted("Nothing here yet. Log a ride, service or issue and it shows up here.") }
            var lastMonth: String? = null
            shown.forEach { e ->
                val month = Dates.formatMonth(e.date)
                if (month != lastMonth) {
                    lastMonth = month
                    item(key = "m-$month-${e.key}") { SectionTitle(month) }
                }
                item(key = e.key) {
                    Row(
                        Modifier.fillMaxWidth()
                            .clickable(enabled = e.partId != null) { e.partId?.let(onOpenPart) }
                            .padding(vertical = 8.dp, horizontal = 4.dp),
                        verticalAlignment = Alignment.Top,
                    ) {
                        Dot(e.color, 10.dp)
                        Spacer(Modifier.width(12.dp))
                        Column(Modifier.weight(1f)) {
                            Text(e.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                            if (e.subtitle.isNotBlank()) Muted(e.subtitle)
                        }
                        Muted(Dates.format(e.date))
                    }
                }
            }
        }
    }
}
