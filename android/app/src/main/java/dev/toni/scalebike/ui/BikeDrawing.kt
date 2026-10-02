package dev.toni.scalebike.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateCentroid
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChanged
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.toni.scalebike.data.Health
import dev.toni.scalebike.ui.theme.Orange
import dev.toni.scalebike.ui.theme.color
import kotlin.math.cos
import kotlin.math.sin

/** Drawing space is 1000 × 620 units. Geometry is a stylised size-L Scale hardtail (≈0.5 units per mm). */
private const val W = 1000f
private const val H = 620f

private val R = Offset(230f, 420f)   // rear axle
private val F = Offset(812f, 420f)   // front axle
private val BB = Offset(455f, 450f)  // bottom bracket

data class Hotspot(val slot: String, val x: Float, val y: Float, val label: String)

val Hotspots = listOf(
    Hotspot("frame", 546f, 188f, "Frame"),
    Hotspot("fork", 770f, 305f, "Fork"),
    Hotspot("headset", 700f, 176f, "Headset"),
    Hotspot("stem", 712f, 136f, "Stem"),
    Hotspot("handlebar", 752f, 118f, "Handlebar"),
    Hotspot("grips", 790f, 114f, "Grips"),
    Hotspot("shifter", 742f, 148f, "Shifter"),
    Hotspot("brake_front", 790f, 388f, "Front brake"),
    Hotspot("rotor_front", 782f, 452f, "Front rotor"),
    Hotspot("wheel_front", 812f, 280f, "Front wheel"),
    Hotspot("tire_front", 968f, 330f, "Front tyre"),
    Hotspot("brake_rear", 278f, 424f, "Rear brake"),
    Hotspot("rotor_rear", 200f, 452f, "Rear rotor"),
    Hotspot("cassette", 230f, 420f, "Cassette"),
    Hotspot("derailleur", 250f, 494f, "Derailleur"),
    Hotspot("wheel_rear", 230f, 280f, "Rear wheel"),
    Hotspot("tire_rear", 74f, 330f, "Rear tyre"),
    Hotspot("chain", 340f, 394f, "Chain"),
    Hotspot("crankset", 480f, 488f, "Crankset"),
    Hotspot("bottom_bracket", 455f, 450f, "BB"),
    Hotspot("pedals", 505f, 525f, "Pedals"),
    Hotspot("seatpost", 386f, 164f, "Seatpost"),
    Hotspot("saddle", 377f, 112f, "Saddle"),
)

@Composable
fun BikeDrawing(
    health: Map<String, Health>,
    selected: String?,
    onSelect: (String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    var zoom by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    val measurer = rememberTextMeasurer()

    Canvas(
        modifier
            .fillMaxWidth()
            .aspectRatio(W / H)
            .clipToBounds()
            // Pinch to zoom; one-finger pan only while zoomed so the page still scrolls normally.
            .pointerInput(Unit) {
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    do {
                        val event = awaitPointerEvent()
                        val pressed = event.changes.count { it.pressed }
                        if (pressed >= 2 || zoom > 1.01f) {
                            val centroid = event.calculateCentroid()
                            if (centroid != Offset.Unspecified) {
                                val newZoom = (zoom * event.calculateZoom()).coerceIn(1f, 4f)
                                val raw = centroid - (centroid - offset) * (newZoom / zoom) + event.calculatePan()
                                val w = size.width.toFloat()
                                val h = size.height.toFloat()
                                offset = Offset(raw.x.coerceIn(w - w * newZoom, 0f), raw.y.coerceIn(h - h * newZoom, 0f))
                                zoom = newZoom
                                event.changes.forEach { if (it.positionChanged()) it.consume() }
                            }
                        }
                    } while (event.changes.any { it.pressed })
                }
            }
            .pointerInput(Unit) {
                detectTapGestures(
                    onDoubleTap = { zoom = 1f; offset = Offset.Zero },
                    onTap = { tap ->
                        val s = size.width / W * zoom
                        val hit = Hotspots
                            .map { it to (offset + Offset(it.x * s, it.y * s) - tap).getDistance() }
                            .filter { it.second < 30.dp.toPx() }
                            .minByOrNull { it.second }
                        onSelect(hit?.first?.slot)
                    },
                )
            },
    ) {
        val s = size.width / W
        withTransform({
            translate(offset.x, offset.y)
            scale(s * zoom, s * zoom, pivot = Offset.Zero)
        }) {
            drawBike(measurer)
        }

        // Hotspots are drawn in screen space so they keep a constant, finger-friendly size.
        val showAllLabels = zoom >= 1.8f
        Hotspots.forEach { h ->
            val p = offset + Offset(h.x * s * zoom, h.y * s * zoom)
            val c = (health[h.slot] ?: Health.UNTRACKED).color()
            val isSel = h.slot == selected
            if (isSel) drawCircle(c.copy(alpha = 0.3f), radius = 18.dp.toPx(), center = p)
            drawCircle(Color.Black.copy(alpha = 0.6f), radius = 8.5.dp.toPx(), center = p)
            drawCircle(c, radius = 6.5.dp.toPx(), center = p)
            if (isSel) drawCircle(Color.White, radius = 8.5.dp.toPx(), center = p, style = Stroke(2.dp.toPx()))
            if (isSel || showAllLabels) drawLabel(measurer, h.label, p, highlighted = isSel)
        }
    }
}

private fun DrawScope.drawLabel(measurer: TextMeasurer, text: String, at: Offset, highlighted: Boolean) {
    val layout = measurer.measure(text, TextStyle(fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color.White))
    val padH = 6.dp.toPx()
    val padV = 3.dp.toPx()
    val w = layout.size.width + padH * 2
    val h = layout.size.height + padV * 2
    var x = at.x - w / 2
    var y = at.y - h - 12.dp.toPx()
    x = x.coerceIn(2f, size.width - w - 2f)
    if (y < 2f) y = at.y + 12.dp.toPx()
    drawRoundRect(
        if (highlighted) Orange else Color(0xE6202226),
        topLeft = Offset(x, y), size = Size(w, h), cornerRadius = CornerRadius(h / 2),
    )
    drawText(layout, topLeft = Offset(x + padH, y + padV))
}

// ---------------------------------------------------------------- bike artwork (unit space)

private val frameFill = Color(0xFF1A1B1E)
private val frameEdge = Color(0xFF50545B)
private val rubber = Color(0xFF2B2C2F)
private val metal = Color(0xFF9DA2A9)
private val darkMetal = Color(0xFF5A5F66)
private val hose = Color(0xFF34363B)

private fun DrawScope.tube(a: Offset, b: Offset, width: Float, fill: Color = frameFill, edge: Color = frameEdge) {
    drawLine(edge, a, b, strokeWidth = width + 3f, cap = StrokeCap.Round)
    drawLine(fill, a, b, strokeWidth = width, cap = StrokeCap.Round)
}

private fun DrawScope.wheel(c: Offset, rotorR: Float) {
    // tyre with knobs
    drawCircle(rubber, radius = 172f, center = c, style = Stroke(20f))
    drawCircle(Color(0xFF232427), radius = 184f, center = c, style = Stroke(6f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(7f, 7f))))
    // rim
    drawCircle(Color(0xFF2E3034), radius = 158f, center = c, style = Stroke(10f))
    drawCircle(frameEdge, radius = 153f, center = c, style = Stroke(1.5f))
    // spokes
    for (i in 0 until 16) {
        val a = Math.toRadians(i * 22.5 + 6).toFloat()
        val hubOff = if (i % 2 == 0) 9f else 14f
        drawLine(
            Color(0xFF6C7178),
            c + Offset(cos(a) * hubOff, sin(a) * hubOff),
            c + Offset(cos(a + 0.18f) * 152f, sin(a + 0.18f) * 152f),
            strokeWidth = 1.6f,
        )
    }
    // rotor
    drawCircle(metal.copy(alpha = 0.85f), radius = rotorR, center = c, style = Stroke(5f))
    drawCircle(darkMetal, radius = rotorR - 8f, center = c, style = Stroke(2f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(5f, 6f))))
    // hub
    drawCircle(Color(0xFF26282C), radius = 16f, center = c)
    drawCircle(metal, radius = 5f, center = c)
}

private fun DrawScope.drawBike(measurer: TextMeasurer) {
    // Wheels
    wheel(R, 40f)
    wheel(F, 44f)

    // Cassette (10–51T)
    for ((i, r) in listOf(48f, 40f, 32f, 24f, 16f).withIndex()) {
        drawCircle(if (i % 2 == 0) metal else darkMetal, radius = r, center = R, style = Stroke(3.5f))
    }

    // Brake hoses (behind frame)
    val frontHose = Path().apply { moveTo(762f, 128f); quadraticTo(800f, 210f, 792f, 380f) }
    drawPath(frontHose, hose, style = Stroke(3.5f))
    val rearHose = Path().apply {
        moveTo(750f, 130f); lineTo(700f, 214f); lineTo(470f, 438f); lineTo(282f, 418f)
    }
    drawPath(rearHose, hose, style = Stroke(3f))

    // Rear triangle
    tube(BB, R, 12f)                              // chainstay
    tube(Offset(399f, 222f), R, 10f)              // seatstay
    // Main triangle
    tube(BB, Offset(395f, 200f), 18f)             // seat tube
    tube(Offset(399f, 216f), Offset(693f, 160f), 18f) // top tube
    tube(BB, Offset(704f, 198f), 26f)             // down tube
    tube(Offset(690f, 150f), Offset(709f, 202f), 28f) // head tube

    // Down tube graphics
    val mid = Offset(580f, 324f)
    rotate(degrees = -45.3f, pivot = mid) {
        val label = measurer.measure("SCOTT  SCALE", TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Black, color = Color(0xFFCDD1D6), letterSpacing = 2.sp))
        // Text is measured in px; scale it to roughly 18 units tall.
        val k = 18f / label.size.height
        withTransform({ scale(k, k, pivot = mid) }) {
            drawText(label, topLeft = mid - Offset(label.size.width / 2f, label.size.height / 2f))
        }
    }

    // Fork: crown, stanchions, lowers
    tube(Offset(711f, 206f), Offset(742f, 214f), 14f, fill = Color(0xFF202226))
    drawLine(metal, Offset(735f, 215f), Offset(766f, 297f), strokeWidth = 12f, cap = StrokeCap.Round)
    tube(Offset(764f, 292f), F, 17f, fill = Color(0xFF202226))
    drawCircle(Color(0xFF8A8F96), radius = 5f, center = Offset(740f, 214f)) // lockout/top cap

    // Spacers, stem, bar, grip, lever, shifter
    tube(Offset(689f, 148f), Offset(686f, 138f), 22f, fill = Color(0xFF26282C))
    tube(Offset(686f, 140f), Offset(735f, 130f), 12f)
    drawLine(Color(0xFF3A3D42), Offset(732f, 131f), Offset(760f, 124f), strokeWidth = 9f, cap = StrokeCap.Round)
    drawLine(rubber, Offset(758f, 124f), Offset(792f, 116f), strokeWidth = 14f, cap = StrokeCap.Round)
    drawLine(metal, Offset(752f, 126f), Offset(784f, 141f), strokeWidth = 4f, cap = StrokeCap.Round)
    drawCircle(Color(0xFF26282C), radius = 7f, center = Offset(742f, 142f))

    // Seatpost + saddle
    drawLine(metal, Offset(395f, 202f), Offset(377f, 128f), strokeWidth = 12f, cap = StrokeCap.Round)
    drawLine(Color(0xFF222428), Offset(392f, 206f), Offset(397f, 194f), strokeWidth = 20f) // seat clamp
    val saddle = Path().apply {
        moveTo(330f, 122f)
        quadraticTo(372f, 106f, 446f, 112f)
        lineTo(448f, 121f)
        quadraticTo(385f, 126f, 334f, 131f)
        close()
    }
    drawPath(saddle, Color(0xFF1E1F22))
    drawPath(saddle, frameEdge, style = Stroke(2f))

    // Drivetrain: chain, derailleur, chainring, crank, pedal
    val chainFx = PathEffect.dashPathEffect(floatArrayOf(5f, 3f))
    drawLine(metal, Offset(455f, 417f), Offset(230f, 372f), strokeWidth = 4f, pathEffect = chainFx)
    drawLine(metal, Offset(455f, 483f), Offset(250f, 501f), strokeWidth = 4f, pathEffect = chainFx)
    drawLine(metal, Offset(244f, 494f), Offset(236f, 462f), strokeWidth = 4f, pathEffect = chainFx)
    drawLine(Color(0xFF2A2C30), Offset(232f, 426f), Offset(240f, 452f), strokeWidth = 10f, cap = StrokeCap.Round)
    drawLine(Color(0xFF2A2C30), Offset(238f, 456f), Offset(252f, 494f), strokeWidth = 9f, cap = StrokeCap.Round)
    drawCircle(darkMetal, radius = 7f, center = Offset(238f, 456f))
    drawCircle(darkMetal, radius = 7f, center = Offset(250f, 494f))

    drawCircle(darkMetal, radius = 34f, center = BB, style = Stroke(6f))
    drawCircle(Color(0xFF2A2C30), radius = 38f, center = BB, style = Stroke(3f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(3f, 3f))))
    drawLine(Color(0xFF444850), BB, Offset(405f, 375f), strokeWidth = 10f, cap = StrokeCap.Round) // far-side crank
    tube(BB, Offset(505f, 525f), 13f, fill = Color(0xFF26282C))
    drawCircle(Color(0xFF2E3034), radius = 14f, center = BB)
    drawRoundRect(Color(0xFF2A2C30), topLeft = Offset(484f, 519f), size = Size(44f, 12f), cornerRadius = CornerRadius(4f))

    // Brake calipers
    drawRoundRect(Color(0xFF2E3034), topLeft = Offset(780f, 378f), size = Size(22f, 20f), cornerRadius = CornerRadius(5f))
    drawRoundRect(Color(0xFF2E3034), topLeft = Offset(266f, 410f), size = Size(24f, 18f), cornerRadius = CornerRadius(5f))
}
