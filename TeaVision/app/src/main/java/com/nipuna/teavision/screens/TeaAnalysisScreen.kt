package com.nipuna.teavision.screens

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.nipuna.teavision.composables.CaptureMetadata
import com.nipuna.teavision.composables.LeafMeasurementData
import com.nipuna.teavision.utils.ImageUtils

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TeaAnalysisScreen(
    bitmap: Bitmap,
    quality: ImageUtils.QualityReport,
    meta: CaptureMetadata?,
    measurement: LeafMeasurementData?,
    segmentationMask: Bitmap?,
    batchId: String,
    batchImageIndex: Int,
    onBack: () -> Unit,
    onSave: (Bitmap) -> Unit,
    onNewBatch: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Leaf Analysis", fontWeight = FontWeight.Bold) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "Back") } }
            )
        }
    ) { pad ->
        Column(
            modifier = Modifier
                .padding(pad)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. Batch Info Card
            ElevatedCard(
                colors = CardDefaults.elevatedCardColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Batch: $batchId", style = MaterialTheme.typography.labelMedium)
                        Text("Image #${batchImageIndex + 1}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    }
                    OutlinedButton(onClick = onNewBatch) {
                        Icon(Icons.Default.Add, null, Modifier.size(18.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("New Batch")
                    }
                }
            }

            // 2. Quality Card
            ElevatedCard(
                colors = CardDefaults.elevatedCardColors(
                    containerColor = if (quality.isPassed) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(Modifier.padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(if (quality.isPassed) Icons.Default.CheckCircle else Icons.Default.Warning, null)
                        Spacer(Modifier.width(8.dp))
                        Text(
                            if (quality.isPassed) "Quality Passed" else "Rejected",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    HorizontalDivider(Modifier.padding(vertical = 8.dp))

                    // Resolution
                    Text("Resolution: ${String.format("%.2f", quality.resolutionMP)} MP")

                    // Sharpness
                    Text("Sharpness Score: ${String.format("%.0f", quality.blurScore)}")

                    // Light Analysis (multi-signal)
                    quality.lightAnalysis?.let { light ->
                        val lightColor = when (light.level) {
                            "too_dark" -> MaterialTheme.colorScheme.error
                            "poor" -> Color(0xFFFF9800)
                            "good" -> Color(0xFF4CAF50)
                            "bright" -> Color(0xFF8BC34A)
                            "too_bright" -> MaterialTheme.colorScheme.error
                            else -> MaterialTheme.colorScheme.onSurface
                        }
                        Text(
                            "Lighting: ${light.label} (${String.format("%.0f", light.score)}/100)",
                            color = lightColor,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            light.tip,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            "Background Brightness: ${String.format("%.0f", light.bgBrightness)} | " +
                            "Highlights: ${String.format("%.0f", light.highlightBrightness)} | " +
                            "Saturation: ${String.format("%.0f", light.avgSaturation)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } ?: run {
                        // Fallback if no light analysis
                        Text("Brightness: ${String.format("%.0f", quality.brightness)}")
                    }

                    // Glare
                    val glareStatus = if (quality.hasGlare) " (Detected!)" else " (None)"
                    Text("Glare: ${String.format("%.1f", quality.glarePercentage * 100)}%$glareStatus")

                    // Background texture
                    Text("Background: ${if (quality.hasClutteredBackground) "Cluttered (use plain cloth)" else "Clean"}")

                    // Light background percentage (capture guide)
                    meta?.let {
                        val pct = (it.whiteBackgroundPercent * 100).toInt()
                        val status = if (it.whiteBackgroundPercent >= 0.60f) " (OK)" else " (Need light surface)"
                        Text("Light Surface: ${pct}%$status")
                    }

                    // Failure reasons if any
                    if (!quality.isPassed && quality.failureReasons.isNotEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Issues:",
                            color = MaterialTheme.colorScheme.error,
                            fontWeight = FontWeight.Bold
                        )
                        quality.failureReasons.forEach { reason ->
                            Text(
                                "- $reason",
                                color = MaterialTheme.colorScheme.error,
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                    }
                }
            }

            // 3. Measurement Card (if available)
            measurement?.let { m ->
                ElevatedCard(
                    colors = CardDefaults.elevatedCardColors(
                        containerColor = if (m.calibrated) MaterialTheme.colorScheme.tertiaryContainer
                        else MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                if (m.calibrated) Icons.Default.Straighten else Icons.Default.Info,
                                null
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(
                                if (m.calibrated) "Leaf Measurements" else "Measurement Info",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        HorizontalDivider(Modifier.padding(vertical = 8.dp))

                        if (m.calibrated) {
                            // Show measurements
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column {
                                    Text("Width", style = MaterialTheme.typography.labelSmall)
                                    Text(
                                        "${String.format("%.1f", m.leafWidthCm ?: 0f)} cm",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                Column {
                                    Text("Height", style = MaterialTheme.typography.labelSmall)
                                    Text(
                                        "${String.format("%.1f", m.leafHeightCm ?: 0f)} cm",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                Column {
                                    Text("Area", style = MaterialTheme.typography.labelSmall)
                                    Text(
                                        "${String.format("%.2f", m.leafAreaCm2 ?: 0f)} cm²",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }

                            Spacer(Modifier.height(8.dp))

                            // Additional info
                            Text(
                                "Calibration: ${String.format("%.1f", m.pixelsPerCm ?: 0f)} px/cm",
                                style = MaterialTheme.typography.bodySmall
                            )
                            m.leafPercentage?.let {
                                Text(
                                    "Leaf Coverage: ${String.format("%.1f", it)}%",
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                            m.colorGreenness?.let {
                                Text(
                                    "Greenness: ${String.format("%.0f", it * 100)}%",
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                            Text(
                                "Segmentation: ${if (m.usedMLSegmentation) "ML Model" else "Color Analysis"} (${String.format("%.0f", (m.segmentationConfidence ?: 0f) * 100)}% conf)",
                                style = MaterialTheme.typography.bodySmall
                            )
                        } else {
                            // Not calibrated - show instructions
                            Text(
                                m.measurementMessage ?: "Place a QR reference card next to the leaf for measurements.",
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "QR Code Format: TEAVISION:<size_cm>",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                "Example: TEAVISION:3.0 for a 3cm QR code",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            }

            // 4. Image Preview (FULL image, no splitting)
            var showMask by remember { mutableStateOf(false) }

            ElevatedCard {
                Column {
                    Image(
                        bitmap = (if (showMask && segmentationMask != null) segmentationMask else bitmap).asImageBitmap(),
                        contentDescription = "Captured Leaf",
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(350.dp)
                            .background(Color.Black)
                    )
                    // Toggle for segmentation mask
                    if (segmentationMask != null) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(8.dp),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Show Mask", style = MaterialTheme.typography.bodySmall)
                            Spacer(Modifier.width(8.dp))
                            Switch(
                                checked = showMask,
                                onCheckedChange = { showMask = it }
                            )
                        }
                    }
                }
            }

            // 5. Actions - Save full image only (NO quadrant splitting)
            if (quality.isPassed) {
                Button(
                    onClick = { onSave(bitmap) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.Default.Save, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Save to Dataset (Image + JSON)")
                }

                // Retake option
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Refresh, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Retake Photo")
                }
            } else {
                // If rejected, only option is to retake
                Button(
                    onClick = onBack,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Icon(Icons.Default.Refresh, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Retake Photo")
                }
            }
        }
    }
}
