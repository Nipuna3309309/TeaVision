package com.nipuna.teavision.composables

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
import android.util.Size
import android.view.ViewGroup
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.AspectRatioStrategy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.Camera
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size as ComposeSize
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.nio.ByteBuffer
import java.util.concurrent.Executors
import kotlin.math.abs
import kotlin.math.sqrt

private const val WHITE_LUMA_THRESHOLD = 180
private const val MIN_WHITE_RATIO = 0.40f
private const val INNER_ROI_FRACTION = 0.60f

data class MpOption(val label: String, val size: Size) {
    val mp: Float = (size.width * size.height) / 1_000_000f
}

/**
 * Query actual camera resolutions supported by the device
 */
fun getAvailableResolutions(context: Context): List<MpOption> {
    val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    val resolutions = mutableListOf<MpOption>()

    try {
        // Get back camera
        val cameraId = cameraManager.cameraIdList.firstOrNull { id ->
            val characteristics = cameraManager.getCameraCharacteristics(id)
            characteristics.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
        } ?: return getDefaultResolutions()

        val characteristics = cameraManager.getCameraCharacteristics(cameraId)
        val streamConfigMap = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
            ?: return getDefaultResolutions()

        // Get JPEG output sizes (highest quality capture)
        val outputSizes = streamConfigMap.getOutputSizes(ImageFormat.JPEG)
            ?.sortedByDescending { it.width * it.height }
            ?: return getDefaultResolutions()

        // Select meaningful resolutions (highest, then ~8MP, ~5MP, ~2MP)
        val targetMps = listOf(999f, 12f, 8f, 5f, 2f) // 999 = highest available

        for (targetMp in targetMps) {
            val bestMatch = if (targetMp > 100f) {
                // Highest available
                outputSizes.firstOrNull()
            } else {
                // Find closest to target MP
                outputSizes.minByOrNull {
                    val mp = (it.width * it.height) / 1_000_000f
                    abs(mp - targetMp)
                }
            }

            bestMatch?.let { size ->
                val mp = (size.width * size.height) / 1_000_000f
                val label = when {
                    mp >= 10 -> "${mp.toInt()}MP"
                    mp >= 1 -> "${String.format("%.1f", mp)}MP"
                    else -> "${(mp * 1000).toInt()}K"
                }
                // Avoid duplicates
                if (resolutions.none { it.size == size }) {
                    resolutions.add(MpOption(label, size))
                }
            }
        }
    } catch (e: Exception) {
        return getDefaultResolutions()
    }

    return resolutions.ifEmpty { getDefaultResolutions() }
}

private fun getDefaultResolutions(): List<MpOption> {
    return listOf(
        MpOption("12MP", Size(4032, 3024)),
        MpOption("8MP", Size(3264, 2448)),
        MpOption("5MP", Size(2592, 1944)),
        MpOption("2MP", Size(1920, 1080))
    )
}

data class CaptureMetadata(
    val tiltAngle: Float,
    val isStable: Boolean,
    val whiteBackgroundPercent: Float,
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * Extended metadata including measurements
 */
data class LeafMeasurementData(
    val calibrated: Boolean = false,
    val pixelsPerCm: Float? = null,
    val qrSizeCm: Float? = null,
    val leafWidthCm: Float? = null,
    val leafHeightCm: Float? = null,
    val leafAreaCm2: Float? = null,
    val leafAreaPixels: Int? = null,
    val leafPercentage: Float? = null,
    val colorGreenness: Float? = null,
    val colorUniformity: Float? = null,
    val segmentationConfidence: Float? = null,
    val usedMLSegmentation: Boolean = false,
    val measurementMessage: String? = null
)

@Composable
fun CameraView(
    onImageCaptured: (Bitmap, Uri, CaptureMetadata) -> Unit,
    onError: (Exception) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()

    // Sensors (tilt + stability)
    var isLevel by remember { mutableStateOf(false) }
    var isStable by remember { mutableStateOf(false) }
    var currentTilt by remember { mutableStateOf(0f) }

    // Background light detection
    var whiteBackgroundPercent by remember { mutableFloatStateOf(0f) }
    val isBackgroundValid = whiteBackgroundPercent >= MIN_WHITE_RATIO

    // MP selection - query ACTUAL device-supported resolutions
    val mpOptions = remember { getAvailableResolutions(context) }
    var selectedMp by remember { mutableStateOf(mpOptions.firstOrNull() ?: MpOption("Default", Size(1920, 1080))) }
    var showMpMenu by remember { mutableStateOf(false) }

    // Camera state
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    var isProcessing by remember { mutableStateOf(false) }

    // --- SENSOR LOGIC (Accelerometer for tilt + stability) ---
    DisposableEffect(Unit) {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

        var lastX = 0f; var lastY = 0f; var lastZ = 0f

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                event?.let {
                    val x = it.values[0]; val y = it.values[1]; val z = it.values[2]

                    // Tilt calculation
                    val g = sqrt(x * x + y * y + z * z)
                    val tilt = Math.toDegrees(Math.acos((z / g).toDouble())).toFloat()
                    currentTilt = tilt
                    isLevel = tilt < 15 // Tolerance: 15 degrees from flat

                    // Stability (Motion detection)
                    val delta = abs(x - lastX) + abs(y - lastY) + abs(z - lastZ)
                    isStable = delta < 0.5f // Must hold still

                    lastX = x; lastY = y; lastZ = z
                }
            }
            override fun onAccuracyChanged(s: Sensor?, a: Int) {}
        }
        sensorManager.registerListener(listener, accelerometer, SensorManager.SENSOR_DELAY_UI)
        onDispose { sensorManager.unregisterListener(listener) }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        // 1. CameraX Preview
        key(selectedMp) {
            AndroidView(
                factory = { ctx ->
                    val previewView = PreviewView(ctx).apply {
                        layoutParams = ViewGroup.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT
                        )
                        scaleType = PreviewView.ScaleType.FILL_CENTER
                    }

                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
                    cameraProviderFuture.addListener({
                        val cameraProvider = cameraProviderFuture.get()

                        val preview = Preview.Builder().build().also {
                            it.setSurfaceProvider(previewView.surfaceProvider)
                        }

                        // Use ResolutionSelector for exact resolution control
                        val resolutionSelector = ResolutionSelector.Builder()
                            .setResolutionStrategy(
                                ResolutionStrategy(
                                    selectedMp.size,
                                    ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER
                                )
                            )
                            .setAspectRatioStrategy(AspectRatioStrategy.RATIO_4_3_FALLBACK_AUTO_STRATEGY)
                            .build()

                        val imgCapture = ImageCapture.Builder()
                            .setResolutionSelector(resolutionSelector)
                            .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                            .build()
                        imageCapture = imgCapture

                        // Image analysis for light background detection
                        val analysisExecutor = Executors.newSingleThreadExecutor()
                        val analysisResolutionSelector = ResolutionSelector.Builder()
                            .setResolutionStrategy(
                                ResolutionStrategy(
                                    Size(1280, 960), // Lower res for analysis (faster)
                                    ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER
                                )
                            )
                            .build()

                        val imageAnalysis = ImageAnalysis.Builder()
                            .setResolutionSelector(analysisResolutionSelector)
                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                            .build()
                            .also { analysis ->
                                analysis.setAnalyzer(analysisExecutor) { imageProxy ->
                                    val ratio = calculateWhiteRatio(imageProxy)
                                    coroutineScope.launch(Dispatchers.Main) {
                                        whiteBackgroundPercent = ratio
                                    }
                                    imageProxy.close()
                                }
                            }

                        val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                        try {
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(
                                lifecycleOwner,
                                cameraSelector,
                                preview,
                                imgCapture,
                                imageAnalysis
                            )
                        } catch (e: Exception) {
                            onError(e)
                        }
                    }, ContextCompat.getMainExecutor(ctx))

                    previewView
                },
                modifier = Modifier.fillMaxSize()
            )
        }

        // 2. Research Overlay
        ResearchOverlay(
            isLevel = isLevel,
            isStable = isStable,
            tilt = currentTilt,
            whiteBackgroundPercent = whiteBackgroundPercent,
            isBackgroundValid = isBackgroundValid
        )

        // 3. Calibration button (top left)
        var showCalibrationDialog by remember { mutableStateOf(false) }
        val isCalibrated = remember {
            com.nipuna.teavision.utils.FixedDistanceMeasurement.isCalibrated(context)
        }
        var calibrationState by remember { mutableStateOf(isCalibrated) }

        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(16.dp)
        ) {
            CalibrationButton(
                isCalibrated = calibrationState,
                onClick = { showCalibrationDialog = true }
            )
        }

        if (showCalibrationDialog) {
            CalibrationDialog(
                onDismiss = { showCalibrationDialog = false },
                onSave = { distance ->
                    com.nipuna.teavision.utils.FixedDistanceMeasurement.saveDistance(context, distance)
                    calibrationState = true
                    showCalibrationDialog = false
                }
            )
        }

        // 4. MP selector (top right)
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier
                    .background(Color.Black.copy(0.8f), MaterialTheme.shapes.medium)
                    .clickable { showMpMenu = true }
                    .padding(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = selectedMp.label,
                    color = Color.White,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold
                )
                Icon(
                    Icons.Default.ArrowDropDown,
                    contentDescription = "Select MP",
                    tint = Color.White
                )
            }
            DropdownMenu(
                expanded = showMpMenu,
                onDismissRequest = { showMpMenu = false }
            ) {
                mpOptions.forEach { option ->
                    DropdownMenuItem(
                        text = { Text("${option.label} (${String.format("%.1f", option.mp)} MP)") },
                        onClick = {
                            selectedMp = option
                            showMpMenu = false
                        }
                    )
                }
            }
        }

        // 4. Capture resolution info (bottom right)
        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp)
                .background(Color.Black.copy(0.8f), MaterialTheme.shapes.medium)
                .padding(12.dp)
        ) {
            Column {
                Text(
                    text = "Capture: ${selectedMp.size.width}x${selectedMp.size.height}",
                    color = Color.White,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "(${String.format("%.1f", selectedMp.mp)} MP)",
                    color = Color.White.copy(0.7f),
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }

        // 5. Capture Button
        val isReady = isLevel && isStable && isBackgroundValid && !isProcessing

        FloatingActionButton(
            onClick = {
                if (isReady && imageCapture != null) {
                    isProcessing = true
                    val metadata = CaptureMetadata(
                        tiltAngle = currentTilt,
                        isStable = isStable,
                        whiteBackgroundPercent = whiteBackgroundPercent
                    )

                    imageCapture?.takePicture(
                        ContextCompat.getMainExecutor(context),
                        object : ImageCapture.OnImageCapturedCallback() {
                            override fun onCaptureSuccess(image: ImageProxy) {
                                coroutineScope.launch(Dispatchers.IO) {
                                    try {
                                        val bitmap = imageProxyToBitmap(image)
                                        image.close()

                                        val file = File.createTempFile("tv_temp", ".jpg", context.cacheDir)
                                        file.outputStream().use {
                                            bitmap.compress(Bitmap.CompressFormat.JPEG, 95, it)
                                        }

                                        withContext(Dispatchers.Main) {
                                            isProcessing = false
                                            onImageCaptured(bitmap, Uri.fromFile(file), metadata)
                                        }
                                    } catch (e: Exception) {
                                        withContext(Dispatchers.Main) {
                                            isProcessing = false
                                            onError(e)
                                        }
                                    }
                                }
                            }

                            override fun onError(exception: ImageCaptureException) {
                                isProcessing = false
                                onError(exception)
                            }
                        }
                    )
                }
            },
            containerColor = if (isReady) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(32.dp)
                .size(80.dp)
        ) {
            if (isProcessing) {
                CircularProgressIndicator(color = Color.White)
            } else {
                Icon(
                    imageVector = if (isReady) Icons.Filled.Camera else Icons.Filled.Block,
                    contentDescription = "Capture",
                    tint = Color.White,
                    modifier = Modifier.size(32.dp)
                )
            }
        }
    }
}

@Composable
fun ResearchOverlay(
    isLevel: Boolean,
    isStable: Boolean,
    tilt: Float,
    whiteBackgroundPercent: Float,
    isBackgroundValid: Boolean
) {
    val statusText = when {
        !isLevel -> "TILTED! (${tilt.toInt()}deg)"
        !isStable -> "HOLD STILL!"
        !isBackgroundValid -> "LIGHT BACKGROUND"
        else -> "READY"
    }

    val statusColor = when {
        !isLevel || !isStable -> Color.Red
        !isBackgroundValid -> Color(0xFFFFC107)
        else -> Color.Green
    }

    Box(modifier = Modifier.fillMaxSize()) {
        // Frame guide + light ROI debug
        Canvas(modifier = Modifier.fillMaxSize()) {
            val boxW = size.width * 0.7f
            val boxH = size.height * 0.5f
            drawRoundRect(
                color = statusColor,
                topLeft = Offset((size.width - boxW) / 2, (size.height - boxH) / 2),
                size = ComposeSize(boxW, boxH),
                cornerRadius = CornerRadius(32f),
                style = Stroke(width = 8f)
            )

            // Donut ROI: sample outside the inner box (center is excluded)
            val roiW = size.width * INNER_ROI_FRACTION
            val roiH = size.height * INNER_ROI_FRACTION
            drawRect(
                color = Color.White.copy(alpha = 0.7f),
                topLeft = Offset(0f, 0f),
                size = ComposeSize(size.width, size.height),
                style = Stroke(width = 3f)
            )
            drawRect(
                color = Color.Red.copy(alpha = 0.7f),
                topLeft = Offset((size.width - roiW) / 2, (size.height - roiH) / 2),
                size = ComposeSize(roiW, roiH),
                style = Stroke(width = 3f)
            )
        }

        // Status text
        Text(
            text = statusText,
            color = statusColor,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Black,
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 80.dp)
                .background(Color.Black.copy(0.7f), MaterialTheme.shapes.medium)
                .padding(16.dp)
        )

        // Tilt/Stability indicator
        Column(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(16.dp)
                .background(Color.Black.copy(0.7f), MaterialTheme.shapes.medium)
                .padding(12.dp)
        ) {
            Text(
                text = "Tilt: ${tilt.toInt()}deg",
                color = if (isLevel) Color.Green else Color.Red,
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = if (isLevel) "Level OK" else "Keep flat!",
                color = if (isLevel) Color.Green else Color.Red,
                style = MaterialTheme.typography.bodySmall
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = if (isStable) "Stable" else "Hold still!",
                color = if (isStable) Color.Green else Color.Red,
                style = MaterialTheme.typography.bodySmall
            )
            Spacer(Modifier.height(4.dp))
            val bgPct = (whiteBackgroundPercent * 100).toInt()
            Text(
                text = "Background: ${bgPct}% light",
                color = if (isBackgroundValid) Color.Green else Color(0xFFFFC107),
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

private fun calculateWhiteRatio(imageProxy: ImageProxy): Float {
    val plane = imageProxy.planes[0]
    val buffer = plane.buffer
    val rowStride = plane.rowStride
    val pixelStride = plane.pixelStride
    val width = imageProxy.width
    val height = imageProxy.height

    val innerWidth = (width * INNER_ROI_FRACTION).toInt()
    val innerHeight = (height * INNER_ROI_FRACTION).toInt()
    val innerStartX = (width - innerWidth) / 2
    val innerStartY = (height - innerHeight) / 2
    val innerEndX = innerStartX + innerWidth
    val innerEndY = innerStartY + innerHeight

    var white = 0
    var total = 0

    var y = 0
    while (y < height) {
        val rowOffset = y * rowStride
        var x = 0
        while (x < width) {
            val inInnerBox = x in innerStartX until innerEndX && y in innerStartY until innerEndY
            val idx = rowOffset + x * pixelStride
            if (!inInnerBox && idx < buffer.limit()) {
                val luma = buffer.get(idx).toInt() and 0xFF
                if (luma >= WHITE_LUMA_THRESHOLD) {
                    white++
                }
                total++
            }
            x += 2
        }
        y += 2
    }

    if (total == 0) return 0f
    return white.toFloat() / total
}

private fun imageProxyToBitmap(image: ImageProxy): Bitmap {
    val buffer: ByteBuffer = image.planes[0].buffer
    val bytes = ByteArray(buffer.remaining())
    buffer.get(bytes)
    val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)

    val rotationDegrees = image.imageInfo.rotationDegrees
    return if (rotationDegrees != 0) {
        val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
        Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    } else {
        bitmap
    }
}
