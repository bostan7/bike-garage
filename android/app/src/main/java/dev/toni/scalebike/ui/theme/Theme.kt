package dev.toni.scalebike.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import dev.toni.scalebike.data.Health
import dev.toni.scalebike.data.Severity

val Orange = Color(0xFFFF6A13)

private val scheme = darkColorScheme(
    primary = Orange,
    onPrimary = Color(0xFF1A0A00),
    primaryContainer = Color(0xFF4A2410),
    onPrimaryContainer = Color(0xFFFFDBCB),
    secondary = Color(0xFFB8C4D0),
    secondaryContainer = Color(0xFF2B3138),
    onSecondaryContainer = Color(0xFFDCE3EA),
    background = Color(0xFF0E0F11),
    onBackground = Color(0xFFE6E7EA),
    surface = Color(0xFF0E0F11),
    onSurface = Color(0xFFE6E7EA),
    surfaceVariant = Color(0xFF24262B),
    onSurfaceVariant = Color(0xFF9EA3AB),
    surfaceContainerLowest = Color(0xFF0A0B0C),
    surfaceContainerLow = Color(0xFF141518),
    surfaceContainer = Color(0xFF17191C),
    surfaceContainerHigh = Color(0xFF1F2125),
    surfaceContainerHighest = Color(0xFF282A2F),
    outline = Color(0xFF3A3D43),
    outlineVariant = Color(0xFF2A2C31),
)

object StatusColors {
    val ok = Color(0xFF43C46B)
    val soon = Color(0xFFFFB020)
    val over = Color(0xFFF0473C)
    val none = Color(0xFF6E737B)
}

fun Health.color(): Color = when (this) {
    Health.OK -> StatusColors.ok
    Health.DUE_SOON -> StatusColors.soon
    Health.OVERDUE -> StatusColors.over
    Health.UNTRACKED -> StatusColors.none
}

fun Severity.color(): Color = when (this) {
    Severity.LOW -> StatusColors.none
    Severity.MEDIUM -> StatusColors.soon
    Severity.HIGH -> StatusColors.over
}

@Composable
fun ScaleBikeTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, content = content)
}
