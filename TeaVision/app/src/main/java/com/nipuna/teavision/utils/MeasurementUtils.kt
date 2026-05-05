package com.nipuna.teavision.utils

import android.graphics.Bitmap
import android.graphics.PointF
import android.graphics.RectF
import com.google.mlkit.vision.barcode.BarcodeScanner
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.tasks.await
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Measurement Utilities for Tea Leaf Dimension Extraction
 *
 * METHODOLOGY:
 * Uses a reference QR code of known physical size to establish pixel-to-cm ratio.
 * The QR code should encode its size (e.g., "TEAVISION:3.0" means 3.0cm side length).
 *
 * WORKFLOW:
 * 1. Detect QR code in image using ML Kit
 * 2. Calculate pixels-per-cm from QR code dimensions
 * 3. Measure objects using the calibrated ratio
 *
 * REFERENCE CARD FORMAT:
 * - Print a QR code containing: "TEAVISION:<size_cm>"
 * - Example: "TEAVISION:3.0" for a 3cm x 3cm QR code
 * - Place the card next to the tea leaf when capturing
 */
object MeasurementUtils {

    private const val QR_PREFIX = "TEAVISION:"
    private const val DEFAULT_QR_SIZE_CM = 3.0f // Default if no size encoded

    data class CalibrationResult(
        val success: Boolean,
        val pixelsPerCm: Float,
        val qrSizeCm: Float,
        val qrBoundingBox: RectF?,
        val qrCorners: List<PointF>?,
        val message: String
    )

    data class MeasurementResult(
        val widthCm: Float,
        val heightCm: Float,
        val areaCm2: Float,
        val pixelsPerCm: Float,
        val boundingBox: RectF,
        val confidence: Float
    )

    data class LeafMeasurement(
        val calibration: CalibrationResult,
        val leafBounds: RectF?,
        val widthCm: Float?,
        val heightCm: Float?,
        val areaCm2: Float?,
        val aspectRatio: Float?
    )

    private val barcodeScanner: BarcodeScanner by lazy {
        val options = BarcodeScannerOptions.Builder()
            .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
            .build()
        BarcodeScanning.getClient(options)
    }

    /**
     * Detect QR code and establish measurement calibration
     */
    suspend fun calibrateFromQRCode(bitmap: Bitmap): CalibrationResult {
        return try {
            val inputImage = InputImage.fromBitmap(bitmap, 0)
            val barcodes = barcodeScanner.process(inputImage).await()

            if (barcodes.isEmpty()) {
                return CalibrationResult(
                    success = false,
                    pixelsPerCm = 0f,
                    qrSizeCm = 0f,
                    qrBoundingBox = null,
                    qrCorners = null,
                    message = "No QR code detected. Place reference card in frame."
                )
            }

            // Find TeaVision reference QR code
            val refBarcode = barcodes.find { barcode ->
                barcode.rawValue?.startsWith(QR_PREFIX) == true
            } ?: barcodes.first()

            // Extract size from QR content or use default
            val qrSizeCm = refBarcode.rawValue?.let { content ->
                if (content.startsWith(QR_PREFIX)) {
                    content.removePrefix(QR_PREFIX).toFloatOrNull() ?: DEFAULT_QR_SIZE_CM
                } else {
                    DEFAULT_QR_SIZE_CM
                }
            } ?: DEFAULT_QR_SIZE_CM

            // Get QR code bounding box
            val boundingBox = refBarcode.boundingBox?.let {
                RectF(it.left.toFloat(), it.top.toFloat(), it.right.toFloat(), it.bottom.toFloat())
            }

            // Get corner points for more accurate measurement
            val corners = refBarcode.cornerPoints?.map { point ->
                PointF(point.x.toFloat(), point.y.toFloat())
            }

            if (boundingBox == null) {
                return CalibrationResult(
                    success = false,
                    pixelsPerCm = 0f,
                    qrSizeCm = qrSizeCm,
                    qrBoundingBox = null,
                    qrCorners = null,
                    message = "QR code detected but no bounds available."
                )
            }

            // Calculate pixels per cm using QR code dimensions
            // Use the average of width and height for more accuracy
            val qrWidthPx = boundingBox.width()
            val qrHeightPx = boundingBox.height()
            val qrAvgSizePx = (qrWidthPx + qrHeightPx) / 2f
            val pixelsPerCm = qrAvgSizePx / qrSizeCm

            // If we have corner points, use diagonal for even better accuracy
            val pixelsPerCmFinal = if (corners != null && corners.size == 4) {
                val diagonal1 = distance(corners[0], corners[2])
                val diagonal2 = distance(corners[1], corners[3])
                val avgDiagonal = (diagonal1 + diagonal2) / 2f
                val qrDiagonalCm = qrSizeCm * sqrt(2f)
                avgDiagonal / qrDiagonalCm
            } else {
                pixelsPerCm
            }

            CalibrationResult(
                success = true,
                pixelsPerCm = pixelsPerCmFinal,
                qrSizeCm = qrSizeCm,
                qrBoundingBox = boundingBox,
                qrCorners = corners,
                message = "Calibrated: ${String.format("%.1f", pixelsPerCmFinal)} px/cm (QR: ${qrSizeCm}cm)"
            )
        } catch (e: Exception) {
            CalibrationResult(
                success = false,
                pixelsPerCm = 0f,
                qrSizeCm = 0f,
                qrBoundingBox = null,
                qrCorners = null,
                message = "Calibration error: ${e.message}"
            )
        }
    }

    /**
     * Measure a region in the image given calibration
     */
    fun measureRegion(
        regionBounds: RectF,
        pixelsPerCm: Float
    ): MeasurementResult {
        val widthPx = regionBounds.width()
        val heightPx = regionBounds.height()

        val widthCm = widthPx / pixelsPerCm
        val heightCm = heightPx / pixelsPerCm
        val areaCm2 = widthCm * heightCm

        return MeasurementResult(
            widthCm = widthCm,
            heightCm = heightCm,
            areaCm2 = areaCm2,
            pixelsPerCm = pixelsPerCm,
            boundingBox = regionBounds,
            confidence = 1.0f
        )
    }

    /**
     * Detect leaf bounds using color segmentation
     * Assumes leaf is darker/greener than white background
     */
    fun detectLeafBounds(
        bitmap: Bitmap,
        excludeRegion: RectF? = null // Exclude QR code region
    ): RectF? {
        val width = bitmap.width
        val height = bitmap.height

        // Scale down for faster processing
        val scale = 200f / max(width, height)
        val scaledW = (width * scale).toInt()
        val scaledH = (height * scale).toInt()
        val scaled = Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)

        val pixels = IntArray(scaledW * scaledH)
        scaled.getPixels(pixels, 0, scaledW, 0, 0, scaledW, scaledH)

        // Scale exclude region
        val scaledExclude = excludeRegion?.let {
            RectF(
                it.left * scale,
                it.top * scale,
                it.right * scale,
                it.bottom * scale
            )
        }

        // Find leaf pixels (non-white, greenish)
        var minX = scaledW
        var maxX = 0
        var minY = scaledH
        var maxY = 0
        var leafPixelCount = 0

        for (y in 0 until scaledH) {
            for (x in 0 until scaledW) {
                // Skip excluded region (QR code area)
                if (scaledExclude != null && scaledExclude.contains(x.toFloat(), y.toFloat())) {
                    continue
                }

                val pixel = pixels[y * scaledW + x]
                val r = (pixel shr 16) and 0xFF
                val g = (pixel shr 8) and 0xFF
                val b = pixel and 0xFF

                // Leaf detection: darker than background, often greenish
                val brightness = (r + g + b) / 3
                val isNotWhite = brightness < 200
                val isGreenish = g > r - 30 && g > b - 30 // Greenish tint
                val isNotTooBlack = brightness > 20 // Not shadow

                if (isNotWhite && isGreenish && isNotTooBlack) {
                    minX = min(minX, x)
                    maxX = max(maxX, x)
                    minY = min(minY, y)
                    maxY = max(maxY, y)
                    leafPixelCount++
                }
            }
        }

        // Need minimum leaf area
        val totalPixels = scaledW * scaledH
        if (leafPixelCount < totalPixels * 0.01) {
            return null // Less than 1% leaf area
        }

        // Add small margin and scale back to original
        val margin = 5
        return RectF(
            max(0, minX - margin) / scale,
            max(0, minY - margin) / scale,
            min(scaledW - 1, maxX + margin) / scale,
            min(scaledH - 1, maxY + margin) / scale
        )
    }

    /**
     * Complete measurement pipeline: calibrate + detect leaf + measure
     */
    suspend fun measureLeaf(bitmap: Bitmap): LeafMeasurement {
        // Step 1: Calibrate using QR code
        val calibration = calibrateFromQRCode(bitmap)

        if (!calibration.success) {
            return LeafMeasurement(
                calibration = calibration,
                leafBounds = null,
                widthCm = null,
                heightCm = null,
                areaCm2 = null,
                aspectRatio = null
            )
        }

        // Step 2: Detect leaf bounds (excluding QR code region)
        val leafBounds = detectLeafBounds(bitmap, calibration.qrBoundingBox)

        if (leafBounds == null) {
            return LeafMeasurement(
                calibration = calibration,
                leafBounds = null,
                widthCm = null,
                heightCm = null,
                areaCm2 = null,
                aspectRatio = null
            )
        }

        // Step 3: Measure
        val measurement = measureRegion(leafBounds, calibration.pixelsPerCm)

        return LeafMeasurement(
            calibration = calibration,
            leafBounds = leafBounds,
            widthCm = measurement.widthCm,
            heightCm = measurement.heightCm,
            areaCm2 = measurement.areaCm2,
            aspectRatio = if (measurement.heightCm > 0) measurement.widthCm / measurement.heightCm else null
        )
    }

    /**
     * Generate printable reference card content
     * Returns SVG or instructions for the reference QR code
     */
    fun getReferenceCardInstructions(sizeCm: Float = 3.0f): String {
        return """
            TEAVISION REFERENCE CARD SETUP:

            1. Generate a QR code containing: "TEAVISION:$sizeCm"
            2. Print at exactly ${sizeCm}cm x ${sizeCm}cm
            3. Recommended: Laminate for durability
            4. Place card next to tea leaf when capturing

            Free QR generators:
            - qr-code-generator.com
            - goqr.me

            IMPORTANT: Measure printed QR code to verify exact size!
        """.trimIndent()
    }

    private fun distance(p1: PointF, p2: PointF): Float {
        val dx = p2.x - p1.x
        val dy = p2.y - p1.y
        return sqrt(dx * dx + dy * dy)
    }
}
