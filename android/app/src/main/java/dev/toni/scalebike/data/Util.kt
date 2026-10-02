package dev.toni.scalebike.data

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.Locale
import java.util.UUID

object Dates {
    private val display = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.UK)
    private val month = DateTimeFormatter.ofPattern("MMMM yyyy", Locale.UK)

    fun today(): String = LocalDate.now().toString()
    fun parse(s: String?): LocalDate? = s?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
    fun format(s: String?): String = parse(s)?.format(display) ?: "—"
    fun formatMonth(s: String?): String = parse(s)?.format(month) ?: "Unknown date"
    fun daysSince(s: String?): Long? = parse(s)?.let { ChronoUnit.DAYS.between(it, LocalDate.now()) }

    /** "2 y 3 mo", "5 mo", "12 days" */
    fun age(s: String?): String {
        val d = parse(s) ?: return "—"
        val now = LocalDate.now()
        val months = ChronoUnit.MONTHS.between(d, now)
        return when {
            months >= 12 -> "${months / 12} y ${months % 12} mo"
            months >= 1 -> "$months mo"
            else -> "${ChronoUnit.DAYS.between(d, now)} days"
        }
    }
}

fun Double.km(): String =
    if (this >= 100) String.format(Locale.UK, "%,.0f km", this) else String.format(Locale.UK, "%.1f km", this)

fun Double.money(): String = String.format(Locale.UK, "€%,.2f", this)

fun String.toNum(): Double? = replace(',', '.').trim().toDoubleOrNull()

fun Double.plain(): String = if (this % 1.0 == 0.0) toLong().toString() else toString()

fun newId(): String = UUID.randomUUID().toString()
