package dev.toni.scalebike.data

import kotlinx.serialization.Serializable

/** Everything the app stores, persisted as a single JSON document. */
@Serializable
data class BikeData(
    val version: Int = 1,
    val setupDone: Boolean = false,
    val bike: BikeInfo = BikeInfo(),
    val parts: List<Part> = emptyList(),
    val events: List<ServiceEvent> = emptyList(),
    val issues: List<Issue> = emptyList(),
    val rides: List<Ride> = emptyList(),
    val riderWeightKg: Double = 75.0,
    val tubeless: Boolean = false,
    val lastChecklistDate: String? = null,
    val fitNotes: String = DEFAULT_FIT_NOTES,
)

const val DEFAULT_FIT_NOTES = """Saddle height (BB centre → top of saddle): ___ mm
Saddle setback / rail position: ___
Saddle tilt: level
Stem spacers below stem: ___ mm
Fork preload clicks / rebound clicks: ___ / ___
Tyre pressure F / R: ___ / ___ psi"""

@Serializable
data class BikeInfo(
    val name: String = "Scott Scale 980",
    val year: Int = 2022,
    val size: String = "L",
    val color: String = "Black",
    val purchaseDate: String? = null,
    val purchasePrice: Double? = null,
    /** Odometer reading when the app was set up; total = start + all logged rides. */
    val startOdometerKm: Double = 0.0,
)

@Serializable
enum class Category(val label: String) {
    FRAME("Frame & fork"),
    COCKPIT("Cockpit"),
    BRAKES("Brakes"),
    DRIVETRAIN("Drivetrain"),
    WHEELS("Wheels & tyres"),
    CONTACT("Saddle & seatpost"),
}

@Serializable
data class Part(
    val id: String,
    /** Position on the bike drawing; several parts can share a slot over time (replacements). */
    val slot: String,
    val category: Category,
    val name: String,
    val brand: String,
    val model: String,
    val spec: String = "",
    val stock: Boolean = true,
    val installedDate: String? = null,
    val installedOdoKm: Double = 0.0,
    val price: Double? = null,
    val boughtFrom: String = "",
    val description: String = "",
    val pros: List<String> = emptyList(),
    val cons: List<String> = emptyList(),
    val maintenance: String = "",
    val serviceIntervalKm: Int? = null,
    val serviceIntervalDays: Int? = null,
    val replaceHint: String = "",
    val notes: String = "",
    val retired: Boolean = false,
    val retiredDate: String? = null,
    val retiredOdoKm: Double? = null,
)

@Serializable
enum class EventType(val label: String) {
    INSTALL("Installed"),
    SERVICE("Service"),
    INSPECT("Inspection"),
    REPAIR("Repair"),
    REMOVED("Removed"),
}

@Serializable
data class ServiceEvent(
    val id: String,
    val partId: String,
    val date: String,
    val odoKm: Double,
    val type: EventType,
    val title: String,
    val notes: String = "",
    val cost: Double? = null,
    val doneBy: String = "",
)

@Serializable
enum class Severity(val label: String) { LOW("Low"), MEDIUM("Medium"), HIGH("High") }

@Serializable
data class Issue(
    val id: String,
    val partId: String,
    val date: String,
    val odoKm: Double,
    val title: String,
    val description: String = "",
    val severity: Severity = Severity.MEDIUM,
    val resolved: Boolean = false,
    val resolvedDate: String? = null,
    val resolution: String = "",
    val photos: List<String> = emptyList(),
)

@Serializable
data class Ride(
    val id: String,
    val date: String,
    val km: Double,
    val note: String = "",
)
