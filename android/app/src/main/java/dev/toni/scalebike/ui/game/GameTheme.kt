package dev.toni.scalebike.ui.game

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.R

/** Colour tokens of the approved prototype (`design/prototype/template.html`, `:root`). Single dark theme. */
object G {
    val bg = Color(0xFF050608)
    val fade = Color(0xE0040507)            // rgba(4,5,7,.88)
    val line = Color(0x1FDCEBFF)            // rgba(220,235,255,.12)
    val fg = Color(0xFFF2F4F6)
    val muted = Color(0xFF8E98A4)
    val neon = Color(0xFFD2F500)            // the bike's neon yellow (SCOTT logo, stock grips)
    val neonDim = Color(0x2ED2F500)         // rgba(210,245,0,.18)
    val ink = Color(0xFF0A0B0D)             // text on neon
    val inkMuted = Color(0xB30A0B0D)        // rgba(10,11,13,.7)
    val ok = Color(0xFF3AD98B)
    val soon = Color(0xFFFFB020)
    val over = Color(0xFFFF4D4F)
    val none = Color(0xFF4A525C)
    val chip = Color(0xD10A0C0F)            // rgba(10,12,15,.82)
    val act = Color(0x0FFFFFFF)             // rgba(255,255,255,.06)
    val segOff = Color(0x17FFFFFF)          // rgba(255,255,255,.09)
}

/** Barlow Condensed: display (italic 800/900 for titles, upright 600/700 for small caps labels). */
val DisplayFont = FontFamily(
    Font(R.font.barlow_condensed_semi_bold, FontWeight.SemiBold),
    Font(R.font.barlow_condensed_bold, FontWeight.Bold),
    Font(R.font.barlow_condensed_bold_italic, FontWeight.Bold, FontStyle.Italic),
    Font(R.font.barlow_condensed_extra_bold_italic, FontWeight.ExtraBold, FontStyle.Italic),
    Font(R.font.barlow_condensed_black_italic, FontWeight.Black, FontStyle.Italic),
)

/** Barlow: body text. */
val BodyFont = FontFamily(
    Font(R.font.barlow_regular, FontWeight.Normal),
    Font(R.font.barlow_medium, FontWeight.Medium),
    Font(R.font.barlow_semi_bold, FontWeight.SemiBold),
)

/** Chakra Petch: numbers (odometer, score, stats). */
val NumFont = FontFamily(
    Font(R.font.chakra_petch_medium, FontWeight.Medium),
    Font(R.font.chakra_petch_semi_bold, FontWeight.SemiBold),
)

private val tight = LineHeightStyle(LineHeightStyle.Alignment.Center, LineHeightStyle.Trim.Both)

/** The prototype's `.it` class: condensed, italic, extra bold (uppercase is applied to the string). */
fun italicDisplay(size: TextUnit, color: Color = G.fg, weight: FontWeight = FontWeight.ExtraBold, spacing: TextUnit = 0.01.em) = TextStyle(
    fontFamily = DisplayFont, fontStyle = FontStyle.Italic, fontWeight = weight, fontSize = size, color = color,
    letterSpacing = spacing, lineHeight = size * 1.0f, lineHeightStyle = tight,
)

/** Small upright caps label (crumbs, prompts, "CONDITION"). */
fun capsLabel(size: TextUnit = 12.sp, color: Color = G.muted, weight: FontWeight = FontWeight.SemiBold, spacing: TextUnit = 0.22.em) = TextStyle(
    fontFamily = DisplayFont, fontWeight = weight, fontSize = size, color = color, letterSpacing = spacing,
    lineHeight = size * 1.15f, lineHeightStyle = tight,
)

fun bodyText(size: TextUnit = 13.sp, color: Color = G.fg, weight: FontWeight = FontWeight.Normal) = TextStyle(
    fontFamily = BodyFont, fontWeight = weight, fontSize = size, color = color, lineHeight = size * 1.3f,
)

fun numText(size: TextUnit, color: Color = G.fg, weight: FontWeight = FontWeight.SemiBold) = TextStyle(
    fontFamily = NumFont, fontWeight = weight, fontSize = size, color = color, letterSpacing = 0.02.em,
    lineHeight = size * 1.0f, lineHeightStyle = tight,
)
