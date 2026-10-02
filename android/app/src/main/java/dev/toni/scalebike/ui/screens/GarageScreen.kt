package dev.toni.scalebike.ui.screens

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.Ride
import dev.toni.scalebike.data.addRide
import dev.toni.scalebike.data.deleteRide
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.money
import dev.toni.scalebike.data.odometerKm
import dev.toni.scalebike.ui.AddRideDialog
import dev.toni.scalebike.ui.BikeInfoDialog
import dev.toni.scalebike.ui.ConfirmDialog
import dev.toni.scalebike.ui.InfoRow
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.OdometerDialog
import dev.toni.scalebike.ui.ScreenHeader
import dev.toni.scalebike.ui.SectionCard

@Composable
fun GarageScreen(data: BikeData) {
    val repo = LocalRepo.current
    val context = LocalContext.current
    var editBike by remember { mutableStateOf(false) }
    var addRide by remember { mutableStateOf(false) }
    var fixOdo by remember { mutableStateOf(false) }
    var deleteRide by remember { mutableStateOf<Ride?>(null) }
    var confirmReset by remember { mutableStateOf(false) }
    var pendingImport by remember { mutableStateOf<android.net.Uri?>(null) }

    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) {
            runCatching { repo.exportTo(uri) }
                .onSuccess { Toast.makeText(context, "Backup saved", Toast.LENGTH_SHORT).show() }
                .onFailure { Toast.makeText(context, "Backup failed: ${it.message}", Toast.LENGTH_LONG).show() }
        }
    }
    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri -> pendingImport = uri }

    val odo = data.odometerKm()
    val upgrades = data.parts.filter { !it.stock }.mapNotNull { it.price }.sum()
    val service = data.events.mapNotNull { it.cost }.sum()
    val bikePrice = data.bike.purchasePrice ?: 0.0
    val total = bikePrice + upgrades + service

    Column(Modifier.fillMaxSize()) {
        ScreenHeader("Garage")
        Column(
            Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            SectionCard("Bike", action = { TextButton(onClick = { editBike = true }) { Text("Edit") } }) {
                InfoRow("Model", "${data.bike.name} (${data.bike.year})")
                InfoRow("Size / colour", "${data.bike.size} · ${data.bike.color}")
                InfoRow("Purchased", Dates.format(data.bike.purchaseDate) + if (data.bike.purchaseDate != null) "  (${Dates.age(data.bike.purchaseDate)} ago)" else "")
                data.bike.purchasePrice?.let { InfoRow("Price", it.money()) }
                InfoRow("Weight (stock)", "≈ 13–14 kg")
            }

            SectionCard("Distance", action = { TextButton(onClick = { fixOdo = true }) { Text("Correct") } }) {
                Text(odo.km(), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Muted("${data.rides.size} rides logged · ${data.rides.sumOf { it.km }.km()} since setup")
                Button(onClick = { addRide = true }, modifier = Modifier.fillMaxWidth()) { Text("Log a ride") }
                val recent = data.rides.sortedByDescending { it.date }.take(15)
                recent.forEachIndexed { i, r ->
                    if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(r.km.km(), fontWeight = FontWeight.Medium)
                            Muted(Dates.format(r.date) + if (r.note.isNotBlank()) " · ${r.note}" else "")
                        }
                        IconButton(onClick = { deleteRide = r }) { Icon(Icons.Filled.Delete, "Delete ride", tint = MaterialTheme.colorScheme.onSurfaceVariant) }
                    }
                }
            }

            SectionCard("Costs") {
                InfoRow("Bike", bikePrice.money())
                InfoRow("Upgrades / new parts", upgrades.money())
                InfoRow("Service & labour", service.money())
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                InfoRow("Total", total.money())
                if (odo > 0) InfoRow("Running cost", "${((upgrades + service) / odo).money()} / km")
            }

            SectionCard("Backup") {
                Muted("Saves all parts, history, issues and rides to a file (photos are not included). Keep a copy in Google Drive.")
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { exporter.launch("scale980-backup-${Dates.today()}.json") }, modifier = Modifier.weight(1f)) { Text("Export") }
                    OutlinedButton(onClick = { importer.launch(arrayOf("application/json", "text/plain", "application/octet-stream")) }, modifier = Modifier.weight(1f)) { Text("Import") }
                }
            }

            SectionCard("Danger zone") {
                OutlinedButton(onClick = { confirmReset = true }, modifier = Modifier.fillMaxWidth()) {
                    Text("Reset all data", color = MaterialTheme.colorScheme.error)
                }
            }
        }
    }

    if (editBike) BikeInfoDialog(data.bike, onDismiss = { editBike = false }, onSave = { b -> repo.update { it.copy(bike = b) } })
    if (addRide) AddRideDialog(onDismiss = { addRide = false }, onSave = { repo.addRide(it) })
    if (fixOdo) {
        OdometerDialog(odo, onDismiss = { fixOdo = false }) { total ->
            repo.update { d -> d.copy(bike = d.bike.copy(startOdometerKm = total - d.rides.sumOf { it.km })) }
        }
    }
    deleteRide?.let { r ->
        ConfirmDialog("Delete ride?", "${r.km.km()} on ${Dates.format(r.date)}", onConfirm = { repo.deleteRide(r.id) }, onDismiss = { deleteRide = null })
    }
    pendingImport?.let { uri ->
        ConfirmDialog(
            "Import backup?", "This replaces everything currently in the app.", confirmLabel = "Import",
            onConfirm = {
                repo.importFrom(uri)
                    .onSuccess { Toast.makeText(context, "Backup restored", Toast.LENGTH_SHORT).show() }
                    .onFailure { Toast.makeText(context, "Not a valid backup file", Toast.LENGTH_LONG).show() }
            },
            onDismiss = { pendingImport = null },
        )
    }
    if (confirmReset) {
        ConfirmDialog(
            "Reset everything?", "Deletes all history, issues, rides and photos and starts fresh. Export a backup first!",
            confirmLabel = "Reset", onConfirm = { repo.resetAll() }, onDismiss = { confirmReset = false },
        )
    }
}
