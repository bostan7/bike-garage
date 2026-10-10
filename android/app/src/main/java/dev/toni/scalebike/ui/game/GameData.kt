package dev.toni.scalebike.ui.game

import dev.toni.scalebike.data.BikeData
import dev.toni.scalebike.data.Category
import dev.toni.scalebike.data.EventType
import dev.toni.scalebike.data.Health
import dev.toni.scalebike.data.Part
import dev.toni.scalebike.data.PartStatus
import dev.toni.scalebike.data.Severity
import dev.toni.scalebike.data.activeParts
import dev.toni.scalebike.data.km
import dev.toni.scalebike.data.money
import dev.toni.scalebike.data.statusOf
import dev.toni.scalebike.garage.GarageMode
import dev.toni.scalebike.garage.PartHealth
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

// Pure helpers for the game UI: they only read BikeData (the data layer stays the source of truth).

/** The PARTS areas in menu order. Labels come from [Category.label]. */
val GAME_AREAS = listOf(Category.WHEELS, Category.DRIVETRAIN, Category.BRAKES, Category.COCKPIT, Category.FRAME, Category.CONTACT)

val GarageMode.title: String
    get() = when (this) {
        GarageMode.SERVICE_LOG -> "Service log"
        GarageMode.GARAGE -> "Garage"
        GarageMode.PARTS -> "Parts"
        GarageMode.WORKSHOP -> "Workshop"
        GarageMode.BIKE -> "Bike"
    }

fun Health.toPartHealth(): PartHealth = when (this) {
    Health.OK -> PartHealth.OK
    Health.DUE_SOON -> PartHealth.SOON
    Health.OVERDUE -> PartHealth.OVER
    Health.UNTRACKED -> PartHealth.NONE
}

/** Everything the HUD needs, computed once per data change. */
data class GameSummary(
    val statusBySlot: Map<String, PartStatus>,
    val partBySlot: Map<String, Part>,
    val healthBySlot: Map<String, PartHealth>,
    val score: Int,
    val classLetter: String,
    val alerts: Int,
    val worstSlot: String?,
)

fun BikeData.gameSummary(): GameSummary {
    val parts = activeParts()
    val statuses = parts.associate { it.slot to statusOf(it) }
    val health = statuses.mapValues { it.value.health.toPartHealth() }
    val soon = health.values.count { it == PartHealth.SOON }
    val over = health.values.count { it == PartHealth.OVER }
    val issues = statuses.values.sumOf { it.openIssues.size }
    val score = (1000 - 40 * soon - 110 * over - 15 * issues).coerceAtLeast(0)
    val cls = when {
        score >= 900 -> "S"
        score >= 800 -> "A"
        score >= 700 -> "B"
        score >= 600 -> "C"
        else -> "D"
    }
    val worst = statuses.entries
        .filter { it.value.health == Health.DUE_SOON || it.value.health == Health.OVERDUE }
        .maxWithOrNull(compareBy({ it.value.health.rank }, { it.value.openIssues.size }, { wear(it.value) ?: 0f }))
        ?.key
    return GameSummary(statuses, parts.associateBy { it.slot }, health, score, cls, soon + over, worst)
}

/** Active parts of one PARTS area, in seed order. */
fun BikeData.partsIn(area: Category): List<Part> = activeParts().filter { it.category == area }

/** Wear since the last service: the larger of the km and day progress (null = no interval). */
fun wear(s: PartStatus): Float? = listOfNotNull(s.kmProgress, s.dayProgress).maxOrNull()

/** Card "Condition" 0..1 (prototype formula, minus 10 % per open issue); null when the part has no interval. */
fun condition(s: PartStatus): Float? {
    val w = wear(s) ?: return if (s.openIssues.isEmpty()) null else (1f - 0.1f * s.openIssues.size).coerceAtLeast(0f)
    return (1f - (w - 0.2f).coerceAtLeast(0f) * 0.9f - 0.1f * s.openIssues.size).coerceIn(0f, 1f)
}

fun healthWord(h: PartHealth): String = when (h) {
    PartHealth.OK -> "Good"
    PartHealth.SOON -> "Service soon"
    PartHealth.OVER -> "Needs attention"
    PartHealth.NONE -> "Not tracked"
}

// ---------------------------------------------------------------- service log (same entries as TimelineScreen)

enum class LogTone { OK, SOON, OVER, NONE, RIDE }

data class LogEntry(
    val key: String,
    val date: String,
    val title: String,
    val subtitle: String,
    val tone: LogTone,
    val partId: String?,
)

fun BikeData.logEntries(): List<LogEntry> {
    val partsById = parts.associateBy { it.id }
    return buildList {
        events.forEach { e ->
            val p = partsById[e.partId]
            add(
                LogEntry(
                    "e" + e.id, e.date, e.title,
                    listOfNotNull(p?.name ?: "Part", e.type.label, e.odoKm.km(), e.cost?.money(), e.doneBy.takeIf { it.isNotBlank() })
                        .joinToString(" · "),
                    if (e.type == EventType.REMOVED) LogTone.NONE else LogTone.OK, e.partId,
                ),
            )
        }
        issues.forEach { i ->
            val p = partsById[i.partId]
            add(
                LogEntry(
                    "i" + i.id, i.date, i.title,
                    "${p?.name ?: "Part"} · Issue · ${i.severity.label}" + if (i.resolved) " · resolved" else " · open",
                    when {
                        i.resolved -> LogTone.NONE
                        i.severity == Severity.HIGH -> LogTone.OVER
                        else -> LogTone.SOON
                    },
                    i.partId,
                ),
            )
            if (i.resolved && i.resolvedDate != null) {
                add(
                    LogEntry(
                        "r" + i.id, i.resolvedDate, "Fixed: ${i.title}",
                        "${p?.name ?: "Part"}" + if (i.resolution.isNotBlank()) " · ${i.resolution}" else "",
                        LogTone.OK, i.partId,
                    ),
                )
            }
        }
        rides.forEach { r -> add(LogEntry("d" + r.id, r.date, "Ride · ${r.km.km()}", r.note, LogTone.RIDE, null)) }
        bike.purchaseDate?.let { add(LogEntry("purchase", it, "Got the bike", bike.name, LogTone.RIDE, null)) }
    }.sortedByDescending { it.date }
}

private val shortDate = DateTimeFormatter.ofPattern("d MMM", Locale.UK)
private val shortDateYear = DateTimeFormatter.ofPattern("d MMM yy", Locale.UK)

/** "4 Oct" this year, "4 Oct 25" otherwise. */
fun shortDate(iso: String?): String {
    val d = iso?.let { runCatching { LocalDate.parse(it) }.getOrNull() } ?: return "—"
    return d.format(if (d.year == LocalDate.now().year) shortDate else shortDateYear).uppercase(Locale.UK)
}

/** "1 850" with a thin space, for the odometer. */
fun groupedKm(km: Double): String = String.format(Locale.UK, "%,d", Math.round(km)).replace(',', ' ')

// ---------------------------------------------------------------- workshop (same content as ToolsScreen)

/** Pre-ride check: short game label + the full instruction. */
val PRE_RIDE_CHECK = listOf(
    "Tyre pressure" to "Checked with a gauge",
    "Brakes firm" to "Both levers firm, bike stops when pushed",
    "Wheels tight" to "QR levers closed tight, no wobble",
    "No headset knock" to "Rock the bike with the front brake on",
    "Chain lubed" to "Clean, lubed, shifts through all gears",
    "Bolts tight" to "Stem, bars and seatpost",
    "Lockout open" to "Fork lockout open, rebound set",
    "Kit packed" to "Pump, tube/plug, multitool, quick link, water",
)

val TORQUE = listOf(
    "Stem steerer & bar clamp bolts" to "5–6 Nm",
    "Headset top cap" to "Snug only",
    "Seatpost clamp" to "5–6 Nm",
    "Saddle rail clamp" to "8–12 Nm",
    "Brake caliper mount bolts" to "6–8 Nm",
    "Brake lever clamp" to "4–6 Nm",
    "Shifter clamp" to "~3 Nm",
    "Rear derailleur mount" to "8–10 Nm",
    "Derailleur cable fixing bolt" to "6–7 Nm",
    "Centre Lock rotor lockring" to "40–50 Nm",
    "Cassette lockring" to "30–50 Nm",
    "Crank left-arm pinch bolts" to "12–14 Nm",
    "Crank preload cap" to "0.7–1.5 Nm",
    "Pedals" to "35–55 Nm",
)

/** Front / rear tyre pressure in psi (formula from ToolsScreen; rear is +2 psi). */
fun tyrePressurePsi(weightKg: Float, tubeless: Boolean): Pair<Float, Float> {
    val front = (8 + 0.24f * weightKg - if (tubeless) 3f else 0f).coerceIn(16f, 40f)
    return front to front + 2f
}
