package com.nipuna.teavision.ml

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.RectF
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.support.image.TensorImage
import org.tensorflow.lite.support.tensorbuffer.TensorBuffer
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min

/**
 * ML-based Leaf Segmentation for accurate boundary detection
 *
 * METHODOLOGY:
 * 1. Primary: TensorFlow Lite model for semantic segmentation (if available)
 * 2. Fallback: Advanced color-based segmentation with morphological operations
 *
 * The segmentation mask allows for:
 * - Accurate leaf area calculation
 * - Precise boundary detection
 * - Multiple leaf detection
 * - Disease region identification (future)
 *
 * MODEL REQUIREMENTS (if using TFLite):
 * - Input: 256x256x3 RGB image
 * - Output: 256x256x1 segmentation mask (0=background, 1=leaf)
 * - Place model file in assets/leaf_segmentation.tflite
 */
object LeafSegmentation {

    private const val MODEL_FILE = "leaf_segmentation.tflite"
    private const val INPUT_SIZE = 256
    private const val NUM_CLASSES = 2 // Background + Leaf

    private var interpreter: Interpreter? = null
    private var useMLModel = false

    data class SegmentationResult(
        val mask: Bitmap,           // Binary mask (white = leaf)
        val leafBounds: RectF?,     // Bounding box of detected leaf
        val leafAreaPixels: Int,    // Number of leaf pixels
        val leafPercentage: Float,  // Leaf area as percentage of image
        val confidence: Float,      // Segmentation confidence
        val usedML: Boolean
    )

    data class LeafAnalysis(
        val segmentation: SegmentationResult,
        val colorStats: ColorStatistics?,
        val healthScore: Float?     // Future: leaf health estimation
    )

    data class ColorStatistics(
        val meanHue: Float,
        val meanSaturation: Float,
        val meanValue: Float,
        val greenness: Float,       // How green the leaf is (0-1)
        val brownness: Float,       // Potential disease indicator
        val uniformity: Float       // Color uniformity (1 = uniform)
    )

    /**
     * Initialize ML model if available
     */
    fun initialize(context: Context) {
        try {
            val modelBuffer = loadModelFile(context, MODEL_FILE)
            if (modelBuffer != null) {
                val options = Interpreter.Options().apply {
                    setNumThreads(4)
                }
                interpreter = Interpreter(modelBuffer, options)
                useMLModel = true
            }
        } catch (e: Exception) {
            // Model not available, will use fallback
            useMLModel = false
        }
    }

    /**
     * Segment leaf from image
     */
    fun segmentLeaf(bitmap: Bitmap, excludeRegion: RectF? = null): SegmentationResult {
        return if (useMLModel && interpreter != null) {
            segmentWithML(bitmap, excludeRegion)
        } else {
            segmentWithColorAnalysis(bitmap, excludeRegion)
        }
    }

    /**
     * ML-based segmentation using TensorFlow Lite
     */
    private fun segmentWithML(bitmap: Bitmap, excludeRegion: RectF?): SegmentationResult {
        val interpreter = this.interpreter ?: return segmentWithColorAnalysis(bitmap, excludeRegion)

        // Preprocess: resize to model input size
        val inputBitmap = Bitmap.createScaledBitmap(bitmap, INPUT_SIZE, INPUT_SIZE, true)

        // Create input buffer
        val inputBuffer = ByteBuffer.allocateDirect(4 * INPUT_SIZE * INPUT_SIZE * 3)
        inputBuffer.order(ByteOrder.nativeOrder())

        val pixels = IntArray(INPUT_SIZE * INPUT_SIZE)
        inputBitmap.getPixels(pixels, 0, INPUT_SIZE, 0, 0, INPUT_SIZE, INPUT_SIZE)

        for (pixel in pixels) {
            // Normalize to [0, 1]
            inputBuffer.putFloat(((pixel shr 16) and 0xFF) / 255.0f)
            inputBuffer.putFloat(((pixel shr 8) and 0xFF) / 255.0f)
            inputBuffer.putFloat((pixel and 0xFF) / 255.0f)
        }

        // Create output buffer
        val outputBuffer = ByteBuffer.allocateDirect(4 * INPUT_SIZE * INPUT_SIZE * NUM_CLASSES)
        outputBuffer.order(ByteOrder.nativeOrder())

        // Run inference
        inputBuffer.rewind()
        interpreter.run(inputBuffer, outputBuffer)

        // Process output mask
        outputBuffer.rewind()
        val mask = Bitmap.createBitmap(INPUT_SIZE, INPUT_SIZE, Bitmap.Config.ARGB_8888)
        var leafPixels = 0

        for (y in 0 until INPUT_SIZE) {
            for (x in 0 until INPUT_SIZE) {
                val bg = outputBuffer.float
                val leaf = outputBuffer.float

                // Apply softmax
                val expBg = exp(bg.toDouble())
                val expLeaf = exp(leaf.toDouble())
                val sum = expBg + expLeaf
                val leafProb = (expLeaf / sum).toFloat()

                if (leafProb > 0.5f) {
                    mask.setPixel(x, y, Color.WHITE)
                    leafPixels++
                } else {
                    mask.setPixel(x, y, Color.BLACK)
                }
            }
        }

        // Scale mask back to original size
        val scaledMask = Bitmap.createScaledBitmap(mask, bitmap.width, bitmap.height, false)

        // Apply exclude region if provided
        if (excludeRegion != null) {
            applyExcludeRegion(scaledMask, excludeRegion)
        }

        // Recalculate after exclusion
        val finalLeafPixels = countWhitePixels(scaledMask)
        val bounds = findBoundingBox(scaledMask)

        return SegmentationResult(
            mask = scaledMask,
            leafBounds = bounds,
            leafAreaPixels = finalLeafPixels,
            leafPercentage = finalLeafPixels.toFloat() / (bitmap.width * bitmap.height) * 100f,
            confidence = 0.9f,
            usedML = true
        )
    }

    /**
     * Fallback: Color-based segmentation with advanced techniques
     */
    private fun segmentWithColorAnalysis(bitmap: Bitmap, excludeRegion: RectF?): SegmentationResult {
        val width = bitmap.width
        val height = bitmap.height

        // Work on scaled version for speed
        val scale = min(1.0f, 800f / max(width, height))
        val scaledW = (width * scale).toInt()
        val scaledH = (height * scale).toInt()
        val scaled = if (scale < 1.0f) {
            Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)
        } else {
            bitmap
        }

        val pixels = IntArray(scaledW * scaledH)
        scaled.getPixels(pixels, 0, scaledW, 0, 0, scaledW, scaledH)

        // Scale exclude region
        val scaledExclude = excludeRegion?.let {
            RectF(it.left * scale, it.top * scale, it.right * scale, it.bottom * scale)
        }

        // Calculate adaptive thresholds from image statistics
        val stats = calculateImageStatistics(pixels)

        // Create binary mask
        val maskPixels = IntArray(scaledW * scaledH)
        var leafPixels = 0

        for (y in 0 until scaledH) {
            for (x in 0 until scaledW) {
                // Skip excluded region
                if (scaledExclude != null && scaledExclude.contains(x.toFloat(), y.toFloat())) {
                    maskPixels[y * scaledW + x] = Color.BLACK
                    continue
                }

                val idx = y * scaledW + x
                val pixel = pixels[idx]

                if (isLeafPixel(pixel, stats)) {
                    maskPixels[idx] = Color.WHITE
                    leafPixels++
                } else {
                    maskPixels[idx] = Color.BLACK
                }
            }
        }

        // Apply morphological operations to clean up
        val cleanedMask = morphologicalClean(maskPixels, scaledW, scaledH)

        // Create mask bitmap
        val maskBitmap = Bitmap.createBitmap(scaledW, scaledH, Bitmap.Config.ARGB_8888)
        maskBitmap.setPixels(cleanedMask, 0, scaledW, 0, 0, scaledW, scaledH)

        // Scale back to original size
        val finalMask = if (scale < 1.0f) {
            Bitmap.createScaledBitmap(maskBitmap, width, height, false)
        } else {
            maskBitmap
        }

        // Recalculate leaf pixels after morphological operations
        val finalLeafPixels = countWhitePixels(finalMask)
        val bounds = findBoundingBox(finalMask)

        return SegmentationResult(
            mask = finalMask,
            leafBounds = bounds,
            leafAreaPixels = finalLeafPixels,
            leafPercentage = finalLeafPixels.toFloat() / (width * height) * 100f,
            confidence = 0.7f,
            usedML = false
        )
    }

    /**
     * Analyze leaf color for health assessment
     */
    fun analyzeLeafColor(bitmap: Bitmap, mask: Bitmap): ColorStatistics? {
        if (bitmap.width != mask.width || bitmap.height != mask.height) return null

        val pixels = IntArray(bitmap.width * bitmap.height)
        val maskPixels = IntArray(mask.width * mask.height)
        bitmap.getPixels(pixels, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        mask.getPixels(maskPixels, 0, mask.width, 0, 0, mask.width, mask.height)

        var hueSum = 0f
        var satSum = 0f
        var valSum = 0f
        var count = 0
        val hsv = FloatArray(3)

        val hueValues = mutableListOf<Float>()

        for (i in pixels.indices) {
            if (maskPixels[i] == Color.WHITE) {
                Color.colorToHSV(pixels[i], hsv)
                hueSum += hsv[0]
                satSum += hsv[1]
                valSum += hsv[2]
                hueValues.add(hsv[0])
                count++
            }
        }

        if (count == 0) return null

        val meanHue = hueSum / count
        val meanSat = satSum / count
        val meanVal = valSum / count

        // Calculate uniformity (inverse of hue variance)
        val hueVariance = hueValues.map { (it - meanHue) * (it - meanHue) }.average().toFloat()
        val uniformity = 1f / (1f + hueVariance / 1000f)

        // Greenness: how close to green (hue ~120) with good saturation
        val greenness = max(0f, 1f - kotlin.math.abs(meanHue - 120f) / 60f) * meanSat

        // Brownness: yellowish-brown indicates disease/aging
        val brownness = if (meanHue in 20f..60f) {
            (1f - kotlin.math.abs(meanHue - 40f) / 20f) * meanSat
        } else 0f

        return ColorStatistics(
            meanHue = meanHue,
            meanSaturation = meanSat,
            meanValue = meanVal,
            greenness = greenness,
            brownness = brownness,
            uniformity = uniformity
        )
    }

    private data class ImageStats(
        val meanBrightness: Float,
        val brightnessThreshold: Float,
        val hasWhiteBackground: Boolean
    )

    private fun calculateImageStatistics(pixels: IntArray): ImageStats {
        var brightnessSum = 0L
        var whiteCount = 0

        for (pixel in pixels) {
            val r = (pixel shr 16) and 0xFF
            val g = (pixel shr 8) and 0xFF
            val b = pixel and 0xFF
            val brightness = (r + g + b) / 3
            brightnessSum += brightness
            if (brightness > 230) whiteCount++
        }

        val meanBrightness = brightnessSum.toFloat() / pixels.size
        val hasWhiteBackground = whiteCount > pixels.size * 0.3f

        // Adaptive threshold based on background
        val threshold = if (hasWhiteBackground) {
            180f // Higher threshold for white background
        } else {
            meanBrightness * 0.8f
        }

        return ImageStats(meanBrightness, threshold, hasWhiteBackground)
    }

    private fun isLeafPixel(pixel: Int, stats: ImageStats): Boolean {
        val r = (pixel shr 16) and 0xFF
        val g = (pixel shr 8) and 0xFF
        val b = pixel and 0xFF
        val brightness = (r + g + b) / 3

        // Must be darker than background threshold
        if (brightness >= stats.brightnessThreshold) return false

        // Not too dark (shadows)
        if (brightness < 20) return false

        // Greenish tint (leaves are typically green)
        val isGreenish = g >= r - 40 && g >= b - 40

        // Not gray (avoid shadows/edges)
        val saturation = max(r, max(g, b)) - min(r, min(g, b))
        val hasColor = saturation > 15

        return isGreenish && hasColor
    }

    private fun morphologicalClean(pixels: IntArray, width: Int, height: Int): IntArray {
        // Erosion followed by dilation (opening) to remove noise
        val eroded = erode(pixels, width, height)
        val dilated = dilate(eroded, width, height)

        // Additional dilation to restore leaf size
        return dilate(dilated, width, height)
    }

    private fun erode(pixels: IntArray, width: Int, height: Int): IntArray {
        val result = IntArray(pixels.size)
        val kernel = 2

        for (y in kernel until height - kernel) {
            for (x in kernel until width - kernel) {
                var allWhite = true
                outer@ for (dy in -kernel..kernel) {
                    for (dx in -kernel..kernel) {
                        if (pixels[(y + dy) * width + (x + dx)] != Color.WHITE) {
                            allWhite = false
                            break@outer
                        }
                    }
                }
                result[y * width + x] = if (allWhite) Color.WHITE else Color.BLACK
            }
        }
        return result
    }

    private fun dilate(pixels: IntArray, width: Int, height: Int): IntArray {
        val result = IntArray(pixels.size)
        val kernel = 2

        for (y in kernel until height - kernel) {
            for (x in kernel until width - kernel) {
                var anyWhite = false
                outer@ for (dy in -kernel..kernel) {
                    for (dx in -kernel..kernel) {
                        if (pixels[(y + dy) * width + (x + dx)] == Color.WHITE) {
                            anyWhite = true
                            break@outer
                        }
                    }
                }
                result[y * width + x] = if (anyWhite) Color.WHITE else Color.BLACK
            }
        }
        return result
    }

    private fun applyExcludeRegion(mask: Bitmap, region: RectF) {
        for (y in region.top.toInt() until min(region.bottom.toInt(), mask.height)) {
            for (x in region.left.toInt() until min(region.right.toInt(), mask.width)) {
                if (x >= 0 && y >= 0) {
                    mask.setPixel(x, y, Color.BLACK)
                }
            }
        }
    }

    private fun countWhitePixels(mask: Bitmap): Int {
        val pixels = IntArray(mask.width * mask.height)
        mask.getPixels(pixels, 0, mask.width, 0, 0, mask.width, mask.height)
        return pixels.count { it == Color.WHITE }
    }

    private fun findBoundingBox(mask: Bitmap): RectF? {
        val width = mask.width
        val height = mask.height
        val pixels = IntArray(width * height)
        mask.getPixels(pixels, 0, width, 0, 0, width, height)

        var minX = width
        var maxX = 0
        var minY = height
        var maxY = 0

        for (y in 0 until height) {
            for (x in 0 until width) {
                if (pixels[y * width + x] == Color.WHITE) {
                    minX = min(minX, x)
                    maxX = max(maxX, x)
                    minY = min(minY, y)
                    maxY = max(maxY, y)
                }
            }
        }

        return if (maxX > minX && maxY > minY) {
            RectF(minX.toFloat(), minY.toFloat(), maxX.toFloat(), maxY.toFloat())
        } else null
    }

    private fun loadModelFile(context: Context, filename: String): MappedByteBuffer? {
        return try {
            val assetFileDescriptor = context.assets.openFd(filename)
            val inputStream = FileInputStream(assetFileDescriptor.fileDescriptor)
            val fileChannel = inputStream.channel
            val startOffset = assetFileDescriptor.startOffset
            val declaredLength = assetFileDescriptor.declaredLength
            fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Release resources
     */
    fun close() {
        interpreter?.close()
        interpreter = null
        useMLModel = false
    }
}
