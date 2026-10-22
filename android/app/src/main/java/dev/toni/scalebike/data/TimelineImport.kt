package dev.toni.scalebike.data

import android.util.JsonReader
import android.util.JsonToken
import java.io.InputStream
import java.io.InputStreamReader
import java.time.Duration
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.temporal.ChronoUnit
import java.util.Locale
import java.util.TreeMap

/**
 * Ride km from a Google Maps Timeline export (phone Settings → Location → Location services → Timeline →
 * Export Timeline data → `Timeline.json`). Only bike trips are used, summed per local day; only the day and the
 * km are kept, no places or coordinates. The file is streamed (it can be 50+ MB, mostly `rawSignals`).
 */
object TimelineImport {
    /** Ride ids written by the import; a re-import replaces these days and never touches hand-logged rides. */
    const val ID_PREFIX = "timeline-"
    /** Google's confidence that the trip was by bike. */
    const val MIN_PROBABILITY = 0.5
    /** Faster than this is a car or bus labelled as a bike by mistake. */
    const val MAX_KMH = 35.0

    data class Day(val date: String, val km: Double, val trips: Int)

    data class Parsed(val days: List<Day>, val trips: Int, val skipped: Int)

    /** Thrown when the file is not an on-device Timeline export (no `semanticSegments`). */
    class NotTimeline : Exception("Not a Timeline export")

    fun parse(input: InputStream): Parsed {
        val byDay = TreeMap<String, Pair<Double, Int>>()
        var trips = 0
        var skipped = 0
        var found = false
        JsonReader(InputStreamReader(input.buffered(1 shl 16), Charsets.UTF_8)).use { r ->
            if (r.peek() != JsonToken.BEGIN_OBJECT) throw NotTimeline()
            r.beginObject()
            while (r.hasNext()) {
                if (r.nextName() != "semanticSegments") {
                    r.skipValue()
                    continue
                }
                found = true
                r.beginArray()
                while (r.hasNext()) {
                    val s = readSegment(r) ?: continue
                    val day = s.dayIfRide()
                    if (day == null) {
                        skipped++
                        continue
                    }
                    trips++
                    val (km, n) = byDay[day] ?: (0.0 to 0)
                    byDay[day] = (km + s.meters!! / 1000.0) to (n + 1)
                }
                r.endArray()
            }
            r.endObject()
        }
        if (!found) throw NotTimeline()
        return Parsed(byDay.map { (d, v) -> Day(d, v.first, v.second) }, trips, skipped)
    }

    /** One timeline segment; only bike activities are returned, visits and paths are skipped. */
    private class Segment(val start: String?, val end: String?, val probability: Double, val meters: Double?) {
        /** Local day of a believable bike trip, or null to skip it. */
        fun dayIfRide(): String? {
            if (probability < MIN_PROBABILITY || meters == null || meters <= 0.0 || start == null || end == null) return null
            val s = runCatching { OffsetDateTime.parse(start) }.getOrNull() ?: return null
            val e = runCatching { OffsetDateTime.parse(end) }.getOrNull() ?: return null
            val hours = Duration.between(s, e).seconds / 3600.0
            if (hours <= 0.0 || meters / 1000.0 / hours > MAX_KMH) return null
            return s.toLocalDate().toString()
        }
    }

    private fun readSegment(r: JsonReader): Segment? {
        var start: String? = null
        var end: String? = null
        var cycling = false
        var probability = 0.0
        var meters: Double? = null
        r.beginObject()
        while (r.hasNext()) {
            when (r.nextName()) {
                "startTime" -> start = r.nextString()
                "endTime" -> end = r.nextString()
                "activity" -> {
                    r.beginObject()
                    while (r.hasNext()) {
                        when (r.nextName()) {
                            "distanceMeters" -> meters = readNumber(r)
                            "topCandidate" -> {
                                r.beginObject()
                                while (r.hasNext()) {
                                    when (r.nextName()) {
                                        "type" -> cycling = r.nextString().uppercase(Locale.ROOT) == "CYCLING"
                                        "probability" -> probability = readNumber(r) ?: 0.0
                                        else -> r.skipValue()
                                    }
                                }
                                r.endObject()
                            }
                            else -> r.skipValue()
                        }
                    }
                    r.endObject()
                }
                else -> r.skipValue()
            }
        }
        r.endObject()
        return if (cycling) Segment(start, end, probability, meters) else null
    }

    /** Numbers may come as JSON numbers or as strings. */
    private fun readNumber(r: JsonReader): Double? = when (r.peek()) {
        JsonToken.NUMBER -> r.nextDouble()
        JsonToken.STRING -> r.nextString().toDoubleOrNull()
        else -> {
            r.skipValue()
            null
        }
    }
}

/** What an import changed, for the banner; [estimateKm] = km estimated for the time before Timeline. */
data class TimelineMerge(val newDays: Int, val updatedDays: Int, val km: Double, val estimateKm: Double, val kmPerDay: Double)

/** Ride ids of the estimated months before Timeline started recording (`estimate-yyyy-MM`). */
const val ESTIMATE_PREFIX = "estimate-"

/**
 * Puts the imported days into the rides: one ride per day (`timeline-yyyy-MM-dd`); a day imported before is
 * replaced by the new total, hand-logged rides stay as they are. Timeline only records from when it was switched
 * on (Toni's: 22 Jun 2026), so the time from the purchase date until then is filled with one estimated ride per
 * month at the Timeline average km/day; the estimate is recomputed on every import (Toni, 2026-10-18).
 */
fun BikeRepository.applyTimeline(days: List<TimelineImport.Day>): TimelineMerge {
    val before = data.value.rides.filter { it.id.startsWith(TimelineImport.ID_PREFIX) }.associateBy { it.id }
    val rides = days.map { d ->
        Ride(
            id = TimelineImport.ID_PREFIX + d.date,
            date = d.date,
            km = Math.round(d.km * 10) / 10.0,
            note = "Timeline · ${d.trips} trip${if (d.trips == 1) "" else "s"}",
        )
    }
    val ids = rides.map { it.id }.toSet()
    var estimate = Estimate(emptyList(), 0.0)
    update { d ->
        val merged = d.copy(rides = d.rides.filterNot { it.id in ids } + rides, lastTimelineImport = Dates.today())
        estimate = merged.estimate()
        merged.copy(rides = merged.rides.filterNot { it.id.startsWith(ESTIMATE_PREFIX) } + estimate.rides)
    }
    val newDays = rides.count { it.id !in before }
    val updated = rides.count { r -> before[r.id]?.let { it.km != r.km } == true }
    val addedKm = rides.sumOf { it.km } - rides.sumOf { before[it.id]?.km ?: 0.0 }
    return TimelineMerge(newDays, updated, addedKm, estimate.rides.sumOf { it.km }, estimate.kmPerDay)
}

/** The estimate rides for this data: none once the odometer was corrected by hand ([BikeData.estimateBeforeTimeline]). */
private fun BikeData.estimate(): Estimate =
    if (!estimateBeforeTimeline) Estimate(emptyList(), 0.0)
    else estimateBeforeTimeline(rides.filter { it.id.startsWith(TimelineImport.ID_PREFIX) }, bike.purchaseDate)

/** Rebuilds the estimate rides after the purchase date or the estimate setting changed. */
fun BikeData.withFreshEstimate(): BikeData =
    copy(rides = rides.filterNot { it.id.startsWith(ESTIMATE_PREFIX) } + estimate().rides)

private class Estimate(val rides: List<Ride>, val kmPerDay: Double)

/**
 * One ride per calendar month from [purchaseDate] up to the day before the first Timeline day, each worth
 * (Timeline km / Timeline days) × the days of that month in the gap. Empty without a purchase date or Timeline rides.
 */
private fun estimateBeforeTimeline(timeline: List<Ride>, purchaseDate: String?): Estimate {
    val start = purchaseDate?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
    if (timeline.isEmpty() || start == null) return Estimate(emptyList(), 0.0)
    val dates = timeline.map { LocalDate.parse(it.date) }
    val first = dates.min()
    val perDay = timeline.sumOf { it.km } / (ChronoUnit.DAYS.between(first, dates.max()) + 1)
    val out = mutableListOf<Ride>()
    var day: LocalDate = start
    while (day.isBefore(first)) {
        val monthEnd = day.withDayOfMonth(day.lengthOfMonth())
        val end = if (monthEnd.isBefore(first)) monthEnd else first.minusDays(1)
        val n = ChronoUnit.DAYS.between(day, end) + 1
        out += Ride(
            id = ESTIMATE_PREFIX + day.toString().substring(0, 7),
            date = end.toString(),
            km = Math.round(perDay * n * 10) / 10.0,
            note = "Estimate · ${String.format(Locale.UK, "%.1f", perDay)} km/day × $n days (before Timeline)",
        )
        day = end.plusDays(1)
    }
    return Estimate(out, perDay)
}
