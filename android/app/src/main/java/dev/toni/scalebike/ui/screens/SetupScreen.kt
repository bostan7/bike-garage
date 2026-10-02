package dev.toni.scalebike.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Health
import dev.toni.scalebike.data.completeSetup
import dev.toni.scalebike.data.toNum
import dev.toni.scalebike.ui.BikeDrawing
import dev.toni.scalebike.ui.DateField
import dev.toni.scalebike.ui.Field
import dev.toni.scalebike.ui.LocalRepo
import dev.toni.scalebike.ui.Muted
import dev.toni.scalebike.ui.SectionCard

@Composable
fun SetupScreen(data: BikeData, modifier: Modifier = Modifier) {
    val repo = LocalRepo.current
    var purchase by remember { mutableStateOf<String?>(null) }
    var price by remember { mutableStateOf("") }
    var km by remember { mutableStateOf("") }
    var baseline by remember { mutableStateOf(true) }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Welcome 👋", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text(
            "${data.bike.name} · ${data.bike.year} · size ${data.bike.size} · ${data.bike.color.lowercase()}",
            style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary,
        )
        BikeDrawing(health = data.parts.associate { it.slot to Health.OK }, selected = null, onSelect = {})
        Muted("All ${data.parts.size} stock parts are pre-loaded. A few details so the maintenance timers start from the right place:")

        SectionCard(null) {
            DateField("When did you get the bike?", purchase, { purchase = it }, allowClear = true)
            Field(price, { price = it }, "Purchase price (€, optional)", number = true)
            Field(km, { km = it }, "Distance ridden so far (km, a guess is fine)", number = true)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(baseline, { baseline = it })
                Column {
                    Text("Start service timers from today")
                    Muted("Tick if the bike is in good shape now. Untick to count from the purchase date (many parts will show as overdue).")
                }
            }
        }

        Button(
            onClick = { repo.completeSetup(purchase, price.toNum(), km.toNum() ?: 0.0, baseline) },
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) { Text("Let's ride") }
    }
}
