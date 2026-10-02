package dev.toni.scalebike.data

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.updateAndGet
import kotlinx.serialization.json.Json
import java.io.File

/** Single source of truth. Data is small, so it's kept in memory and rewritten as one JSON file on every change. */
class BikeRepository(private val context: Context) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true; prettyPrint = true }
    private val file = File(context.filesDir, "bike.json")
    private val photoDir = File(context.filesDir, "photos").apply { mkdirs() }

    private val _data = MutableStateFlow(load())
    val data: StateFlow<BikeData> = _data.asStateFlow()

    private fun load(): BikeData =
        runCatching { if (file.exists()) json.decodeFromString<BikeData>(file.readText()) else null }.getOrNull()
            ?: SeedData.initial()

    fun update(transform: (BikeData) -> BikeData) {
        persist(_data.updateAndGet(transform))
    }

    @Synchronized
    private fun persist(d: BikeData) {
        val tmp = File(file.parentFile, "bike.json.tmp")
        tmp.writeText(json.encodeToString(BikeData.serializer(), d))
        if (!tmp.renameTo(file)) {
            file.delete()
            tmp.renameTo(file)
        }
    }

    fun exportTo(uri: Uri) {
        context.contentResolver.openOutputStream(uri, "wt")?.use {
            it.write(json.encodeToString(BikeData.serializer(), _data.value).toByteArray())
        }
    }

    fun importFrom(uri: Uri): Result<Unit> = runCatching {
        val text = context.contentResolver.openInputStream(uri)!!.use { it.readBytes().decodeToString() }
        val d = json.decodeFromString<BikeData>(text)
        _data.value = d
        persist(d)
    }

    /** Copies a picked image into app storage and returns its file name. */
    fun savePhoto(uri: Uri): String? = runCatching {
        val name = "${newId()}.jpg"
        context.contentResolver.openInputStream(uri)!!.use { input ->
            File(photoDir, name).outputStream().use { input.copyTo(it) }
        }
        name
    }.getOrNull()

    fun photoFile(name: String): File = File(photoDir, name)

    fun resetAll() {
        photoDir.listFiles()?.forEach { it.delete() }
        update { SeedData.initial() }
    }
}

fun BikeRepository.addRide(r: Ride) = update { it.copy(rides = it.rides + r) }

fun BikeRepository.deleteRide(id: String) = update { d -> d.copy(rides = d.rides.filterNot { it.id == id }) }

fun BikeRepository.upsertEvent(e: ServiceEvent) = update { d -> d.copy(events = d.events.filterNot { it.id == e.id } + e) }

fun BikeRepository.deleteEvent(id: String) = update { d -> d.copy(events = d.events.filterNot { it.id == id }) }

fun BikeRepository.upsertIssue(i: Issue) = update { d -> d.copy(issues = d.issues.filterNot { it.id == i.id } + i) }

fun BikeRepository.deleteIssue(issue: Issue) {
    issue.photos.forEach { photoFile(it).delete() }
    update { d -> d.copy(issues = d.issues.filterNot { it.id == issue.id }) }
}

fun BikeRepository.updatePart(p: Part) = update { d -> d.copy(parts = d.parts.map { if (it.id == p.id) p else it }) }

fun BikeRepository.replacePart(old: Part, new: Part, date: String, odo: Double, labourCost: Double?, note: String) = update { d ->
    val retired = old.copy(retired = true, retiredDate = date, retiredOdoKm = odo)
    val removed = ServiceEvent(
        newId(), old.id, date, odo, EventType.REMOVED,
        "Removed after ${(odo - old.installedOdoKm).coerceAtLeast(0.0).km()} — replaced by ${new.brand} ${new.model}".trim(), note,
    )
    val installed = ServiceEvent(
        newId(), new.id, date, odo, EventType.INSTALL,
        "Installed (replaced ${old.brand} ${old.model})".trim(), note, labourCost,
    )
    d.copy(parts = d.parts.map { if (it.id == old.id) retired else it } + new, events = d.events + removed + installed)
}

fun BikeRepository.completeSetup(purchaseDate: String?, purchasePrice: Double?, currentKm: Double, baseline: Boolean) = update { d ->
    val today = Dates.today()
    val parts = d.parts.map {
        if (it.stock && it.installedDate == null) it.copy(installedDate = purchaseDate, installedOdoKm = 0.0) else it
    }
    val baselineEvents = if (!baseline) emptyList() else parts.filter { !it.retired }.map {
        ServiceEvent(newId(), it.id, today, currentKm, EventType.INSPECT, "Baseline check at app setup")
    }
    d.copy(
        setupDone = true,
        bike = d.bike.copy(purchaseDate = purchaseDate, purchasePrice = purchasePrice, startOdometerKm = currentKm),
        parts = parts,
        events = d.events + baselineEvents,
    )
}
