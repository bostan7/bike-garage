package dev.toni.scalebike.data

enum class Health(val rank: Int, val label: String) {
    UNTRACKED(0, "No interval"),
    OK(1, "OK"),
    DUE_SOON(2, "Due soon"),
    OVERDUE(3, "Needs attention"),
}

data class PartStatus(
    val health: Health,
    val kmSince: Double,
    val daysSince: Long?,
    val kmProgress: Float?,
    val dayProgress: Float?,
    val openIssues: List<Issue>,
    val lastServiceDate: String?,
    val summary: String,
)

fun BikeData.odometerKm(): Double = bike.startOdometerKm + rides.sumOf { it.km }

fun BikeData.activeParts(): List<Part> = parts.filter { !it.retired }

fun BikeData.partForSlot(slot: String): Part? = parts.firstOrNull { it.slot == slot && !it.retired }

fun BikeData.kmOnPart(p: Part): Double = ((p.retiredOdoKm ?: odometerKm()) - p.installedOdoKm).coerceAtLeast(0.0)

/** Event types that restart a part's service interval. */
private val resettingTypes = setOf(EventType.SERVICE, EventType.INSPECT, EventType.REPAIR, EventType.INSTALL)

fun BikeData.statusOf(part: Part): PartStatus {
    val last = events
        .filter { it.partId == part.id && it.type in resettingTypes }
        .maxWithOrNull(compareBy({ it.date }, { it.odoKm }))
    val baseDate = last?.date ?: part.installedDate
    val baseOdo = last?.odoKm ?: part.installedOdoKm
    val kmSince = (odometerKm() - baseOdo).coerceAtLeast(0.0)
    val daysSince = Dates.daysSince(baseDate)

    val kmP = part.serviceIntervalKm?.takeIf { it > 0 }?.let { (kmSince / it).toFloat() }
    val dayP = part.serviceIntervalDays?.takeIf { it > 0 }?.let { d -> daysSince?.let { it.toFloat() / d } }
    val progress = listOfNotNull(kmP, dayP).maxOrNull()
    val open = issues.filter { it.partId == part.id && !it.resolved }

    var health = when {
        part.retired -> Health.UNTRACKED
        progress == null -> Health.UNTRACKED
        progress >= 1f -> Health.OVERDUE
        progress >= 0.8f -> Health.DUE_SOON
        else -> Health.OK
    }
    if (open.any { it.severity == Severity.HIGH }) health = Health.OVERDUE
    else if (open.isNotEmpty() && health.rank < Health.DUE_SOON.rank) health = Health.DUE_SOON

    val bits = mutableListOf<String>()
    part.serviceIntervalKm?.takeIf { it > 0 }?.let {
        val r = it - kmSince
        bits += if (r >= 0) "in ${r.km()}" else "${(-r).km()} over"
    }
    part.serviceIntervalDays?.takeIf { it > 0 }?.let { d ->
        if (daysSince == null) bits += "set install date"
        else {
            val r = d - daysSince
            bits += if (r >= 0) "in $r days" else "${-r} days over"
        }
    }
    var summary = when {
        part.retired -> "Retired"
        bits.isEmpty() -> "No service interval"
        progress != null && progress >= 1f -> "Service due · " + bits.joinToString(" · ")
        else -> "Service " + bits.joinToString(" or ")
    }
    if (open.isNotEmpty()) summary = "${open.size} open issue${if (open.size > 1) "s" else ""} · $summary"

    return PartStatus(health, kmSince, daysSince, kmP, dayP, open, baseDate, summary)
}
