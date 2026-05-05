package com.nipuna.teavision.utils

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PointF
import android.hardware.camera2.CameraCharacteristics
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Reference Marker Detection for Distance Estimation
 *
 * RESEARCH METHODOLOGY:
 * This implementation uses the pinhole camera model for distance estimation
 * based on a known-size reference object (ruler/scale bar).
 *
 * PINHOLE CAMERA MODEL:
 * Distance = (Real_Object_Length × Focal_Length_Pixels) / Object_Length_Pixels
 *
 * RULER DETECTION STRATEGY:
 * Instead of generic edge detection (which fails with cluttered backgrounds),
 * we specifically look for ruler characteristics:
 * 1. High-contrast dark markings (numbers, tick marks)
 * 2. Linear arrangement of periodic features
 * 3. Hough transform to find dominant lines through dark marks
 *
 * REFERENCES:
 * - Hartley & Zisserman (2004). Multiple View Geometry in Computer Vision
 * - Duda, R. O., & Hart, P. E. (1972). Use of the Hough transformation
 */
object ReferenceMarkerDetector {

    private const val MIN_RULER_LENGTH_RATIO = 0.15f
    private const val MAX_RULER_LENGTH_RATIO = 0.95f

    data class DetectionResult(
        val detected: Boolean,
        val distanceMeters: Float?,
        val confidence: Float,
        val rulerPixelLength: Float?,
        val rulerEndpoints: Pair<PointF, PointF>?,
        val message: String
    )

    data class CameraIntrinsics(
        val focalLengthMm: Float,
        val sensorWidthMm: Float,
        val sensorHeightMm: Float,
        val imageWidthPx: Int,
        val imageHeightPx: Int
    ) {
        val focalLengthPixels: Float
            get() = focalLengthMm * (imageWidthPx / sensorWidthMm)
    }

    fun extractCameraIntrinsics(
        characteristics: CameraCharacteristics,
        imageWidth: Int,
        imageHeight: Int
    ): CameraIntrinsics? {
        return try {
            val focalLengths = characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
            val sensorSize = characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)

            if (focalLengths != null && focalLengths.isNotEmpty() && sensorSize != null) {
                CameraIntrinsics(
                    focalLengthMm = focalLengths[0],
                    sensorWidthMm = sensorSize.width,
                    sensorHeightMm = sensorSize.height,
                    imageWidthPx = imageWidth,
                    imageHeightPx = imageHeight
                )
            } else null
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Detect ruler using dark marking detection + Hough line transform
     * Works better with cluttered backgrounds by focusing on ruler-specific features
     */
    fun detectRulerAndCalculateDistance(
        bitmap: Bitmap,
        intrinsics: CameraIntrinsics,
        rulerLengthCm: Float
    ): DetectionResult {
        // Step 1: Resize for processing
        val scale = 600f / max(bitmap.width, bitmap.height)
        val scaledWidth = (bitmap.width * scale).toInt()
        val scaledHeight = (bitmap.height * scale).toInt()
        val scaled = Bitmap.createScaledBitmap(bitmap, scaledWidth, scaledHeight, true)

        // Step 2: Extract grayscale and find dark markings (ruler numbers/ticks)
        val pixels = IntArray(scaledWidth * scaledHeight)
        scaled.getPixels(pixels, 0, scaledWidth, 0, 0, scaledWidth, scaledHeight)

        val grayscale = IntArray(pixels.size)
        for (i in pixels.indices) {
            val r = Color.red(pixels[i])
            val g = Color.green(pixels[i])
            val b = Color.blue(pixels[i])
            grayscale[i] = (0.299 * r + 0.587 * g + 0.114 * b).toInt()
        }

        // Step 3: Detect dark marks using adaptive thresholding
        // This finds the ruler's printed numbers and tick marks
        val darkMarks = detectDarkMarksAdaptive(grayscale, scaledWidth, scaledHeight)

        // Step 4: Use Hough transform to find lines through dark marks
        val rulerLine = houghLineFindRuler(darkMarks, scaledWidth, scaledHeight)

        if (rulerLine == null) {
            return DetectionResult(
                detected = false,
                distanceMeters = null,
                confidence = 0f,
                rulerPixelLength = null,
                rulerEndpoints = null,
                message = "No ruler detected. Place ruler with visible markings."
            )
        }

        // Step 5: Refine endpoints by finding extent of dark marks along the line
        val refinedLine = refineRulerEndpoints(darkMarks, rulerLine, scaledWidth, scaledHeight)
        val (p1Scaled, p2Scaled) = refinedLine

        val pixelLengthScaled = distance(p1Scaled, p2Scaled)
        val pixelLength = pixelLengthScaled / scale

        // Validate
        val minLength = intrinsics.imageWidthPx * MIN_RULER_LENGTH_RATIO
        val maxLength = intrinsics.imageWidthPx * MAX_RULER_LENGTH_RATIO

        if (pixelLength < minLength) {
            return DetectionResult(
                detected = false,
                distanceMeters = null,
                confidence = 0f,
                rulerPixelLength = pixelLength,
                rulerEndpoints = Pair(
                    PointF(p1Scaled.x / scale, p1Scaled.y / scale),
                    PointF(p2Scaled.x / scale, p2Scaled.y / scale)
                ),
                message = "Ruler too small. Move closer."
            )
        }

        if (pixelLength > maxLength) {
            return DetectionResult(
                detected = false,
                distanceMeters = null,
                confidence = 0f,
                rulerPixelLength = pixelLength,
                rulerEndpoints = Pair(
                    PointF(p1Scaled.x / scale, p1Scaled.y / scale),
                    PointF(p2Scaled.x / scale, p2Scaled.y / scale)
                ),
                message = "Ruler too large. Move back."
            )
        }

        // Step 6: Calculate distance
        val rulerLengthMeters = rulerLengthCm / 100f
        val distanceMeters = (rulerLengthMeters * intrinsics.focalLengthPixels) / pixelLength

        // Confidence based on number of dark marks found along line
        val confidence = calculateLineConfidence(darkMarks, refinedLine, scaledWidth)

        val endpoints = Pair(
            PointF(p1Scaled.x / scale, p1Scaled.y / scale),
            PointF(p2Scaled.x / scale, p2Scaled.y / scale)
        )

        return DetectionResult(
            detected = true,
            distanceMeters = distanceMeters,
            confidence = confidence,
            rulerPixelLength = pixelLength,
            rulerEndpoints = endpoints,
            message = "Ruler: ${rulerLengthCm.toInt()}cm → ${String.format("%.0f", distanceMeters * 100)}cm"
        )
    }

    /**
     * Adaptive dark mark detection
     * Finds pixels significantly darker than their local neighborhood
     * This detects ruler numbers and tick marks even on textured backgrounds
     */
    private fun detectDarkMarksAdaptive(
        grayscale: IntArray,
        width: Int,
        height: Int
    ): IntArray {
        val result = IntArray(grayscale.size)
        val windowSize = 25  // Local window for comparison
        val halfWindow = windowSize / 2
        val darkThreshold = 30  // How much darker than local average

        // First pass: compute integral image for fast local mean calculation
        val integral = LongArray(grayscale.size)
        for (y in 0 until height) {
            var rowSum = 0L
            for (x in 0 until width) {
                val i = y * width + x
                rowSum += grayscale[i]
                integral[i] = rowSum + if (y > 0) integral[(y - 1) * width + x] else 0L
            }
        }

        // Second pass: find pixels darker than local mean
        for (y in halfWindow until height - halfWindow) {
            for (x in halfWindow until width - halfWindow) {
                val i = y * width + x

                // Calculate local mean using integral image
                val x1 = x - halfWindow
                val y1 = y - halfWindow
                val x2 = x + halfWindow
                val y2 = y + halfWindow

                val sum = integral[y2 * width + x2] -
                        (if (x1 > 0) integral[y2 * width + x1 - 1] else 0L) -
                        (if (y1 > 0) integral[(y1 - 1) * width + x2] else 0L) +
                        (if (x1 > 0 && y1 > 0) integral[(y1 - 1) * width + x1 - 1] else 0L)

                val localMean = sum / (windowSize * windowSize)

                // Mark as dark if significantly below local mean
                if (grayscale[i] < localMean - darkThreshold) {
                    result[i] = 255
                }
            }
        }

        // Morphological cleanup - remove isolated noise
        return morphologicalClean(result, width, height)
    }

    /**
     * Remove isolated pixels (noise) using morphological opening
     */
    private fun morphologicalClean(binary: IntArray, width: Int, height: Int): IntArray {
        val result = IntArray(binary.size)

        // Erosion then dilation (opening)
        for (y in 1 until height - 1) {
            for (x in 1 until width - 1) {
                val i = y * width + x

                // Count neighbors
                var neighbors = 0
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        if (binary[(y + dy) * width + (x + dx)] > 0) neighbors++
                    }
                }

                // Keep only if has enough neighbors (part of a cluster)
                result[i] = if (neighbors >= 4) 255 else 0
            }
        }

        return result
    }

    /**
     * Hough line transform to find the dominant line through dark marks
     * Specifically tuned for ruler detection
     */
    private fun houghLineFindRuler(
        darkMarks: IntArray,
        width: Int,
        height: Int
    ): Pair<PointF, PointF>? {
        // Collect dark mark points
        val points = mutableListOf<PointF>()
        for (y in 0 until height) {
            for (x in 0 until width) {
                if (darkMarks[y * width + x] > 0) {
                    points.add(PointF(x.toFloat(), y.toFloat()))
                }
            }
        }

        if (points.size < 30) return null

        // Hough accumulator
        // rho: distance from origin, theta: angle
        val numTheta = 180
        val maxRho = sqrt((width * width + height * height).toDouble()).toInt()
        val accumulator = Array(2 * maxRho) { IntArray(numTheta) }

        // Vote for each point
        for (p in points) {
            for (thetaIdx in 0 until numTheta) {
                val theta = Math.PI * thetaIdx / numTheta
                val rho = (p.x * cos(theta) + p.y * sin(theta)).roundToInt() + maxRho
                if (rho in 0 until 2 * maxRho) {
                    accumulator[rho][thetaIdx]++
                }
            }
        }

        // Find peak (most voted line)
        var maxVotes = 0
        var bestRho = 0
        var bestTheta = 0

        for (rho in 0 until 2 * maxRho) {
            for (theta in 0 until numTheta) {
                if (accumulator[rho][theta] > maxVotes) {
                    maxVotes = accumulator[rho][theta]
                    bestRho = rho
                    bestTheta = theta
                }
            }
        }

        // Need minimum votes (at least 10% of dark points should be on the line)
        if (maxVotes < points.size * 0.08) return null

        // Convert back to line parameters
        val theta = Math.PI * bestTheta / numTheta
        val rho = (bestRho - maxRho).toDouble()

        // Find line endpoints within image bounds
        return lineFromRhoTheta(rho, theta, width, height)
    }

    /**
     * Convert Hough (rho, theta) to line endpoints
     */
    private fun lineFromRhoTheta(
        rho: Double,
        theta: Double,
        width: Int,
        height: Int
    ): Pair<PointF, PointF>? {
        val cosT = cos(theta)
        val sinT = sin(theta)

        val intersections = mutableListOf<PointF>()

        // Check intersection with all 4 image boundaries
        // Top edge (y = 0)
        if (abs(sinT) > 0.001) {
            val x = rho / cosT
            if (x >= 0 && x < width) {
                intersections.add(PointF(x.toFloat(), 0f))
            }
        }

        // Bottom edge (y = height-1)
        if (abs(sinT) > 0.001) {
            val x = (rho - (height - 1) * sinT) / cosT
            if (x >= 0 && x < width) {
                intersections.add(PointF(x.toFloat(), (height - 1).toFloat()))
            }
        }

        // Left edge (x = 0)
        if (abs(cosT) > 0.001) {
            val y = rho / sinT
            if (y >= 0 && y < height) {
                intersections.add(PointF(0f, y.toFloat()))
            }
        }

        // Right edge (x = width-1)
        if (abs(cosT) > 0.001) {
            val y = (rho - (width - 1) * cosT) / sinT
            if (y >= 0 && y < height) {
                intersections.add(PointF((width - 1).toFloat(), y.toFloat()))
            }
        }

        // Return two furthest intersection points
        if (intersections.size < 2) return null

        var maxDist = 0f
        var p1 = intersections[0]
        var p2 = intersections[1]

        for (i in intersections.indices) {
            for (j in i + 1 until intersections.size) {
                val d = distance(intersections[i], intersections[j])
                if (d > maxDist) {
                    maxDist = d
                    p1 = intersections[i]
                    p2 = intersections[j]
                }
            }
        }

        return Pair(p1, p2)
    }

    /**
     * Refine ruler endpoints by finding the actual extent of marks along the line
     */
    private fun refineRulerEndpoints(
        darkMarks: IntArray,
        line: Pair<PointF, PointF>,
        width: Int,
        height: Int
    ): Pair<PointF, PointF> {
        val (p1, p2) = line
        val lineAngle = atan2((p2.y - p1.y).toDouble(), (p2.x - p1.x).toDouble())

        // Find all dark points near the line
        val nearLinePoints = mutableListOf<PointF>()
        val tolerance = 15f  // Pixels from line

        for (y in 0 until height) {
            for (x in 0 until width) {
                if (darkMarks[y * width + x] > 0) {
                    val point = PointF(x.toFloat(), y.toFloat())
                    val dist = pointToLineDistance(point, p1, p2)
                    if (dist < tolerance) {
                        nearLinePoints.add(point)
                    }
                }
            }
        }

        if (nearLinePoints.size < 10) return line

        // Project points onto line direction and find extremes
        val cosA = cos(lineAngle).toFloat()
        val sinA = sin(lineAngle).toFloat()

        var minProj = Float.MAX_VALUE
        var maxProj = Float.MIN_VALUE
        var minPoint = nearLinePoints[0]
        var maxPoint = nearLinePoints[0]

        for (p in nearLinePoints) {
            // Project onto line direction from p1
            val proj = (p.x - p1.x) * cosA + (p.y - p1.y) * sinA
            if (proj < minProj) {
                minProj = proj
                minPoint = p
            }
            if (proj > maxProj) {
                maxProj = proj
                maxPoint = p
            }
        }

        return Pair(minPoint, maxPoint)
    }

    /**
     * Distance from point to line
     */
    private fun pointToLineDistance(point: PointF, lineP1: PointF, lineP2: PointF): Float {
        val lineLen = distance(lineP1, lineP2)
        if (lineLen < 0.001f) return distance(point, lineP1)

        return abs(
            (lineP2.y - lineP1.y) * point.x -
                    (lineP2.x - lineP1.x) * point.y +
                    lineP2.x * lineP1.y -
                    lineP2.y * lineP1.x
        ) / lineLen
    }

    /**
     * Calculate confidence based on mark density along line
     */
    private fun calculateLineConfidence(
        darkMarks: IntArray,
        line: Pair<PointF, PointF>,
        width: Int
    ): Float {
        val (p1, p2) = line
        val length = distance(p1, p2)
        val steps = length.toInt()

        var marksOnLine = 0
        for (i in 0..steps) {
            val t = i.toFloat() / steps
            val x = (p1.x + t * (p2.x - p1.x)).toInt()
            val y = (p1.y + t * (p2.y - p1.y)).toInt()

            if (x in 0 until width && y >= 0) {
                val idx = y * width + x
                if (idx < darkMarks.size && darkMarks[idx] > 0) {
                    marksOnLine++
                }
            }
        }

        // Ruler should have marks covering ~20-40% of its length
        val coverage = marksOnLine.toFloat() / steps
        return min(1f, coverage * 3f)  // Scale up, cap at 1
    }

    private fun distance(p1: PointF, p2: PointF): Float {
        val dx = p2.x - p1.x
        val dy = p2.y - p1.y
        return sqrt(dx * dx + dy * dy)
    }
}
