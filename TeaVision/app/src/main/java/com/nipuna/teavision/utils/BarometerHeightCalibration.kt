package com.nipuna.teavision.utils

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlin.math.abs
import kotlin.math.pow

/**
 * Barometer-based Height Calibration
 *
 * HOW IT WORKS:
 * 1. User places phone on floor and presses "Set Floor"
 * 2. App records the air pressure at floor level
 * 3. User lifts phone to capture position
 * 4. App calculates height difference from pressure change
 *
 * PHYSICS:
 * - Air pressure decreases ~0.12 hPa per meter of altitude
 * - Formula: height_meters = 44330 * (1 - (P/P0)^0.1903)
 * - For small heights: height_cm ≈ (P0 - P) * 843
 *
 * ACCURACY:
 * - Phone barometers have ~0.01 hPa resolution
 * - This gives ~8cm resolution for height measurements
 * - Good enough for rough calibration (25-50cm range)
 */
object BarometerHeightCalibration {

    private const val PREFS_NAME = "teavision_barometer_cal"
    private const val KEY_FLOOR_PRESSURE = "floor_pressure_hpa"

    // Conversion factor: hPa to cm (approximately 843 cm per hPa at sea level)
    private const val HPA_TO_CM = 843f

    data class PressureReading(
        val pressureHpa: Float,
        val isStable: Boolean,
        val stabilityScore: Float // 0-1, higher = more stable
    )

    data class HeightResult(
        val heightCm: Float,
        val floorPressure: Float,
        val currentPressure: Float,
        val confidence: Float // 0-1 based on stability
    )

    /**
     * Check if device has a barometer sensor
     */
    fun hasBarometer(context: Context): Boolean {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        return sensorManager.getDefaultSensor(Sensor.TYPE_PRESSURE) != null
    }

    /**
     * Get barometer pressure as a Flow (for real-time updates)
     */
    fun getPressureFlow(context: Context): Flow<PressureReading> = callbackFlow {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val barometer = sensorManager.getDefaultSensor(Sensor.TYPE_PRESSURE)

        if (barometer == null) {
            close(IllegalStateException("No barometer sensor available"))
            return@callbackFlow
        }

        // Track recent readings for stability detection
        val recentReadings = mutableListOf<Float>()
        val maxReadings = 10

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                event?.let {
                    val pressure = it.values[0]

                    // Add to recent readings
                    recentReadings.add(pressure)
                    if (recentReadings.size > maxReadings) {
                        recentReadings.removeAt(0)
                    }

                    // Calculate stability (standard deviation of recent readings)
                    val stability = if (recentReadings.size >= 5) {
                        val avg = recentReadings.average().toFloat()
                        val variance = recentReadings.map { r -> (r - avg).pow(2) }.average().toFloat()
                        val stdDev = kotlin.math.sqrt(variance)
                        // Convert to 0-1 score (lower stdDev = higher stability)
                        // 0.01 hPa stdDev = 1.0 stability, 0.1 hPa = 0 stability
                        (1f - (stdDev / 0.1f)).coerceIn(0f, 1f)
                    } else {
                        0f
                    }

                    val isStable = stability > 0.7f && recentReadings.size >= 5

                    trySend(PressureReading(
                        pressureHpa = pressure,
                        isStable = isStable,
                        stabilityScore = stability
                    ))
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }

        sensorManager.registerListener(
            listener,
            barometer,
            SensorManager.SENSOR_DELAY_UI
        )

        awaitClose {
            sensorManager.unregisterListener(listener)
        }
    }

    /**
     * Save the floor pressure reference
     */
    fun saveFloorPressure(context: Context, pressureHpa: Float) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_FLOOR_PRESSURE, pressureHpa)
            .apply()
    }

    /**
     * Get saved floor pressure
     */
    fun getFloorPressure(context: Context): Float? {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return if (prefs.contains(KEY_FLOOR_PRESSURE)) {
            prefs.getFloat(KEY_FLOOR_PRESSURE, 0f)
        } else {
            null
        }
    }

    /**
     * Clear floor pressure calibration
     */
    fun clearFloorPressure(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(KEY_FLOOR_PRESSURE)
            .apply()
    }

    /**
     * Calculate height from floor based on current pressure
     */
    fun calculateHeight(floorPressure: Float, currentPressure: Float): Float {
        // Pressure decreases as altitude increases
        // Simple linear approximation for small heights:
        // height_cm = (P_floor - P_current) * 843
        val pressureDiff = floorPressure - currentPressure
        return pressureDiff * HPA_TO_CM
    }

    /**
     * Calculate height with full result details
     */
    fun calculateHeightResult(
        context: Context,
        currentPressure: Float,
        stabilityScore: Float
    ): HeightResult? {
        val floorPressure = getFloorPressure(context) ?: return null
        val heightCm = calculateHeight(floorPressure, currentPressure)

        return HeightResult(
            heightCm = heightCm,
            floorPressure = floorPressure,
            currentPressure = currentPressure,
            confidence = stabilityScore
        )
    }

    /**
     * Check if floor pressure has been calibrated
     */
    fun hasFloorCalibration(context: Context): Boolean {
        return getFloorPressure(context) != null
    }
}
