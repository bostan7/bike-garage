package dev.toni.scalebike.ui.game

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.garage.GarageMode
import kotlinx.coroutines.delay

// ---------------------------------------------------------------- top left: nameplate + odometer

@Composable
fun Nameplate(sub: String, odoKm: Double, showOdo: Boolean, modifier: Modifier = Modifier) {
    val odoAlpha by animateFloatAsState(if (showOdo) 1f else 0f, tween(300), label = "odo")
    Column(modifier) {
        Text("SCOTT", style = capsLabel(13.sp, G.neon, FontWeight.Bold, 0.4.em))
        Text("SCALE 980", style = italicDisplay(36.sp).copy(lineHeight = 32.sp))
        Text(sub.uppercase(), style = capsLabel(12.sp, G.muted, FontWeight.SemiBold, 0.2.em), modifier = Modifier.padding(top = 3.dp).graphicsLayer { alpha = odoAlpha })
        Text(
            buildAnnotatedString {
                append("ODO ")
                withStyle(SpanStyle(fontSize = 20.sp, color = G.fg, fontWeight = FontWeight.SemiBold)) { append(groupedKm(odoKm)) }
                append(" KM")
            },
            style = numText(12.sp, G.muted, FontWeight.Medium).copy(letterSpacing = 0.08.em, lineHeight = 22.sp),
            modifier = Modifier.padding(top = 6.dp).graphicsLayer { alpha = odoAlpha },
        )
    }
}

// ---------------------------------------------------------------- top right: alerts, status, sound, condition badge

@Composable
fun TopRightHud(
    alerts: Int,
    statusOn: Boolean,
    soundOn: Boolean,
    classLetter: String,
    score: Int,
    onAlerts: () -> Unit,
    onStatus: () -> Unit,
    onSound: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
        ChipButton(
            text = if (alerts > 0) "$alerts ALERT${if (alerts == 1) "" else "S"}" else "ALL GOOD",
            pressed = false,
            onClick = onAlerts,
            color = if (alerts > 0) G.soon else G.ok,
            leading = if (alerts > 0) ({ StatusDot(G.over, glow = true, size = 8.dp) }) else null,
        )
        ChipButton("STATUS", statusOn, onStatus, toggle = true)
        ChipButton("SOUND", soundOn, onSound, toggle = true)
        ConditionBadge(classLetter, score)
    }
}

@Composable
fun ConditionBadge(classLetter: String, score: Int) {
    val count = remember { Animatable(0f) }
    LaunchedEffect(score) { count.animateTo(score.toFloat(), tween(900, easing = easeOutQuint)) }
    val shown = count.value.toInt()
    Row(
        Modifier.height(44.dp).clip(SlantShape(10.dp)).background(G.chip),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.fillMaxHeight().background(G.neon).padding(start = 16.dp, end = 14.dp), contentAlignment = Alignment.Center) {
            Text(classLetter, style = italicDisplay(30.sp, G.ink, FontWeight.Black))
        }
        Column(Modifier.padding(start = 10.dp, end = 16.dp, top = 2.dp)) {
            Text(shown.toString(), style = numText(22.sp))
            Text("CONDITION", style = capsLabel(10.sp, G.muted, FontWeight.SemiBold, 0.24.em))
        }
    }
}

// ---------------------------------------------------------------- bottom: mode tabs + control prompts

@Composable
fun ModeBar(current: GarageMode, onSelect: (GarageMode) -> Unit, onPrev: () -> Unit, onNext: () -> Unit, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        ArrowButton("‹", "Previous mode", onPrev)
        Row(horizontalArrangement = Arrangement.spacedBy(18.dp), verticalAlignment = Alignment.CenterVertically) {
            GarageMode.entries.forEach { m -> ModeTab(m.title, m == current) { onSelect(m) } }
        }
        ArrowButton("›", "Next mode", onNext)
    }
}

@Composable
private fun ArrowButton(glyph: String, description: String, onClick: () -> Unit) {
    Box(
        Modifier.size(44.dp).gameClick(onClick = onClick).semantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) { Text(glyph, style = italicDisplay(26.sp, G.muted)) }
}

@Composable
private fun ModeTab(title: String, selected: Boolean, onClick: () -> Unit) {
    val k by animateFloatAsState(if (selected) 1f else 0f, tween(300, easing = easeOutQuint), label = "tab")
    val color = androidx.compose.ui.graphics.lerp(G.muted, G.fg, k)
    Box(
        Modifier
            .heightIn(min = 44.dp)
            .gameClick(role = Role.Tab, onClick = onClick)
            .graphicsLayer { scaleX = 1f + 0.12f * k; scaleY = 1f + 0.12f * k }
            .drawBehind {
                if (k > 0.01f) {
                    val h = 3.dp.toPx()
                    val ext = 4.dp.toPx()
                    val cx = size.width / 2
                    val half = (size.width / 2 + ext) * k
                    val y = size.height - 6.dp.toPx()
                    val p = skewedPath(cx - half, cx + half, y, y + h, 20f)
                    drawGlow(p, G.neon.copy(alpha = 0.9f * k), 10.dp.toPx())
                    drawPath(p, G.neon)
                }
            }
            .padding(start = 2.dp, end = 2.dp, top = 4.dp, bottom = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(title.uppercase(), style = italicDisplay(17.sp, color), maxLines = 1, softWrap = false)
    }
}

@Composable
fun ControlPrompts(bottomInset: Dp, modifier: Modifier = Modifier) {
    val items = listOf("◀▶" to "EDGE SWIPE · MODE", "⟳" to "DRAG · ROTATE", "●" to "TAP · SELECT", "●●" to "DOUBLE TAP · RESET", "▬" to "HOLD · CONFIRM")
    Row(
        modifier
            .fillMaxWidth()
            .background(Brush.verticalGradient(listOf(Color.Transparent, Color(0xA6000000))))
            .padding(start = 16.dp, end = 16.dp, top = 4.dp, bottom = 5.dp + bottomInset),
        horizontalArrangement = Arrangement.spacedBy(22.dp, Alignment.CenterHorizontally),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        items.forEach { (key, what) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.heightIn(min = 16.dp).widthIn(min = 18.dp)
                        .border(1.dp, G.muted, RoundedCornerShape(3.dp)).padding(horizontal = 4.dp),
                    contentAlignment = Alignment.Center,
                ) { Text(key, style = capsLabel(10.sp, G.fg, FontWeight.SemiBold, 0.em)) }
                Text(what, style = capsLabel(11.sp, G.muted, FontWeight.SemiBold, 0.14.em), modifier = Modifier.padding(start = 6.dp))
            }
        }
    }
}

// ---------------------------------------------------------------- edge swipe zones

@Composable
fun EdgeGlow(left: Boolean, flash: Boolean, modifier: Modifier = Modifier) {
    val a by animateFloatAsState(if (flash) 1f else 0.3f, tween(300), label = "edge")
    Box(
        modifier
            .width(20.dp)
            .graphicsLayer { alpha = a }
            .background(Brush.horizontalGradient(if (left) listOf(G.neonDim, Color.Transparent) else listOf(Color.Transparent, G.neonDim))),
        contentAlignment = Alignment.Center,
    ) { Text(if (left) "‹" else "›", style = italicDisplay(18.sp, G.neon)) }
}

// ---------------------------------------------------------------- speed-stripe wipe on mode change

private val wipeEase = CubicBezierEasing(0.3f, 0.7f, 0.2f, 1f)

/** Three skewed stripes (neon 18 %, white 5 %, neon 2 % of the width) race across the screen; `dir < 0` = right to left. */
@Composable
fun SpeedWipe(trigger: Int, dir: Int, enabled: Boolean, modifier: Modifier = Modifier) {
    val t = remember { Animatable(1f) }
    LaunchedEffect(trigger) {
        if (trigger == 0 || !enabled) return@LaunchedEffect
        t.snapTo(0f)
        t.animateTo(1f, tween(500, easing = LinearEasing))
    }
    if (t.value >= 1f) return
    Canvas(modifier.fillMaxSize()) {
        val w = size.width
        val stripes = listOf(Triple(0.18f, G.neon, 0f), Triple(0.05f, Color.White, 40f), Triple(0.02f, G.neon, 80f))
        stripes.forEach { (frac, color, delayMs) ->
            val k = ((t.value * 500f - delayMs) / 420f).coerceIn(0f, 1f)
            if (k <= 0f || k >= 1f) return@forEach
            val e = wipeEase.transform(k)
            val from = if (dir >= 0) -0.30f * w else 1.15f * w
            val to = if (dir >= 0) 1.15f * w else -0.30f * w
            val x = from + (to - from) * e
            val top = -0.2f * size.height
            val bottom = 1.2f * size.height
            drawPath(skewedPath(x, x + frac * w, top, bottom, 24f), color.copy(alpha = 0.55f * (1f - e)))
        }
    }
}

// ---------------------------------------------------------------- NFS banner

data class BannerMsg(val text: String, val sub: String, val id: Long = System.nanoTime())

/** Neon slab that slides in from the left at 34 % height and leaves after 1.9 s. */
@Composable
fun Banner(msg: BannerMsg?, leftInset: Dp, reduced: Boolean, modifier: Modifier = Modifier) {
    var visible by remember { mutableStateOf(false) }
    var shown by remember { mutableStateOf<BannerMsg?>(null) }
    LaunchedEffect(msg?.id) {
        if (msg == null) return@LaunchedEffect
        shown = msg
        visible = true
        delay(1900)
        visible = false
    }
    val k by animateFloatAsState(if (visible) 1f else 0f, if (reduced) tween(0) else tween(350, easing = easeOutQuint), label = "banner")
    val m = shown ?: return
    if (k <= 0.001f) return
    BoxWithConstraints(modifier.fillMaxSize()) {
        Box(
            Modifier
                .padding(top = maxHeight * 0.34f)
                .graphicsLayer { translationX = -(1f - k) * 1.05f * size.width }
                .clip(CutRightShape(28.dp))
                .background(G.neon)
                .padding(start = 22.dp + leftInset, end = 46.dp, top = 10.dp, bottom = 10.dp),
        ) {
            Column {
                Text(m.sub.uppercase(), style = capsLabel(12.sp, G.ink.copy(alpha = 0.7f), FontWeight.Bold, 0.22.em))
                Text(m.text.uppercase(), style = italicDisplay(22.sp, G.ink, spacing = 0.02.em))
            }
        }
    }
}

// ---------------------------------------------------------------- intro title

@Composable
fun IntroTitle(visible: Boolean, loading: Boolean, modifier: Modifier = Modifier) {
    val a by animateFloatAsState(if (visible) 1f else 0f, tween(800), label = "intro")
    if (a <= 0.001f) return
    BoxWithConstraints(modifier.fillMaxSize().graphicsLayer { alpha = a }, contentAlignment = Alignment.Center) {
        val big = (maxWidth.value * 0.09f).coerceIn(46f, 86f).sp
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("SCOTT", style = capsLabel(14.sp, G.neon, FontWeight.Bold, 0.7.em))
            Text("SCALE 980", style = italicDisplay(big).copy(lineHeight = big * 0.95f))
            Text(
                if (loading) "OPENING THE GARAGE…" else "TAP TO SKIP",
                style = capsLabel(12.sp, G.muted, FontWeight.SemiBold, 0.32.em),
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}
