package dev.toni.scalebike.ui.game

import android.graphics.BlurMaskFilter
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameMillis
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.asAndroidPath
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.garage.PartHealth
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.tan

// ---------------------------------------------------------------- shapes

/** CSS `clip-path: polygon(c 0, 100% 0, calc(100% - c) 100%, 0 100%)`: the slanted chip / button / badge shape. */
class SlantShape(private val cut: Dp) : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val c = with(density) { cut.toPx() }
        return Outline.Generic(
            Path().apply {
                moveTo(c, 0f); lineTo(size.width, 0f); lineTo(size.width - c, size.height); lineTo(0f, size.height); close()
            },
        )
    }
}

/** Banner slab: straight on the left (it slides in from the screen edge), slanted on the right. */
class CutRightShape(private val cut: Dp) : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val c = with(density) { cut.toPx() }
        return Outline.Generic(
            Path().apply { moveTo(0f, 0f); lineTo(size.width, 0f); lineTo(size.width - c, size.height); lineTo(0f, size.height); close() },
        )
    }
}

/** Parallelogram like CSS `skewX(-deg)` around the vertical centre, spanning x0..x1. */
fun skewedPath(x0: Float, x1: Float, top: Float, bottom: Float, deg: Float): Path {
    val s = tan(Math.toRadians(deg.toDouble())).toFloat() * (bottom - top) / 2f
    return Path().apply { moveTo(x0 + s, top); lineTo(x1 + s, top); lineTo(x1 - s, bottom); lineTo(x0 - s, bottom); close() }
}

/** Soft neon glow behind a shape (blur mask on the framework paint; works on the hardware canvas since API 28). */
fun DrawScope.drawGlow(path: Path, color: Color, blurPx: Float) {
    drawIntoCanvas { canvas ->
        val p = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
            this.color = color.toArgb()
            maskFilter = BlurMaskFilter(blurPx.coerceAtLeast(0.5f), BlurMaskFilter.Blur.NORMAL)
        }
        canvas.nativeCanvas.drawPath(path.asAndroidPath(), p)
    }
}

fun DrawScope.drawGlowCircle(center: Offset, radius: Float, color: Color, blurPx: Float) {
    drawIntoCanvas { canvas ->
        val p = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
            this.color = color.toArgb()
            maskFilter = BlurMaskFilter(blurPx, BlurMaskFilter.Blur.NORMAL)
        }
        canvas.nativeCanvas.drawCircle(center.x, center.y, radius, p)
    }
}

val easeOutQuint = CubicBezierEasing(0.2f, 0.8f, 0.2f, 1f)   // prototype: cubic-bezier(.2,.8,.2,1)

/** Click without the Material ripple (game UI). */
fun Modifier.gameClick(enabled: Boolean = true, role: Role = Role.Button, onClick: () -> Unit): Modifier = this.then(
    Modifier.clickable(
        interactionSource = null, indication = null, enabled = enabled, role = role, onClick = onClick,
    ),
)

/** Takes all touches on an area so they don't fall through to the 3D garage below (panels). */
fun Modifier.blockTouches(): Modifier = pointerInput(Unit) {
    awaitPointerEventScope { while (true) awaitPointerEvent() }
}

fun healthColor(h: PartHealth): Color = when (h) {
    PartHealth.OK -> G.ok
    PartHealth.SOON -> G.soon
    PartHealth.OVER -> G.over
    PartHealth.NONE -> G.none
}

// ---------------------------------------------------------------- small pieces

/** Status dot; amber and red ones glow. */
@Composable
fun StatusDot(color: Color, glow: Boolean, size: Dp = 9.dp, modifier: Modifier = Modifier) {
    Canvas(modifier.size(size)) {
        val r = this.size.minDimension / 2
        if (glow) drawGlowCircle(center, r * 1.3f, color.copy(alpha = 0.8f), 8.dp.toPx())
        drawCircle(color, r)
    }
}

@Composable
fun HealthDot(h: PartHealth, size: Dp = 9.dp, modifier: Modifier = Modifier) =
    StatusDot(healthColor(h), h == PartHealth.SOON || h == PartHealth.OVER, size, modifier)

/** 20-block skewed stat bar (prototype `.segs`). */
@Composable
fun SegBar(value: Float, color: Color, modifier: Modifier = Modifier) {
    val target = (value.coerceIn(0f, 1f) * 20f)
    val n by animateFloatAsState(target, tween(450, easing = easeOutQuint), label = "segs")
    Canvas(modifier.fillMaxWidth().height(9.dp)) {
        val gap = 2.dp.toPx()
        val w = (size.width - gap * 19) / 20
        val lit = Math.round(n)
        for (i in 0 until 20) {
            val x = i * (w + gap)
            drawPath(skewedPath(x, x + w, 0f, size.height, 20f), if (i < lit) color else G.segOff)
        }
    }
}

/** Stat row: italic caps label, number on the right, segmented bar below. */
@Composable
fun StatRow(label: String, value: String, fraction: Float, color: Color) {
    Column(Modifier.fillMaxWidth().padding(top = 6.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(label.uppercase(), style = italicDisplay(13.sp, weight = FontWeight.Bold, spacing = 0.08.em), modifier = Modifier.weight(1f))
            Text(value, style = numText(13.sp))
        }
        SegBar(fraction, color)
    }
}

/** Slanted HUD chip (ALERTS / STATUS / SOUND). */
@Composable
fun ChipButton(
    text: String,
    pressed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    color: Color = G.fg,
    toggle: Boolean = false,
    leading: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier
            .heightIn(min = 44.dp)
            .clip(SlantShape(8.dp))
            .background(if (pressed) G.neon else G.chip)
            .gameClick(onClick = onClick)
            .semantics { if (toggle) stateDescription = if (pressed) "On" else "Off" }
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        leading?.invoke()
        Text(text.uppercase(), style = italicDisplay(14.sp, if (pressed) G.ink else color, FontWeight.Bold, 0.08.em))
    }
}

/**
 * NFS list item (prototype `.item`): index number, big italic title, small subtitle, something on the right.
 * The current item gets a neon slab that slides in from the left (skewX -14°).
 */
@Composable
fun MenuItem(
    index: Int,
    title: String,
    subtitle: String?,
    current: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    trailing: (@Composable RowScope.() -> Unit)? = null,
) {
    val slab by animateFloatAsState(if (current) 1f else 0f, tween(250, easing = easeOutQuint), label = "slab")
    Row(
        modifier
            .fillMaxWidth()
            .heightIn(min = 48.dp)
            .drawBehind {
                if (slab > 0.001f) drawPath(skewedPath(0f, size.width * slab, 0f, size.height, 14f), G.neon)
            }
            .gameClick(onClick = onClick)
            .padding(start = 6.dp, end = 10.dp, top = 7.dp, bottom = 7.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(index.toString().padStart(2, '0'), style = numText(12.sp, if (current) G.inkMuted else G.muted, FontWeight.Medium), modifier = Modifier.width(28.dp))
        Spacer(Modifier.width(8.dp))
        Column(Modifier.weight(1f)) {
            Text(title.uppercase(), style = italicDisplay(20.sp, if (current) G.ink else G.fg), maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (!subtitle.isNullOrBlank()) {
                Text(subtitle, style = bodyText(12.sp, if (current) G.inkMuted else G.muted), maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 2.dp))
            }
        }
        if (trailing != null) {
            Spacer(Modifier.width(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.CenterVertically, content = trailing)
        }
    }
}

/** Panel title (h2 with the skewed neon bar in front) + crumb, optional "‹ back" link. */
@Composable
fun PanelHeader(title: String, crumb: String, onBack: (() -> Unit)? = null, backLabel: String = "‹ ALL AREAS") {
    Column(Modifier.fillMaxWidth().padding(top = 4.dp, end = 30.dp, bottom = 8.dp)) {
        if (onBack != null) {
            Box(Modifier.heightIn(min = 36.dp).gameClick(onClick = onBack), contentAlignment = Alignment.CenterStart) {
                Text(backLabel, style = capsLabel(12.sp, G.muted, FontWeight.Bold, 0.16.em))
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Canvas(Modifier.width(18.dp).height(24.dp)) {
                drawPath(skewedPath(0f, 8.dp.toPx(), 1.dp.toPx(), size.height - 1.dp.toPx(), 20f), G.neon)
            }
            Text(title.uppercase(), style = italicDisplay(30.sp).copy(lineHeight = 28.sp), maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        Text(crumb.uppercase(), style = capsLabel(12.sp), modifier = Modifier.padding(top = 2.dp))
    }
}

/** Small muted note in lists. */
@Composable
fun ListNote(text: String, modifier: Modifier = Modifier) {
    Text(text, style = bodyText(12.sp, G.muted), modifier = modifier.padding(horizontal = 6.dp, vertical = 6.dp))
}

/** Key / value row (prototype `.kv`). */
@Composable
fun KeyValue(key: String, value: String, valueStyle: androidx.compose.ui.text.TextStyle = bodyText(13.sp)) {
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(key, style = bodyText(13.sp, G.muted), modifier = Modifier.width(92.dp))
        Text(value, style = valueStyle, modifier = Modifier.weight(1f))
    }
}

// ---------------------------------------------------------------- action buttons

@Composable
private fun ActLabel(label: String, hint: String?, primary: Boolean) {
    Column {
        Text(label.uppercase(), style = italicDisplay(16.sp, if (primary) G.neon else G.fg, spacing = 0.04.em), maxLines = 1, overflow = TextOverflow.Ellipsis)
        if (hint != null) Text(hint, style = bodyText(12.sp, G.muted), maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

/** Slanted action button, plain tap. */
@Composable
fun ActButton(
    label: String,
    hint: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    primary: Boolean = false,
) {
    Box(
        modifier
            .heightIn(min = 44.dp)
            .clip(SlantShape(8.dp))
            .background(if (primary) G.neonDim else G.act)
            .gameClick(onClick = onClick)
            .padding(start = 16.dp, end = 14.dp, top = 6.dp, bottom = 6.dp),
        contentAlignment = Alignment.CenterStart,
    ) { ActLabel(label, hint, primary) }
}

/**
 * Hold-to-confirm button (prototype `[data-hold]`): pressing fills it with neon over 800 ms with a rising tone;
 * letting go early cancels. Timed on frame clock time, so it still needs a real hold with "Remove animations" on.
 */
@Composable
fun HoldButton(
    label: String,
    fx: GameFx,
    onConfirm: () -> Unit,
    modifier: Modifier = Modifier,
    hint: String? = "Hold to confirm",
    primary: Boolean = false,
    trailing: (@Composable () -> Unit)? = null,
) {
    var fill by remember { mutableFloatStateOf(0f) }
    val scope = rememberCoroutineScope()
    val confirm by rememberUpdatedState(onConfirm)
    Row(
        modifier
            .heightIn(min = 44.dp)
            .clip(SlantShape(8.dp))
            .background(if (primary) G.neonDim else G.act),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .weight(1f)
                .heightIn(min = 44.dp)
                .drawBehind { if (fill > 0f) drawRect(G.neon.copy(alpha = 0.35f), size = Size(size.width * fill, size.height)) }
                .semantics(mergeDescendants = true) {
                    role = Role.Button
                    onClick(label = "Confirm") { confirm(); true }
                }
                .pointerInput(Unit) {
                    awaitEachGesture {
                        awaitFirstDown()
                        var done = false
                        fx.startHold()
                        val job: Job = scope.launch {
                            val start = withFrameMillis { it }
                            while (true) {
                                val now = withFrameMillis { it }
                                fill = ((now - start) / 800f).coerceAtMost(1f)
                                if (fill >= 1f) break
                            }
                            done = true
                            fx.confirm()
                            confirm()
                            delay(250)
                            fill = 0f
                        }
                        waitForUpOrCancellation()
                        if (!done) {
                            job.cancel()
                            fx.stopHold()
                            fill = 0f
                        }
                    }
                }
                .padding(start = 16.dp, end = 10.dp, top = 6.dp, bottom = 6.dp),
            contentAlignment = Alignment.CenterStart,
        ) { ActLabel(label, hint, primary) }
        trailing?.invoke()
    }
}

/** Little secondary button inside an action (e.g. "DETAILS"). */
@Composable
fun MiniButton(text: String, onClick: () -> Unit) {
    Box(
        Modifier.heightIn(min = 44.dp).gameClick(onClick = onClick).padding(horizontal = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Box(Modifier.background(G.chip).padding(horizontal = 8.dp, vertical = 4.dp)) {
            Text(text.uppercase(), style = capsLabel(12.sp, G.fg, FontWeight.Bold, 0.14.em))
        }
    }
}

/** Column of actions at the bottom of a panel. */
@Composable
fun Actions(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().padding(top = 8.dp, bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(5.dp), content = content)
}
