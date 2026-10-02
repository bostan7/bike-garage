package dev.toni.scalebike.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddAPhoto
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import coil.compose.AsyncImage
import dev.toni.scalebike.data.BikeInfo
import dev.toni.scalebike.data.Dates
import dev.toni.scalebike.data.EventType
import dev.toni.scalebike.data.Issue
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.Ride
import dev.toni.scalebike.data.ServiceEvent
import dev.toni.scalebike.data.Severity
import dev.toni.scalebike.data.newId
import dev.toni.scalebike.data.plain
import dev.toni.scalebike.data.toNum
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
private fun FormDialog(
    title: String,
    onDismiss: () -> Unit,
    saveEnabled: Boolean = true,
    saveLabel: String = "Save",
    onSave: () -> Unit,
    onDelete: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    var confirmDelete by remember { mutableStateOf(false) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
        },
        confirmButton = { TextButton(enabled = saveEnabled, onClick = onSave) { Text(saveLabel) } },
        dismissButton = {
            Row {
                if (onDelete != null) {
                    TextButton(onClick = { confirmDelete = true }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
                }
                TextButton(onClick = onDismiss) { Text("Cancel") }
            }
        },
    )
    if (confirmDelete && onDelete != null) {
        ConfirmDialog("Delete?", "This can't be undone.", onConfirm = onDelete, onDismiss = { confirmDelete = false })
    }
}

@Composable
private fun <T> Segmented(options: List<T>, selected: T, label: (T) -> String, onSelect: (T) -> Unit) {
    SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
        options.forEachIndexed { i, o ->
            SegmentedButton(
                selected = o == selected,
                onClick = { onSelect(o) },
                shape = SegmentedButtonDefaults.itemShape(i, options.size),
            ) { Text(label(o), maxLines = 1) }
        }
    }
}

// ---------------------------------------------------------------- rides & odometer

@Composable
fun AddRideDialog(onDismiss: () -> Unit, onSave: (Ride) -> Unit) {
    var date by remember { mutableStateOf<String?>(Dates.today()) }
    var km by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    val kmVal = km.toNum()
    FormDialog(
        "Add ride", onDismiss,
        saveEnabled = kmVal != null && kmVal > 0,
        onSave = { onSave(Ride(newId(), date ?: Dates.today(), kmVal!!, note.trim())); onDismiss() },
    ) {
        DateField("Date", date, { date = it })
        Field(km, { km = it }, "Distance (km)", number = true)
        Field(note, { note = it }, "Note (optional)")
    }
}

@Composable
fun OdometerDialog(current: Double, onDismiss: () -> Unit, onSave: (Double) -> Unit) {
    var km by remember { mutableStateOf(String.format(java.util.Locale.UK, "%.1f", current)) }
    val v = km.toNum()
    FormDialog("Correct odometer", onDismiss, saveEnabled = v != null && v >= 0, onSave = { onSave(v!!); onDismiss() }) {
        Muted("Enter the bike's real total distance (e.g. from your bike computer or Strava). Logged rides are kept.")
        Field(km, { km = it }, "Total km", number = true)
    }
}

@Composable
fun BikeInfoDialog(bike: BikeInfo, onDismiss: () -> Unit, onSave: (BikeInfo) -> Unit) {
    var name by remember { mutableStateOf(bike.name) }
    var year by remember { mutableStateOf(bike.year.toString()) }
    var size by remember { mutableStateOf(bike.size) }
    var color by remember { mutableStateOf(bike.color) }
    var date by remember { mutableStateOf(bike.purchaseDate) }
    var price by remember { mutableStateOf(bike.purchasePrice?.plain().orEmpty()) }
    FormDialog("Bike info", onDismiss, onSave = {
        onSave(
            bike.copy(
                name = name.trim(), year = year.toIntOrNull() ?: bike.year, size = size.trim(), color = color.trim(),
                purchaseDate = date, purchasePrice = price.toNum(),
            ),
        )
        onDismiss()
    }) {
        Field(name, { name = it }, "Name")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field(year, { year = it }, "Year", Modifier.weight(1f), number = true)
            Field(size, { size = it }, "Size", Modifier.weight(1f))
        }
        Field(color, { color = it }, "Colour")
        DateField("Purchase date", date, { date = it }, allowClear = true)
        Field(price, { price = it }, "Purchase price (€)", number = true)
    }
}

// ---------------------------------------------------------------- service events

@Composable
fun EventDialog(
    partId: String,
    initial: ServiceEvent?,
    currentOdo: Double,
    defaultType: EventType = EventType.SERVICE,
    onDismiss: () -> Unit,
    onSave: (ServiceEvent) -> Unit,
    onDelete: (() -> Unit)? = null,
) {
    val editableTypes = listOf(EventType.SERVICE, EventType.INSPECT, EventType.REPAIR)
    var type by remember { mutableStateOf(initial?.type ?: defaultType) }
    var date by remember { mutableStateOf<String?>(initial?.date ?: Dates.today()) }
    var odo by remember { mutableStateOf((initial?.odoKm ?: currentOdo).plain()) }
    var title by remember { mutableStateOf(initial?.title.orEmpty()) }
    var notes by remember { mutableStateOf(initial?.notes.orEmpty()) }
    var cost by remember { mutableStateOf(initial?.cost?.plain().orEmpty()) }
    var doneBy by remember { mutableStateOf(initial?.doneBy ?: "Me") }

    FormDialog(
        if (initial == null) "Log maintenance" else "Edit entry", onDismiss,
        saveEnabled = odo.toNum() != null,
        onSave = {
            onSave(
                ServiceEvent(
                    id = initial?.id ?: newId(), partId = partId, date = date ?: Dates.today(), odoKm = odo.toNum() ?: currentOdo,
                    type = type, title = title.trim().ifEmpty { type.label }, notes = notes.trim(), cost = cost.toNum(), doneBy = doneBy.trim(),
                ),
            )
            onDismiss()
        },
        onDelete = onDelete,
    ) {
        if (type in editableTypes) {
            Segmented(editableTypes, type, { it.label }) { type = it }
        } else {
            Muted("Type: ${type.label}")
        }
        DateField("Date", date, { date = it })
        Field(odo, { odo = it }, "Odometer (km)", number = true)
        Field(title, { title = it }, "What was done (e.g. new pads, cleaned & lubed)")
        Field(notes, { notes = it }, "Notes", singleLine = false, minLines = 2)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field(cost, { cost = it }, "Cost (€)", Modifier.weight(1f), number = true)
            Field(doneBy, { doneBy = it }, "Done by", Modifier.weight(1f))
        }
    }
}

// ---------------------------------------------------------------- issues

@Composable
fun IssueDialog(
    partId: String,
    initial: Issue?,
    currentOdo: Double,
    onDismiss: () -> Unit,
    onSave: (Issue) -> Unit,
    onDelete: (() -> Unit)? = null,
) {
    val repo = LocalRepo.current
    val scope = rememberCoroutineScope()
    var title by remember { mutableStateOf(initial?.title.orEmpty()) }
    var desc by remember { mutableStateOf(initial?.description.orEmpty()) }
    var severity by remember { mutableStateOf(initial?.severity ?: Severity.MEDIUM) }
    var date by remember { mutableStateOf<String?>(initial?.date ?: Dates.today()) }
    var odo by remember { mutableStateOf((initial?.odoKm ?: currentOdo).plain()) }
    var resolved by remember { mutableStateOf(initial?.resolved ?: false) }
    var resolvedDate by remember { mutableStateOf(initial?.resolvedDate) }
    var resolution by remember { mutableStateOf(initial?.resolution.orEmpty()) }
    val photos = remember { mutableStateListOf<String>().apply { addAll(initial?.photos.orEmpty()) } }
    var viewing by remember { mutableStateOf<String?>(null) }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(6)) { uris ->
        scope.launch {
            val names = withContext(Dispatchers.IO) { uris.mapNotNull { repo.savePhoto(it) } }
            photos.addAll(names)
        }
    }

    FormDialog(
        if (initial == null) "Report issue" else "Issue", onDismiss,
        saveEnabled = title.isNotBlank(),
        onSave = {
            onSave(
                Issue(
                    id = initial?.id ?: newId(), partId = partId, date = date ?: Dates.today(), odoKm = odo.toNum() ?: currentOdo,
                    title = title.trim(), description = desc.trim(), severity = severity, resolved = resolved,
                    resolvedDate = if (resolved) resolvedDate ?: Dates.today() else null, resolution = resolution.trim(), photos = photos.toList(),
                ),
            )
            onDismiss()
        },
        onDelete = onDelete,
    ) {
        Field(title, { title = it }, "What's wrong? (e.g. creaking when pedalling)")
        Field(desc, { desc = it }, "Details", singleLine = false, minLines = 3)
        Text("Severity", style = MaterialTheme.typography.labelLarge)
        Segmented(Severity.entries, severity, { it.label }) { severity = it }
        DateField("Noticed on", date, { date = it })
        Field(odo, { odo = it }, "Odometer (km)", number = true)

        Text("Photos", style = MaterialTheme.typography.labelLarge)
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            photos.forEach { name ->
                Box(Modifier.size(76.dp)) {
                    AsyncImage(
                        model = repo.photoFile(name), contentDescription = null, contentScale = ContentScale.Crop,
                        modifier = Modifier.size(76.dp).clip(RoundedCornerShape(10.dp)).clickable { viewing = name },
                    )
                    Icon(
                        Icons.Filled.Close, "Remove", tint = Color.White,
                        modifier = Modifier.align(Alignment.TopEnd).padding(3.dp).size(20.dp)
                            .clip(RoundedCornerShape(10.dp)).background(Color(0xAA000000))
                            .clickable { photos.remove(name); repo.photoFile(name).delete() },
                    )
                }
            }
            OutlinedButton(
                onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                modifier = Modifier.size(76.dp), shape = RoundedCornerShape(10.dp),
            ) { Icon(Icons.Filled.AddAPhoto, "Add photo") }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Resolved", Modifier.weight(1f), style = MaterialTheme.typography.labelLarge)
            Switch(resolved, { resolved = it; if (it && resolvedDate == null) resolvedDate = Dates.today() })
        }
        if (resolved) {
            DateField("Resolved on", resolvedDate, { resolvedDate = it })
            Field(resolution, { resolution = it }, "How was it fixed?", singleLine = false, minLines = 2)
        }
    }

    viewing?.let { name ->
        Dialog(onDismissRequest = { viewing = null }) {
            AsyncImage(
                model = repo.photoFile(name), contentDescription = null, contentScale = ContentScale.Fit,
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).clickable { viewing = null },
            )
        }
    }
}

// ---------------------------------------------------------------- parts

@Composable
fun ReplacePartDialog(
    old: Part,
    currentOdo: Double,
    onDismiss: () -> Unit,
    onSave: (newPart: Part, date: String, odo: Double, labour: Double?, note: String) -> Unit,
) {
    var brand by remember { mutableStateOf(old.brand) }
    var model by remember { mutableStateOf("") }
    var spec by remember { mutableStateOf(old.spec) }
    var date by remember { mutableStateOf<String?>(Dates.today()) }
    var odo by remember { mutableStateOf(currentOdo.plain()) }
    var price by remember { mutableStateOf("") }
    var from by remember { mutableStateOf("") }
    var labour by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    FormDialog(
        "Replace ${old.name.lowercase()}", onDismiss, saveLabel = "Replace",
        saveEnabled = brand.isNotBlank() && model.isNotBlank() && odo.toNum() != null,
        onSave = {
            val d = date ?: Dates.today()
            val o = odo.toNum() ?: currentOdo
            val new = old.copy(
                id = newId(), brand = brand.trim(), model = model.trim(), spec = spec.trim(), stock = false,
                installedDate = d, installedOdoKm = o, price = price.toNum(), boughtFrom = from.trim(),
                pros = emptyList(), cons = emptyList(), notes = "", retired = false, retiredDate = null, retiredOdoKm = null,
            )
            onSave(new, d, o, labour.toNum(), note.trim())
            onDismiss()
        },
    ) {
        Muted("The current ${old.brand} ${old.model} moves to this slot's history with its distance.")
        Field(brand, { brand = it }, "Brand")
        Field(model, { model = it }, "Model")
        Field(spec, { spec = it }, "Spec", singleLine = false)
        DateField("Installed on", date, { date = it })
        Field(odo, { odo = it }, "Odometer (km)", number = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field(price, { price = it }, "Part price (€)", Modifier.weight(1f), number = true)
            Field(labour, { labour = it }, "Labour (€)", Modifier.weight(1f), number = true)
        }
        Field(from, { from = it }, "Bought from")
        Field(note, { note = it }, "Why replaced?", singleLine = false)
    }
}

@Composable
fun EditPartDialog(part: Part, onDismiss: () -> Unit, onSave: (Part) -> Unit) {
    var brand by remember { mutableStateOf(part.brand) }
    var model by remember { mutableStateOf(part.model) }
    var spec by remember { mutableStateOf(part.spec) }
    var installed by remember { mutableStateOf(part.installedDate) }
    var installedOdo by remember { mutableStateOf(part.installedOdoKm.plain()) }
    var price by remember { mutableStateOf(part.price?.plain().orEmpty()) }
    var from by remember { mutableStateOf(part.boughtFrom) }
    var stock by remember { mutableStateOf(part.stock) }
    var km by remember { mutableStateOf(part.serviceIntervalKm?.toString().orEmpty()) }
    var days by remember { mutableStateOf(part.serviceIntervalDays?.toString().orEmpty()) }
    var maintenance by remember { mutableStateOf(part.maintenance) }
    var description by remember { mutableStateOf(part.description) }
    var pros by remember { mutableStateOf(part.pros.joinToString("\n")) }
    var cons by remember { mutableStateOf(part.cons.joinToString("\n")) }
    var hint by remember { mutableStateOf(part.replaceHint) }
    var notes by remember { mutableStateOf(part.notes) }

    fun lines(s: String) = s.lines().map { it.trim().removePrefix("•").removePrefix("-").trim() }.filter { it.isNotEmpty() }

    FormDialog("Edit ${part.name.lowercase()}", onDismiss, onSave = {
        onSave(
            part.copy(
                brand = brand.trim(), model = model.trim(), spec = spec.trim(), installedDate = installed,
                installedOdoKm = installedOdo.toNum() ?: part.installedOdoKm, price = price.toNum(), boughtFrom = from.trim(),
                stock = stock, serviceIntervalKm = km.toIntOrNull(), serviceIntervalDays = days.toIntOrNull(),
                maintenance = maintenance.trim(), description = description.trim(), pros = lines(pros), cons = lines(cons),
                replaceHint = hint.trim(), notes = notes.trim(),
            ),
        )
        onDismiss()
    }) {
        Field(brand, { brand = it }, "Brand")
        Field(model, { model = it }, "Model")
        Field(spec, { spec = it }, "Spec", singleLine = false)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(stock, { stock = it })
            Text("Stock part (came with the bike)")
        }
        DateField("Installed on", installed, { installed = it }, allowClear = true)
        Field(installedOdo, { installedOdo = it }, "Odometer at install (km)", number = true)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field(price, { price = it }, "Price (€)", Modifier.weight(1f), number = true)
            Field(from, { from = it }, "Bought from", Modifier.weight(1f))
        }
        Text("Service interval (leave empty to ignore)", style = MaterialTheme.typography.labelLarge)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field(km, { km = it }, "Every km", Modifier.weight(1f), number = true)
            Field(days, { days = it }, "Every days", Modifier.weight(1f), number = true)
        }
        Field(maintenance, { maintenance = it }, "What to do at service", singleLine = false, minLines = 2)
        Field(hint, { hint = it }, "When to replace", singleLine = false)
        Field(description, { description = it }, "Description", singleLine = false)
        Field(pros, { pros = it }, "Advantages (one per line)", singleLine = false, minLines = 3)
        Field(cons, { cons = it }, "Disadvantages (one per line)", singleLine = false, minLines = 3)
        Field(notes, { notes = it }, "Personal notes", singleLine = false, minLines = 2)
    }
}
