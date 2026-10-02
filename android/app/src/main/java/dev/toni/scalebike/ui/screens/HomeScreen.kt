package dev.toni.scalebike.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Category
import dev.toni.scalebike.data.Health
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.PartStatus
import dev.toni.scalebike.data.activeParts
import dev.toni.scalebike.data.addRide
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.odometerKm
import dev.toni.scalebike.data.partForSlot
import dev.toni.scalebike.data.statusOf
import dev.toni.scalebike.ui.AddRideDialog
import dev.toni.scalebike.ui.BikeDrawing
import dev.toni.scalebike.ui.Dot
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.StatusDot
import dev.toni.scalebike.ui.theme.color

@Composable
fun HomeScreen(data: BikeData, onOpenPart: (String) -> Unit) {
    val repo = LocalRepo.current
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    var addRide by remember { mutableStateOf(false) }
    val parts = remember(data) { data.activeParts() }
    val statuses = remember(data) { parts.associate { it.id to data.statusOf(it) } }
    val healthBySlot = remember(statuses) { parts.associate { it.slot to statuses.getValue(it.id).health } }
    val attention = parts.filter { statuses.getValue(it.id).health.rank >= Health.DUE_SOON.rank }
        .sortedByDescending { statuses.getValue(it.id).health.rank }

    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(data.bike.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Muted("${data.bike.year} · Size ${data.bike.size} · ${data.bike.color}")
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(data.odometerKm().km(), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Muted("odometer")
                }
            }
        }

        item {
            Card(
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
            ) {
                BikeDrawing(healthBySlot, selected, { selected = it }, Modifier.padding(vertical = 8.dp))
                Row(Modifier.padding(start = 16.dp, end = 16.dp, bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Legend(Health.OK, "OK"); Spacer(Modifier.width(12.dp))
                    Legend(Health.DUE_SOON, "Soon"); Spacer(Modifier.width(12.dp))
                    Legend(Health.OVERDUE, "Now")
                    Spacer(Modifier.weight(1f))
                    Muted("pinch · double-tap")
                }
            }
        }

        val sel = selected?.let { data.partForSlot(it) }
        if (sel != null) {
            item(key = "selected") { PartRow(sel, statuses.getValue(sel.id), highlighted = true) { onOpenPart(sel.id) } }
        }

        item {
            FilledTonalButton(onClick = { addRide = true }, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Filled.Add, null); Spacer(Modifier.width(8.dp)); Text("Log a ride")
            }
        }

        if (attention.isNotEmpty()) {
            item { SectionTitle("Needs attention (${attention.size})") }
            items(attention, key = { "att-" + it.id }) { p -> PartRow(p, statuses.getValue(p.id)) { onOpenPart(p.id) } }
        } else {
            item { Muted("✅ Everything is up to date.", Modifier.padding(horizontal = 4.dp)) }
        }

        Category.entries.forEach { cat ->
            val inCat = parts.filter { it.category == cat }
            if (inCat.isNotEmpty()) {
                item(key = "cat-$cat") { SectionTitle(cat.label) }
                items(inCat, key = { it.id }) { p -> PartRow(p, statuses.getValue(p.id)) { onOpenPart(p.id) } }
            }
        }
    }

    if (addRide) AddRideDialog(onDismiss = { addRide = false }, onSave = { repo.addRide(it) })
}

@Composable
private fun Legend(h: Health, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Dot(h.color(), size = 8.dp); Spacer(Modifier.width(4.dp)); Muted(label)
    }
}

@Composable
fun SectionTitle(text: String) {
    Text(
        text, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(start = 4.dp, top = 8.dp),
    )
}

@Composable
fun PartRow(part: Part, status: PartStatus, highlighted: Boolean = false, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (highlighted) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainer,
        ),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
    ) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            StatusDot(status.health)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(part.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text("${part.brand} ${part.model}", style = MaterialTheme.typography.bodyMedium)
                Muted(status.summary)
            }
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
