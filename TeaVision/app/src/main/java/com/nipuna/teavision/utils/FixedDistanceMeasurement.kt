package com.nipuna.teavision.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.RectF
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import kotlin.math.max

/**
 * Fixed Distance Measurement System
 *
 * USER-FRIENDLY APPROACH:
 * 1. User sets up a capture station (phone on stand at fixed height)
 * 2. User inputs the height ONCE in settings (e.g., 30cm)
 * 3. App calculates real measurements using camera intrinsics
 *
 * FORMULA:
 * real_size = (pixel_size × distance) / focal_length_pixels
 *
 * Where:
 * focal_length_pixels = (focal_length_mm × image_width_px) / sensor_width_mm
 */
object FixedDistanceMeasurement {

    private const val PREFS_NAME = "teavision_calibration"
    private const val KEY_DISTANCE_CM = "capture_distance_cm"
    private const val DEFAULT_DISTANCE_CM = 30f // Default 30cm

    data class CameraCalibration(
        val focalLengthMm: Float,
        val sensorWidthMm: Float,
        val sensorHeightMm: Float,
        val focalLengthPx: Float,  // Calculated for current image size
        val distanceCm: Float,
        val pixelsPerCm: Float
    )

    data class LeafDimensions(
        val widthCm: Float,
        val heightCm: Float,
        val areaCm2: Float,
        val widthPx: Float,
        val heightPx: Float,
        val areaPx: Int,
        val calibrationUsed: CameraCalibration?
    )

    /**
     * Save capture distance to preferences
     */
    fun saveDistance(context: Context, distanceCm: Float) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_DISTANCE_CM, distanceCm)
            .apply()
    }

    /**
     * Get saved capture distance
     */
    fun getDistance(context: Context): Float {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getFloat(KEY_DISTANCE_CM, DEFAULT_DISTANCE_CM)
    }

    /**
     * Check if distance has been calibrated
     */
    fun isCalibrated(context: Context): Boolean {
        return context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .contains(KEY_DISTANCE_CM)
    }

    /**
     * Get camera intrinsics and calculate calibration
     */
    fun getCalibration(context: Context, imageWidth: Int, imageHeight: Int): CameraCalibration? {
        try {
            val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager

            // Find back camera
            val cameraId = cameraManager.cameraIdList.firstOrNull { id ->
                val chars = cameraManager.getCameraCharacteristics(id)
                chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
            } ?: return null

            val characteristics = cameraManager.getCameraCharacteristics(cameraId)

            // Get focal length
            val focalLengths = characteristics.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)
            val focalLengthMm = focalLengths?.firstOrNull() ?: return null

            // Get sensor size
            val sensorSize = characteristics.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)
                ?: return null

            val sensorWidthMm = sensorSize.width
            val sensorHeightMm = sensorSize.height

            // Calculate focal length in pixels
            val focalLengthPx = (focalLengthMm * imageWidth) / sensorWidthMm

            // Get user's configured distance
            val distanceCm = getDistance(context)

            // Calculate pixels per cm at this distance
            // Formula: pixels_per_cm = focal_length_px / distance_cm
            val pixelsPerCm = focalLengthPx / distanceCm

            return CameraCalibration(
                focalLengthMm = focalLengthMm,
                sensorWidthMm = sensorWidthMm,
                sensorHeightMm = sensorHeightMm,
                focalLengthPx = focalLengthPx,
                distanceCm = distanceCm,
                pixelsPerCm = pixelsPerCm
            )
        } catch (e: Exception) {
            return null
        }
    }

    /**
     * Measure leaf dimensions using fixed distance calibration
     */
    fun measureLeaf(
        context: Context,
        bitmap: Bitmap,
        leafBounds: RectF
    ): LeafDimensions {
        val calibration = getCalibration(context, bitmap.width, bitmap.height)

        val widthPx = leafBounds.width()
        val heightPx = leafBounds.height()
        val areaPx = (widthPx * heightPx).toInt()

        return if (calibration != null && calibration.pixelsPerCm > 0) {
            // Calculate real dimensions
            val widthCm = widthPx / calibration.pixelsPerCm
            val heightCm = heightPx / calibration.pixelsPerCm
            val areaCm2 = widthCm * heightCm

            LeafDimensions(
                widthCm = widthCm,
                heightCm = heightCm,
                areaCm2 = areaCm2,
                widthPx = widthPx,
                heightPx = heightPx,
                areaPx = areaPx,
                calibrationUsed = calibration
            )
        } else {
            // No calibration - return pixel values only
            LeafDimensions(
                widthCm = 0f,
                heightCm = 0f,
                areaCm2 = 0f,
                widthPx = widthPx,
                heightPx = heightPx,
                areaPx = areaPx,
                calibrationUsed = null
            )
        }
    }

    /**
     * Get setup instructions for user
     */
    fun getSetupInstructions(): String {
        return """
            CAPTURE STATION SETUP:

            1. Set up a phone stand at a fixed height above a white surface
            2. Measure the exact distance from camera lens to surface
            3. Enter this distance in Settings (one-time setup)
            4. Place tea leaves on the white surface and capture

            TIPS:
            - Use a consistent setup for all captures
            - Recommended height: 25-35cm
            - Keep phone parallel to surface (use level indicator)
            - Use good lighting (avoid shadows)
        """.trimIndent()
    }
}
