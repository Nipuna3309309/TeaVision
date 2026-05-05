package com.nipuna.teavision.utils

import android.graphics.Bitmap
import kotlin.math.sqrt
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

object ImageUtils {

    // --- RESEARCH SETTINGS ---
    private const val MIN_RESOLUTION_MP = 2.0
    private const val BLUR_THRESHOLD = 40.0
    private const val GLARE_THRESHOLD = 0.05
    private const val CLUTTER_THRESHOLD = 0.35

    // Light score thresholds (0-100 combined score)
    private const val LIGHT_TOO_DARK = 20.0
    private const val LIGHT_POOR = 40.0
    private const val LIGHT_GOOD_MAX = 85.0
    private const val LIGHT_TOO_BRIGHT = 95.0

    data class LightAnalysis(
        val score: Double,              // 0-100 combined light score
        val level: String,              // "too_dark", "poor", "good", "bright", "too_bright"
        val label: String,              // Human-readable label
        val bgBrightness: Double,       // Background-only brightness (0-255)
        val highlightBrightness: Double,// Top 5% brightest pixels (0-255)
        val avgSaturation: Double,      // Average saturation (0-255)
        val overexposedPct: Double,     // % of overexposed pixels
        val underexposedPct: Double,    // % of underexposed pixels
        val rawBrightness: Double,      // Old-style average brightness for compatibility
        val tip: String                 // Recommendation
    )

    data class QualityReport(
        val isPassed: Boolean,
        val blurScore: Double,
        val resolutionMP: Double,
        val brightness: Double,
        val hasGlare: Boolean,
        val glarePercentage: Double,
        val hasClutteredBackground: Boolean,
        val failureReasons: List<String> = emptyList(),
        val lightAnalysis: LightAnalysis? = null
    )

    /**
     * RESEARCH-GRADE CHECK:
     * 1. Resolution (NO upscaling)
     * 2. Blur
     * 3. Lighting (multi-signal: background + highlights + saturation)
     * 4. Glare/blown highlights
     * 5. Background clutter
     *
     * Returns original bitmap UNTOUCHED + QualityReport
     */
    fun checkQuality(bitmap: Bitmap): Pair<Bitmap, QualityReport> {
        val failures = mutableListOf<String>()

        // 1. Resolution Check
        val resolutionMP = getResolutionMP(bitmap)
        if (resolutionMP < MIN_RESOLUTION_MP) {
            failures.add("Low Resolution: ${String.format("%.1f", resolutionMP)} MP (min ${MIN_RESOLUTION_MP} MP required)")
        }

        // 2. Blur Check
        val blurScore = calculateBlurScore(bitmap)
        if (blurScore < BLUR_THRESHOLD) {
            failures.add("Too Blurry (Score: ${String.format("%.0f", blurScore)}, need $BLUR_THRESHOLD+)")
        }

        // 3. Multi-signal Light Analysis
        val lightAnalysis = analyzeLighting(bitmap)
        if (lightAnalysis.level == "too_dark") {
            failures.add("Too Dark (Light Score: ${String.format("%.0f", lightAnalysis.score)}/100)")
        } else if (lightAnalysis.level == "too_bright") {
            failures.add("Too Bright / Overexposed (Light Score: ${String.format("%.0f", lightAnalysis.score)}/100)")
        }

        // 4. Glare Detection
        val glarePercentage = calculateGlarePercentage(bitmap)
        val hasGlare = glarePercentage > GLARE_THRESHOLD
        if (hasGlare) {
            failures.add("Glare Detected (${String.format("%.1f", glarePercentage * 100)}% blown highlights)")
        }

        // 5. Background Clutter
        val hasClutter = detectBackgroundClutter(bitmap)
        if (hasClutter) {
            failures.add("Cluttered Background (use plain cloth)")
        }

        val isPassed = failures.isEmpty()

        return Pair(
            bitmap,
            QualityReport(
                isPassed = isPassed,
                blurScore = blurScore,
                resolutionMP = resolutionMP,
                brightness = lightAnalysis.rawBrightness, // backward compat
                hasGlare = hasGlare,
                glarePercentage = glarePercentage,
                hasClutteredBackground = hasClutter,
                failureReasons = failures,
                lightAnalysis = lightAnalysis
            )
        )
    }

    /**
     * Multi-signal lighting analysis.
     *
     * Problem: Tea leaves are dark green → average brightness is always low.
     * Solution: Analyze BACKGROUND (non-leaf) areas, highlights, and saturation
     * to determine actual ambient lighting conditions.
     *
     * Signal 1: Background brightness — mask out green/dark leaf pixels,
     *           measure the brightness of everything else (table, paper, etc.)
     * Signal 2: Highlight percentile — top 5% brightest pixels.
     *           Well-lit scenes have bright highlights even on dark subjects.
     * Signal 3: Saturation — in low light cameras boost ISO → washed/noisy colors.
     *           Good light → vivid saturated colors.
     * Signal 4: Over/under exposure check.
     */
    fun analyzeLighting(bitmap: Bitmap): LightAnalysis {
        val scaled = Bitmap.createScaledBitmap(
            bitmap, 300,
            (bitmap.height * (300.0 / bitmap.width)).toInt(), true
        )
        val width = scaled.width
        val height = scaled.height
        val totalPixels = width * height
        val pixels = IntArray(totalPixels)
        scaled.getPixels(pixels, 0, width, 0, 0, width, height)

        // Extract per-pixel values
        val luminances = IntArray(totalPixels)
        val saturations = DoubleArray(totalPixels)
        val isLeafPixel = BooleanArray(totalPixels)

        var rawBrightnessSum = 0L

        for (i in pixels.indices) {
            val pixel = pixels[i]
            val r = (pixel shr 16) and 0xFF
            val g = (pixel shr 8) and 0xFF
            val b = pixel and 0xFF

            // Luminance
            val luma = (0.299 * r + 0.587 * g + 0.114 * b).toInt()
            luminances[i] = luma
            rawBrightnessSum += luma

            // Saturation (simplified HSV-like)
            val maxC = max(r, max(g, b))
            val minC = min(r, min(g, b))
            saturations[i] = if (maxC > 0) (maxC - minC).toDouble() / maxC else 0.0

            // Leaf detection: pixel is likely a leaf if it's greenish and not very bright
            // Green-dominant: G > R-20 AND G > B-10 AND not too bright
            val isGreen = g > r - 20 && g > b - 10 && g > 40
            val isDark = luma < 160
            val hasColor = (maxC - minC) > 25 // has some saturation
            isLeafPixel[i] = isGreen && isDark && hasColor
        }

        val rawBrightness = rawBrightnessSum.toDouble() / totalPixels

        // --- Signal 1: Background brightness (non-leaf pixels) ---
        var bgSum = 0L
        var bgCount = 0
        for (i in pixels.indices) {
            if (!isLeafPixel[i]) {
                bgSum += luminances[i]
                bgCount++
            }
        }

        val bgBrightness = if (bgCount > totalPixels * 0.05) {
            // At least 5% background pixels found
            bgSum.toDouble() / bgCount
        } else {
            // Almost entire image is leaf — use 90th percentile as fallback
            val sorted = luminances.clone()
            sorted.sort()
            sorted[(totalPixels * 0.90).toInt()].toDouble()
        }

        // --- Signal 2: Highlight analysis (top 5% brightest pixels) ---
        val sortedLuma = luminances.clone()
        sortedLuma.sort()
        val p95Index = (totalPixels * 0.95).toInt().coerceIn(0, totalPixels - 1)
        val highlightBrightness = sortedLuma[p95Index].toDouble()

        // --- Signal 3: Saturation ---
        val avgSaturation = saturations.average() * 255.0

        // --- Signal 4: Over/under exposure ---
        var overexposedCount = 0
        var underexposedCount = 0
        for (luma in luminances) {
            if (luma > 250) overexposedCount++
            if (luma < 15) underexposedCount++
        }
        val overexposedPct = overexposedCount.toDouble() / totalPixels * 100
        val underexposedPct = underexposedCount.toDouble() / totalPixels * 100

        // --- Combine into final score (0-100) ---
        val bgPct = bgBrightness / 255.0 * 100.0
        val highlightPct = highlightBrightness / 255.0 * 100.0
        val satScore = min(100.0, avgSaturation / 255.0 * 100.0 * 1.3)

        var lightScore = bgPct * 0.40 + highlightPct * 0.30 + satScore * 0.30

        // Clamp
        lightScore = lightScore.coerceIn(0.0, 100.0)

        // Penalize overexposure
        if (overexposedPct > 15) {
            lightScore = min(lightScore, 95.0)
        }

        // Classify
        val (level, label, tip) = when {
            lightScore < LIGHT_TOO_DARK -> Triple(
                "too_dark", "Too Dark",
                "Move to a brighter area or use additional lighting."
            )
            lightScore < LIGHT_POOR -> Triple(
                "poor", "Poor Lighting",
                "Lighting is dim. Consider adding more light for better results."
            )
            lightScore < LIGHT_GOOD_MAX -> Triple(
                "good", "Good Lighting",
                "Lighting conditions are ideal for analysis."
            )
            lightScore < LIGHT_TOO_BRIGHT -> Triple(
                "bright", "Bright",
                "Slightly bright but acceptable for analysis."
            )
            else -> Triple(
                "too_bright", "Too Bright / Overexposed",
                "Image is overexposed. Reduce direct light or move to shade."
            )
        }

        return LightAnalysis(
            score = Math.round(lightScore * 10.0) / 10.0,
            level = level,
            label = label,
            bgBrightness = Math.round(bgBrightness * 10.0) / 10.0,
            highlightBrightness = Math.round(highlightBrightness * 10.0) / 10.0,
            avgSaturation = Math.round(avgSaturation * 10.0) / 10.0,
            overexposedPct = Math.round(overexposedPct * 10.0) / 10.0,
            underexposedPct = Math.round(underexposedPct * 10.0) / 10.0,
            rawBrightness = Math.round(rawBrightness * 10.0) / 10.0,
            tip = tip
        )
    }

    /**
     * Standard Laplacian Variance for Blur Detection
     */
    private fun calculateBlurScore(bitmap: Bitmap): Double {
        val scaled = Bitmap.createScaledBitmap(bitmap, 400, (bitmap.height * (400.0 / bitmap.width)).toInt(), true)
        val width = scaled.width
        val height = scaled.height
        val pixels = IntArray(width * height)
        scaled.getPixels(pixels, 0, width, 0, 0, width, height)

        var sum = 0L
        var count = 0

        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                val idx = y * width + x
                val valC = getLuminance(pixels[idx])
                val valL = getLuminance(pixels[idx - 1])
                val valR = getLuminance(pixels[idx + 1])
                val valU = getLuminance(pixels[idx - width])
                val valD = getLuminance(pixels[idx + width])

                val lap = (valL + valR + valU + valD) - (4 * valC)
                sum += abs(lap)
                count++
            }
        }
        return sum.toDouble() / count * 10
    }

    /**
     * Detect blown highlights (glare from flash/reflections)
     */
    private fun calculateGlarePercentage(bitmap: Bitmap): Double {
        val scaled = Bitmap.createScaledBitmap(bitmap, 200, (bitmap.height * (200.0 / bitmap.width)).toInt(), true)
        val width = scaled.width
        val height = scaled.height
        val pixels = IntArray(width * height)
        scaled.getPixels(pixels, 0, width, 0, 0, width, height)

        var blownCount = 0
        for (pixel in pixels) {
            val r = (pixel shr 16) and 0xFF
            val g = (pixel shr 8) and 0xFF
            val b = pixel and 0xFF
            if ((r > 250 || g > 250 || b > 250) && (r + g + b) > 700) {
                blownCount++
            }
        }
        return blownCount.toDouble() / pixels.size
    }

    /**
     * Background clutter detection via edge region variance
     */
    private fun detectBackgroundClutter(bitmap: Bitmap): Boolean {
        val scaled = Bitmap.createScaledBitmap(bitmap, 100, (bitmap.height * (100.0 / bitmap.width)).toInt(), true)
        val width = scaled.width
        val height = scaled.height
        val pixels = IntArray(width * height)
        scaled.getPixels(pixels, 0, width, 0, 0, width, height)

        val edgePixels = mutableListOf<Int>()
        val edgeMargin = 0.15

        for (y in 0 until height) {
            for (x in 0 until width) {
                val isEdge = y < height * edgeMargin ||
                             y > height * (1 - edgeMargin) ||
                             x < width * edgeMargin ||
                             x > width * (1 - edgeMargin)
                if (isEdge) {
                    edgePixels.add(getLuminance(pixels[y * width + x]))
                }
            }
        }

        if (edgePixels.isEmpty()) return false

        val mean = edgePixels.average()
        val variance = edgePixels.map { (it - mean) * (it - mean) }.average()
        val normalizedVariance = sqrt(variance) / 255.0

        return normalizedVariance > CLUTTER_THRESHOLD
    }

    private fun getLuminance(color: Int): Int {
        val r = (color shr 16) and 0xFF
        val g = (color shr 8) and 0xFF
        val b = color and 0xFF
        return (0.299 * r + 0.587 * g + 0.114 * b).toInt()
    }

    fun getResolutionMP(bitmap: Bitmap): Double {
        return (bitmap.width * bitmap.height) / 1_000_000.0
    }
}
