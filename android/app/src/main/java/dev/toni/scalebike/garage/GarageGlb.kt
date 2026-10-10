package dev.toni.scalebike.garage

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.cos
import kotlin.math.sin

/**
 * What the engine needs from a .glb's JSON that Filament cannot give back: the original emissive colour
 * of every primitive (Filament has no getter for material parameters). Used to restore a part after a
 * highlight and to fade the garage neon in the intro.
 */
internal class GlbInfo private constructor(
    private val byNode: Map<String, List<FloatArray>>,
    private val byMaterial: Map<String, FloatArray>,
) {
    /** Emissive (factor * strength, linear) of a primitive, looked up by node name, else by material name. */
    fun emissive(nodeName: String?, primitive: Int, materialName: String?): FloatArray {
        nodeName?.let { name -> byNode[name]?.getOrNull(primitive)?.let { return it } }
        materialName?.let { name -> byMaterial[name]?.let { return it } }
        return ZERO
    }

    companion object {
        private val ZERO = floatArrayOf(0f, 0f, 0f)

        fun parse(glb: ByteArray): GlbInfo? = try {
            val bb = ByteBuffer.wrap(glb).order(ByteOrder.LITTLE_ENDIAN)
            require(bb.getInt(0) == 0x46546C67) { "not a GLB" }
            val jsonLength = bb.getInt(12)
            require(bb.getInt(16) == 0x4E4F534A) { "first chunk is not JSON" }
            val json = JSONObject(String(glb, 20, jsonLength, Charsets.UTF_8))
            fromJson(json)
        } catch (e: Exception) {
            null
        }

        private fun fromJson(json: JSONObject): GlbInfo {
            val materials = json.optJSONArray("materials") ?: JSONArray()
            val matEmissive = ArrayList<FloatArray>(materials.length())
            val byMaterial = HashMap<String, FloatArray>()
            for (i in 0 until materials.length()) {
                val m = materials.getJSONObject(i)
                val f = m.optJSONArray("emissiveFactor")
                val strength = m.optJSONObject("extensions")
                    ?.optJSONObject("KHR_materials_emissive_strength")
                    ?.optDouble("emissiveStrength", 1.0) ?: 1.0
                val e = if (f != null && f.length() >= 3) {
                    floatArrayOf(
                        (f.getDouble(0) * strength).toFloat(),
                        (f.getDouble(1) * strength).toFloat(),
                        (f.getDouble(2) * strength).toFloat(),
                    )
                } else ZERO
                matEmissive.add(e)
                m.optString("name").takeIf { it.isNotEmpty() }?.let { byMaterial[it] = e }
            }
            val meshes = json.optJSONArray("meshes") ?: JSONArray()
            val nodes = json.optJSONArray("nodes") ?: JSONArray()
            val byNode = HashMap<String, List<FloatArray>>()
            for (i in 0 until nodes.length()) {
                val n = nodes.getJSONObject(i)
                val name = n.optString("name").takeIf { it.isNotEmpty() } ?: continue
                val meshIndex = n.optInt("mesh", -1)
                if (meshIndex < 0 || meshIndex >= meshes.length()) continue
                val prims = meshes.getJSONObject(meshIndex).optJSONArray("primitives") ?: continue
                byNode[name] = List(prims.length()) { p ->
                    val mi = prims.getJSONObject(p).optInt("material", -1)
                    matEmissive.getOrNull(mi) ?: ZERO
                }
            }
            return GlbInfo(byNode, byMaterial)
        }
    }
}

/**
 * Builds a tiny garage .glb in memory for when assets/garage.glb is missing: a dark glossy floor disc,
 * a turntable disc (node "turntable", origin at the turntable centre) and a yellow neon ring ("neon_ring").
 * Loaded through gltfio like the real file, so no extra material files are needed.
 */
internal object FallbackGarage {
    private const val SEGMENTS = 96

    private class Mesh(val positions: FloatArray, val indices: ShortArray, val material: Int) {
        val vertexCount get() = positions.size / 3
    }

    fun build(): ByteArray {
        val cx = GarageTuning.TURNTABLE_X.toFloat()
        // floor centred under the turntable, in world space (node without translation)
        val floor = disc(0f, 0f, 0f, 0f, 5.5f, material = 0, offsetX = cx)
        // turntable top at y = 0.035, node translated to the centre
        val table = disc(0.035f, 0f, 0f, 0f, 1.0f, material = 1, offsetX = 0f)
        val ring = disc(0.0355f, 0f, 0f, 1.0f, 1.035f, material = 2, offsetX = 0f)
        val meshes = listOf(floor, table, ring)

        val bin = ByteArrayOutputStream()
        val bufferViews = JSONArray()
        val accessors = JSONArray()
        val gltfMeshes = JSONArray()
        meshes.forEachIndexed { i, mesh ->
            val posAcc = accessors.length()
            addView(bin, bufferViews, floatBytes(mesh.positions), 34962)
            accessors.put(
                JSONObject().put("bufferView", bufferViews.length() - 1).put("componentType", 5126)
                    .put("count", mesh.vertexCount).put("type", "VEC3")
                    .put("min", JSONArray(minMax(mesh.positions, true)))
                    .put("max", JSONArray(minMax(mesh.positions, false)))
            )
            val normals = FloatArray(mesh.positions.size) { if (it % 3 == 1) 1f else 0f }
            addView(bin, bufferViews, floatBytes(normals), 34962)
            accessors.put(
                JSONObject().put("bufferView", bufferViews.length() - 1).put("componentType", 5126)
                    .put("count", mesh.vertexCount).put("type", "VEC3")
            )
            addView(bin, bufferViews, shortBytes(mesh.indices), 34963)
            accessors.put(
                JSONObject().put("bufferView", bufferViews.length() - 1).put("componentType", 5123)
                    .put("count", mesh.indices.size).put("type", "SCALAR")
            )
            gltfMeshes.put(
                JSONObject().put("name", "mesh$i").put(
                    "primitives", JSONArray().put(
                        JSONObject().put(
                            "attributes", JSONObject().put("POSITION", posAcc).put("NORMAL", posAcc + 1)
                        ).put("indices", posAcc + 2).put("material", mesh.material)
                    )
                )
            )
        }
        val neon = GarageTuning.linear(GarageTuning.SELECT_HEX)
        val materials = JSONArray()
            .put(pbr("floor", floatArrayOf(0.02f, 0.021f, 0.024f), metallic = 0f, roughness = 0.3f))
            .put(pbr("turntable", floatArrayOf(0.04f, 0.045f, 0.05f), metallic = 0.8f, roughness = 0.3f))
            .put(
                pbr("neon_ring", floatArrayOf(0f, 0f, 0f), metallic = 0f, roughness = 0.5f)
                    .put("emissiveFactor", JSONArray(neon.map { it.toDouble() }))
                    .put(
                        "extensions", JSONObject().put(
                            "KHR_materials_emissive_strength", JSONObject().put("emissiveStrength", 6.0)
                        )
                    )
            )
        val nodes = JSONArray()
            .put(JSONObject().put("name", "floor").put("mesh", 0))
            .put(JSONObject().put("name", "turntable").put("mesh", 1).put("translation", JSONArray(listOf(cx.toDouble(), 0.0, 0.0))))
            .put(JSONObject().put("name", "neon_ring").put("mesh", 2).put("translation", JSONArray(listOf(cx.toDouble(), 0.0, 0.0))))
        val binBytes = pad4(bin.toByteArray(), 0)
        val json = JSONObject()
            .put("asset", JSONObject().put("version", "2.0"))
            .put("extensionsUsed", JSONArray().put("KHR_materials_emissive_strength"))
            .put("scene", 0)
            .put("scenes", JSONArray().put(JSONObject().put("nodes", JSONArray(listOf(0, 1, 2)))))
            .put("nodes", nodes)
            .put("meshes", gltfMeshes)
            .put("materials", materials)
            .put("accessors", accessors)
            .put("bufferViews", bufferViews)
            .put("buffers", JSONArray().put(JSONObject().put("byteLength", binBytes.size)))
        val jsonBytes = pad4(json.toString().toByteArray(Charsets.UTF_8), 0x20)

        val total = 12 + 8 + jsonBytes.size + 8 + binBytes.size
        val out = ByteBuffer.allocate(total).order(ByteOrder.LITTLE_ENDIAN)
        out.putInt(0x46546C67).putInt(2).putInt(total)
        out.putInt(jsonBytes.size).putInt(0x4E4F534A).put(jsonBytes)
        out.putInt(binBytes.size).putInt(0x004E4942).put(binBytes)
        return out.array()
    }

    /** Flat disc (inner = 0) or annulus facing +Y, triangle list. */
    private fun disc(y: Float, cx: Float, cz: Float, inner: Float, outer: Float, material: Int, offsetX: Float): Mesh {
        val pos = ArrayList<Float>()
        val idx = ArrayList<Short>()
        if (inner <= 0f) {
            pos += listOf(cx + offsetX, y, cz)
            for (i in 0..SEGMENTS) {
                val a = 2.0 * Math.PI * i / SEGMENTS
                pos += listOf(cx + offsetX + outer * cos(a).toFloat(), y, cz + outer * sin(a).toFloat())
            }
            for (i in 1..SEGMENTS) idx += listOf(0, (i + 1).toShort(), i.toShort())
        } else {
            for (i in 0..SEGMENTS) {
                val a = 2.0 * Math.PI * i / SEGMENTS
                val c = cos(a).toFloat()
                val s = sin(a).toFloat()
                pos += listOf(cx + offsetX + inner * c, y, cz + inner * s)
                pos += listOf(cx + offsetX + outer * c, y, cz + outer * s)
            }
            for (i in 0 until SEGMENTS) {
                val a = (2 * i).toShort()
                val b = (2 * i + 1).toShort()
                val c = (2 * i + 2).toShort()
                val d = (2 * i + 3).toShort()
                idx += listOf(a, c, b, b, c, d)
            }
        }
        return Mesh(pos.toFloatArray(), idx.toShortArray(), material)
    }

    private fun pbr(name: String, color: FloatArray, metallic: Float, roughness: Float) = JSONObject()
        .put("name", name)
        .put(
            "pbrMetallicRoughness", JSONObject()
                .put("baseColorFactor", JSONArray(listOf(color[0].toDouble(), color[1].toDouble(), color[2].toDouble(), 1.0)))
                .put("metallicFactor", metallic.toDouble())
                .put("roughnessFactor", roughness.toDouble())
        )

    private fun addView(bin: ByteArrayOutputStream, views: JSONArray, bytes: ByteArray, target: Int) {
        while (bin.size() % 4 != 0) bin.write(0)
        views.put(JSONObject().put("buffer", 0).put("byteOffset", bin.size()).put("byteLength", bytes.size).put("target", target))
        bin.write(bytes)
    }

    private fun floatBytes(a: FloatArray): ByteArray =
        ByteBuffer.allocate(a.size * 4).order(ByteOrder.LITTLE_ENDIAN).also { b -> a.forEach { b.putFloat(it) } }.array()

    private fun shortBytes(a: ShortArray): ByteArray =
        ByteBuffer.allocate(a.size * 2).order(ByteOrder.LITTLE_ENDIAN).also { b -> a.forEach { b.putShort(it) } }.array()

    private fun minMax(p: FloatArray, min: Boolean): List<Double> = (0 until 3).map { c ->
        var v = p[c]
        var i = c
        while (i < p.size) {
            v = if (min) minOf(v, p[i]) else maxOf(v, p[i]); i += 3
        }
        v.toDouble()
    }

    private fun pad4(bytes: ByteArray, fill: Int): ByteArray {
        val padded = (bytes.size + 3) and 3.inv()
        if (padded == bytes.size) return bytes
        return bytes.copyOf(padded).also { for (i in bytes.size until padded) it[i] = fill.toByte() }
    }
}
