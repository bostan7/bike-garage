package dev.toni.scalebike.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.ui.Field
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.ScreenHeader
import dev.toni.scalebike.ui.SectionCard
import java.util.Locale
import kotlin.math.roundToInt

private val checklist = listOf(
    "Tyre pressure checked",
    "Brakes: both levers firm, bike stops when pushed",
    "Wheels: QR levers closed tight, no wobble",
    "Headset: no knock when rocking with front brake on",
    "Chain clean & lubed, shifts through all gears",
    "Stem, bars & seatpost bolts tight",
    "Fork lockout open, rebound set",
    "Carrying: pump, tube/plug, multitool, quick link, water",
)

private val torque = listOf(
    "Stem steerer & bar clamp bolts" to "5–6 Nm",
    "Headset top cap" to "Snug only — set preload, then stem",
    "Seatpost clamp" to "5–6 Nm",
    "Saddle rail clamp" to "8–12 Nm",
    "Brake caliper mount bolts" to "6–8 Nm",
    "Brake lever clamp" to "4–6 Nm",
    "Shifter clamp" to "~3 Nm",
    "Rear derailleur mount" to "8–10 Nm",
    "Derailleur cable fixing bolt" to "6–7 Nm",
    "Centre Lock rotor lockring" to "40–50 Nm",
    "Cassette lockring" to "30–50 Nm",
    "Crank left-arm pinch bolts (HT-II)" to "12–14 Nm",
    "Crank preload cap" to "0.7–1.5 Nm (hand tight)",
    "Pedals" to "35–55 Nm",
)

@Composable
fun ToolsScreen(data: BikeData) {
    val repo = LocalRepo.current
    val checked = remember { mutableStateListOf<Int>() }
    var weight by remember(data.riderWeightKg) { mutableFloatStateOf(data.riderWeightKg.toFloat()) }
    var fitNotes by remember { mutableStateOf(data.fitNotes) }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader("Tools")
        Column(
            Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            SectionCard("Pre-ride check") {
                Muted("Last completed: ${Dates.format(data.lastChecklistDate)}")
                checklist.forEachIndexed { i, item ->
                    Row(
                        Modifier.fillMaxWidth().clickable { if (i in checked) checked.remove(i) else checked.add(i) },
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Checkbox(i in checked, { if (it) checked.add(i) else checked.remove(i) })
                        Text(item, style = MaterialTheme.typography.bodyMedium)
                    }
                }
                Button(
                    enabled = checked.size == checklist.size,
                    onClick = {
                        repo.update { it.copy(lastChecklistDate = Dates.today()) }
                        checked.clear()
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(if (checked.size == checklist.size) "All good — ride! 🚵" else "${checked.size}/${checklist.size} checked") }
            }

            SectionCard("Tyre pressure") {
                Muted("Maxxis Rekon Race 29×2.25\". Starting point — adjust ±2 psi for terrain and feel.")
                Text("Rider weight incl. kit: ${weight.roundToInt()} kg")
                Slider(
                    value = weight, onValueChange = { weight = it }, valueRange = 45f..130f,
                    onValueChangeFinished = { repo.update { it.copy(riderWeightKg = weight.roundToInt().toDouble()) } },
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Tubeless", Modifier.weight(1f))
                    Switch(data.tubeless, { v -> repo.update { it.copy(tubeless = v) } })
                }
                val front = (8 + 0.24f * weight - if (data.tubeless) 3f else 0f).coerceIn(16f, 40f)
                val rear = front + 2f
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    PressureBox("Front", front, Modifier.weight(1f))
                    PressureBox("Rear", rear, Modifier.weight(1f))
                }
            }

            SectionCard("Torque reference") {
                Muted("Typical values. Always use the number printed on the part or frame if it differs.")
                torque.forEachIndexed { i, (what, nm) ->
                    if (i > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Text(what, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
                        Text(nm, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }

            SectionCard(
                "Fit & setup notes",
                action = {
                    TextButton(enabled = fitNotes != data.fitNotes, onClick = { repo.update { it.copy(fitNotes = fitNotes) } }) { Text("Save") }
                },
            ) {
                Muted("So you can always get back to your setup after changing parts.")
                Field(fitNotes, { fitNotes = it }, "Notes", singleLine = false, minLines = 6)
            }
        }
    }
}

@Composable
private fun PressureBox(label: String, psi: Float, modifier: Modifier) {
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Muted(label)
        Text("${psi.roundToInt()} psi", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        Muted(String.format(Locale.UK, "%.2f bar", psi * 0.0689476f))
    }
}
