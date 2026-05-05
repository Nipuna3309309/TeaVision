package com.nipuna.teavision

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.google.accompanist.permissions.*
import com.nipuna.teavision.composables.*
import com.nipuna.teavision.ml.LeafSegmentation
import com.nipuna.teavision.network.UploadWorker
import com.nipuna.teavision.screens.TeaAnalysisScreen
import com.nipuna.teavision.ui.theme.TeaVisionTheme
import com.nipuna.teavision.utils.FixedDistanceMeasurement
import com.nipuna.teavision.utils.ImageUtils
import com.nipuna.teavision.utils.MeasurementUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalPermissionsApi::class)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Initialize ML segmentation (loads model if available)
        LeafSegmentation.initialize(this)
        setContent { TeaVisionTheme { MainScreen() } }
    }

    override fun onDestroy() {
        super.onDestroy()
        LeafSegmentation.close()
    }
}

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun MainScreen() {
    val context = LocalContext.current
    val permission = rememberPermissionState(Manifest.permission.CAMERA)
    val scope = rememberCoroutineScope()

    var activeBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var activeMeta by remember { mutableStateOf<CaptureMetadata?>(null) }
    var activeQuality by remember { mutableStateOf<ImageUtils.QualityReport?>(null) }
    var activeMeasurement by remember { mutableStateOf<LeafMeasurementData?>(null) }
    var activeSegmentationMask by remember { mutableStateOf<Bitmap?>(null) }
    var showResults by remember { mutableStateOf(false) }
    var isProcessing by remember { mutableStateOf(false) }

    // Batch/Session management
    var currentBatchId by remember { mutableStateOf(generateBatchId()) }
    var batchImageCount by remember { mutableIntStateOf(0) }

    if (permission.status.isGranted) {
        if (showResults && activeBitmap != null && activeQuality != null) {
            TeaAnalysisScreen(
                bitmap = activeBitmap!!,
                quality = activeQuality!!,
                meta = activeMeta,
                measurement = activeMeasurement,
                segmentationMask = activeSegmentationMask,
                batchId = currentBatchId,
                batchImageIndex = batchImageCount,
                onBack = {
                    showResults = false
                    activeBitmap = null
                    activeMeasurement = null
                    activeSegmentationMask = null
                },
                onSave = { bmp ->
                    saveData(context, bmp, activeMeta, activeQuality!!, activeMeasurement, currentBatchId, batchImageCount, scope)
                    batchImageCount++
                },
                onNewBatch = {
                    currentBatchId = generateBatchId()
                    batchImageCount = 0
                }
            )
        } else {
            Box(modifier = Modifier.fillMaxSize()) {
                CameraView(
                    onImageCaptured = { rawBmp, _, meta ->
                        isProcessing = true
                        scope.launch(Dispatchers.Default) {
                            // Step 1: Quality Check (NO enhancement/upscaling)
                            val (originalBmp, quality) = ImageUtils.checkQuality(rawBmp)

                            // Step 2: Run measurement pipeline (QR calibration + segmentation)
                            var measurement: LeafMeasurementData? = null
                            var segMask: Bitmap? = null

                            try {
                                // Calibrate using QR code
                                val calibration = MeasurementUtils.calibrateFromQRCode(originalBmp)

                                // Run segmentation
                                val segResult = LeafSegmentation.segmentLeaf(
                                    originalBmp,
                                    calibration.qrBoundingBox
                                )
                                segMask = segResult.mask

                                // Calculate measurements if calibrated
                                if (calibration.success && segResult.leafBounds != null) {
                                    val measResult = MeasurementUtils.measureRegion(
                                        segResult.leafBounds,
                                        calibration.pixelsPerCm
                                    )

                                    // Analyze leaf color
                                    val colorStats = LeafSegmentation.analyzeLeafColor(originalBmp, segResult.mask)

                                    measurement = LeafMeasurementData(
                                        calibrated = true,
                                        pixelsPerCm = calibration.pixelsPerCm,
                                        qrSizeCm = calibration.qrSizeCm,
                                        leafWidthCm = measResult.widthCm,
                                        leafHeightCm = measResult.heightCm,
                                        leafAreaCm2 = measResult.areaCm2,
                                        leafAreaPixels = segResult.leafAreaPixels,
                                        leafPercentage = segResult.leafPercentage,
                                        colorGreenness = colorStats?.greenness,
                                        colorUniformity = colorStats?.uniformity,
                                        segmentationConfidence = segResult.confidence,
                                        usedMLSegmentation = segResult.usedML,
                                        measurementMessage = calibration.message
                                    )
                                } else {
                                    // Not calibrated - still show segmentation info
                                    measurement = LeafMeasurementData(
                                        calibrated = false,
                                        leafAreaPixels = segResult.leafAreaPixels,
                                        leafPercentage = segResult.leafPercentage,
                                        segmentationConfidence = segResult.confidence,
                                        usedMLSegmentation = segResult.usedML,
                                        measurementMessage = calibration.message
                                    )
                                }
                            } catch (e: Exception) {
                                // Measurement failed - continue without it
                                measurement = LeafMeasurementData(
                                    calibrated = false,
                                    measurementMessage = "Measurement error: ${e.message}"
                                )
                            }

                            withContext(Dispatchers.Main) {
                                isProcessing = false
                                if (quality.isPassed) {
                                    activeBitmap = originalBmp
                                    activeMeta = meta
                                    activeQuality = quality
                                    activeMeasurement = measurement
                                    activeSegmentationMask = segMask
                                    showResults = true
                                } else {
                                    // Show all failure reasons
                                    val reasons = quality.failureReasons.joinToString("\n")
                                    Toast.makeText(context, "REJECTED:\n$reasons", Toast.LENGTH_LONG).show()
                                }
                            }
                        }
                    },
                    onError = {
                        isProcessing = false
                        Toast.makeText(context, "Error: ${it.message}", Toast.LENGTH_SHORT).show()
                    }
                )

                // Processing overlay
                if (isProcessing) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color.Black.copy(alpha = 0.5f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator(color = Color.White)
                            Spacer(Modifier.height(16.dp))
                            Text(
                                "Analyzing image...",
                                color = Color.White
                            )
                        }
                    }
                }
            }
        }
    } else {
        Box(Modifier.fillMaxSize(), Alignment.Center) {
            Button(onClick = { permission.launchPermissionRequest() }) { Text("Allow Camera for Research") }
        }
    }
}

private fun generateBatchId(): String {
    return "BATCH_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())}"
}

fun saveData(
    ctx: Context,
    bitmap: Bitmap,
    meta: CaptureMetadata?,
    quality: ImageUtils.QualityReport,
    measurement: LeafMeasurementData?,
    batchId: String,
    imageIndex: Int,
    scope: kotlinx.coroutines.CoroutineScope
) {
    scope.launch(Dispatchers.IO) {
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val folder = "TeaVision_DataSet"
        val imageName = "TV_${batchId}_${String.format("%03d", imageIndex)}"

        // Enhanced metadata JSON with measurements
        val json = buildString {
            appendLine("{")
            appendLine("  \"filename\": \"$imageName.jpg\",")
            appendLine("  \"batch_id\": \"$batchId\",")
            appendLine("  \"image_index\": $imageIndex,")
            appendLine("  \"timestamp\": ${meta?.timestamp ?: System.currentTimeMillis()},")
            appendLine("  \"timestamp_iso\": \"${SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(Date(meta?.timestamp ?: System.currentTimeMillis()))}\",")
            appendLine("  \"device\": {")
            appendLine("    \"model\": \"${Build.MODEL}\",")
            appendLine("    \"manufacturer\": \"${Build.MANUFACTURER}\",")
            appendLine("    \"android_version\": \"${Build.VERSION.RELEASE}\",")
            appendLine("    \"sdk_level\": ${Build.VERSION.SDK_INT}")
            appendLine("  },")
            appendLine("  \"image\": {")
            appendLine("    \"width\": ${bitmap.width},")
            appendLine("    \"height\": ${bitmap.height},")
            appendLine("    \"resolution_mp\": ${String.format("%.2f", quality.resolutionMP)}")
            appendLine("  },")
            appendLine("  \"quality\": {")
            appendLine("    \"blur_score\": ${String.format("%.1f", quality.blurScore)},")
            appendLine("    \"brightness\": ${String.format("%.1f", quality.brightness)},")
            appendLine("    \"has_glare\": ${quality.hasGlare},")
            appendLine("    \"glare_percentage\": ${String.format("%.2f", quality.glarePercentage * 100)},")
            appendLine("    \"has_cluttered_background\": ${quality.hasClutteredBackground}")
            appendLine("  },")
            // Light analysis from multi-signal detection
            appendLine("  \"light_analysis\": {")
            quality.lightAnalysis?.let { light ->
                appendLine("    \"score\": ${String.format("%.1f", light.score)},")
                appendLine("    \"level\": \"${light.level}\",")
                appendLine("    \"label\": \"${light.label}\",")
                appendLine("    \"bg_brightness\": ${String.format("%.1f", light.bgBrightness)},")
                appendLine("    \"highlight_brightness\": ${String.format("%.1f", light.highlightBrightness)},")
                appendLine("    \"avg_saturation\": ${String.format("%.1f", light.avgSaturation)},")
                appendLine("    \"overexposed_pct\": ${String.format("%.1f", light.overexposedPct)},")
                appendLine("    \"underexposed_pct\": ${String.format("%.1f", light.underexposedPct)},")
                appendLine("    \"tip\": \"${light.tip}\",")
                appendLine("    \"method\": \"multi_signal\"")
            } ?: run {
                appendLine("    \"score\": 0,")
                appendLine("    \"level\": \"unknown\",")
                appendLine("    \"method\": \"none\"")
            }
            appendLine("  },")
            appendLine("  \"capture\": {")
            appendLine("    \"tilt_angle\": ${meta?.tiltAngle ?: 0f},")
            appendLine("    \"is_stable\": ${meta?.isStable ?: false},")
            appendLine("    \"white_background_pct\": ${String.format("%.2f", (meta?.whiteBackgroundPercent ?: 0f) * 100)}")
            appendLine("  },")
            // Add measurement data
            appendLine("  \"measurement\": {")
            appendLine("    \"calibrated\": ${measurement?.calibrated ?: false},")
            if (measurement?.calibrated == true) {
                appendLine("    \"pixels_per_cm\": ${String.format("%.2f", measurement.pixelsPerCm ?: 0f)},")
                appendLine("    \"qr_size_cm\": ${String.format("%.1f", measurement.qrSizeCm ?: 0f)},")
                appendLine("    \"leaf_width_cm\": ${String.format("%.2f", measurement.leafWidthCm ?: 0f)},")
                appendLine("    \"leaf_height_cm\": ${String.format("%.2f", measurement.leafHeightCm ?: 0f)},")
                appendLine("    \"leaf_area_cm2\": ${String.format("%.2f", measurement.leafAreaCm2 ?: 0f)},")
            }
            appendLine("    \"leaf_area_pixels\": ${measurement?.leafAreaPixels ?: 0},")
            appendLine("    \"leaf_percentage\": ${String.format("%.2f", measurement?.leafPercentage ?: 0f)},")
            appendLine("    \"segmentation_confidence\": ${String.format("%.2f", measurement?.segmentationConfidence ?: 0f)},")
            appendLine("    \"used_ml_segmentation\": ${measurement?.usedMLSegmentation ?: false}")
            appendLine("  },")
            // Add color analysis if available
            appendLine("  \"color_analysis\": {")
            appendLine("    \"greenness\": ${String.format("%.2f", measurement?.colorGreenness ?: 0f)},")
            appendLine("    \"uniformity\": ${String.format("%.2f", measurement?.colorUniformity ?: 0f)}")
            appendLine("  }")
            appendLine("}")
        }

        var success = false

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // Android 10+: Save image to Pictures and JSON to Documents
            val resolver = ctx.contentResolver

            // Save image to Pictures/TeaVision_DataSet/
            val imageValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, "$imageName.jpg")
                put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/$folder")
            }
            resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, imageValues)?.let { uri ->
                resolver.openOutputStream(uri)?.use {
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 95, it)
                }
            }

            // Save JSON to Documents/TeaVision_DataSet/
            val jsonValues = ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, "$imageName.json")
                put(MediaStore.MediaColumns.MIME_TYPE, "application/json")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "Documents/$folder")
            }
            resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, jsonValues)?.let { uri ->
                resolver.openOutputStream(uri)?.use {
                    it.write(json.toByteArray())
                }
                success = true
            }
        } else {
            // Android 9 and below: Direct file access
            val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), folder)
            if (!dir.exists()) dir.mkdirs()

            FileOutputStream(File(dir, "$imageName.jpg")).use {
                bitmap.compress(Bitmap.CompressFormat.JPEG, 95, it)
            }
            FileOutputStream(File(dir, "$imageName.json")).use {
                it.write(json.toByteArray())
            }
            success = true
        }

        withContext(Dispatchers.Main) {
            if (success) {
                Toast.makeText(ctx, "Saved: $imageName\n(Image + JSON)", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(ctx, "Failed to save metadata", Toast.LENGTH_SHORT).show()
            }
        }

        // Best-effort upload to server (local save is primary, never lose data)
        if (success) {
            try {
                val uploaded = UploadWorker.uploadToServer(bitmap, json, imageName)
                withContext(Dispatchers.Main) {
                    if (uploaded) {
                        Toast.makeText(ctx, "Uploaded to server", Toast.LENGTH_SHORT).show()
                    }
                    // Silent on failure - local save already succeeded
                }
            } catch (_: Exception) {
                // Server upload is best-effort; ignore errors
            }
        }
    }
}
