package com.nipuna.teavision.composables

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Straighten
import androidx.compose.material.icons.filled.VerticalAlignBottom
import androidx.compose.material.icons.filled.VerticalAlignTop
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.nipuna.teavision.utils.BarometerHeightCalibration
import com.nipuna.teavision.utils.FixedDistanceMeasurement
import kotlinx.coroutines.flow.collectLatest
import kotlin.math.abs
import kotlin.math.roundToInt

enum class CalibrationMethod {
    MANUAL,
    BAROMETER
}

@Composable
fun CalibrationDialog(
    onDismiss: () -> Unit,
    onSave: (Float) -> Unit
) {
    val context = LocalContext.current
    val hasBarometer = remember { BarometerHeightCalibration.hasBarometer(context) }

    var selectedMethod by remember {
        mutableStateOf(if (hasBarometer) CalibrationMethod.BAROMETER else CalibrationMethod.MANUAL)
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.Straighten, contentDescription = null) },
        title = {
            Text(
                "Capture Station Setup",
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Method selector (only if barometer available)
                if (hasBarometer) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = selectedMethod == CalibrationMethod.BAROMETER,
                            onClick = { selectedMethod = CalibrationMethod.BAROMETER },
                            label = { Text("Lift to Measure") },
                            leadingIcon = {
                                Icon(
                                    Icons.Default.VerticalAlignTop,
                                    contentDescription = null,
                                    modifier = Modifier.size(18.dp)
                                )
                            },
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = selectedMethod == CalibrationMethod.MANUAL,
                            onClick = { selectedMethod = CalibrationMethod.MANUAL },
                            label = { Text("Manual") },
                            leadingIcon = {
                                Icon(
                                    Icons.Default.Straighten,
                                    contentDescription = null,
                                    modifier = Modifier.size(18.dp)
                                )
                            },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }

                when (selectedMethod) {
                    CalibrationMethod.MANUAL -> ManualCalibrationContent(
                        onSave = onSave
                    )
                    CalibrationMethod.BAROMETER -> BarometerCalibrationContent(
                        onSave = onSave
                    )
                }
            }
        },
        confirmButton = {},  // Handled inside each content
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
private fun ManualCalibrationContent(
    onSave: (Float) -> Unit
) {
    val context = LocalContext.current
    var distanceText by remember {
        mutableStateOf(FixedDistanceMeasurement.getDistance(context).toInt().toString())
    }
    var isError by remember { mutableStateOf(false) }

    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            "Enter the distance from your phone camera to the capture surface.",
            style = MaterialTheme.typography.bodyMedium
        )

        OutlinedTextField(
            value = distanceText,
            onValueChange = {
                distanceText = it.filter { c -> c.isDigit() || c == '.' }
                isError = false
            },
            label = { Text("Distance") },
            suffix = { Text("cm") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            isError = isError,
            supportingText = if (isError) {
                { Text("Enter a valid distance (10-100 cm)") }
            } else {
                { Text("Recommended: 25-35 cm") }
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Button(
            onClick = {
                val distance = distanceText.toFloatOrNull()
                if (distance != null && distance in 10f..100f) {
                    onSave(distance)
                } else {
                    isError = true
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Save Distance")
        }
    }
}

@Composable
private fun BarometerCalibrationContent(
    onSave: (Float) -> Unit
) {
    val context = LocalContext.current

    // State
    var floorSet by remember { mutableStateOf(BarometerHeightCalibration.hasFloorCalibration(context)) }
    var currentPressure by remember { mutableFloatStateOf(0f) }
    var isStable by remember { mutableStateOf(false) }
    var stabilityScore by remember { mutableFloatStateOf(0f) }
    var calculatedHeight by remember { mutableFloatStateOf(0f) }

    // Collect pressure readings
    LaunchedEffect(Unit) {
        BarometerHeightCalibration.getPressureFlow(context).collectLatest { reading ->
            currentPressure = reading.pressureHpa
            isStable = reading.isStable
            stabilityScore = reading.stabilityScore

            // Calculate height if floor is set
            if (floorSet) {
                BarometerHeightCalibration.getFloorPressure(context)?.let { floorP ->
                    calculatedHeight = BarometerHeightCalibration.calculateHeight(floorP, currentPressure)
                }
            }
        }
    }

    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Instructions
        Text(
            if (!floorSet) {
                "1. Place phone on the FLOOR and press 'Set Floor'"
            } else {
                "2. Lift phone to capture position"
            },
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Bold
        )

        // Pressure reading display
        Card(
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "Pressure: ${String.format("%.2f", currentPressure)} hPa",
                    style = MaterialTheme.typography.bodyMedium
                )

                Spacer(Modifier.height(4.dp))

                // Stability indicator
                val stabilityColor by animateColorAsState(
                    targetValue = when {
                        stabilityScore > 0.8f -> Color.Green
                        stabilityScore > 0.5f -> Color.Yellow
                        else -> Color.Red
                    },
                    label = "stability"
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .background(stabilityColor, MaterialTheme.shapes.small)
                    )
                    Text(
                        if (isStable) "Stable - Ready" else "Hold still...",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (isStable) Color.Green else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Step 1: Set Floor
        if (!floorSet) {
            Button(
                onClick = {
                    if (isStable) {
                        BarometerHeightCalibration.saveFloorPressure(context, currentPressure)
                        floorSet = true
                    }
                },
                enabled = isStable,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(
                    Icons.Default.VerticalAlignBottom,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(Modifier.width(8.dp))
                Text("Set Floor Level")
            }

            Text(
                "Place phone flat on the floor and hold still",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        } else {
            // Step 2: Show height and confirm
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = if (calculatedHeight in 10f..100f)
                        MaterialTheme.colorScheme.primaryContainer
                    else
                        MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "Measured Height",
                        style = MaterialTheme.typography.labelMedium
                    )
                    Text(
                        "${abs(calculatedHeight).roundToInt()} cm",
                        style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.Bold
                    )

                    if (calculatedHeight < 10f) {
                        Text(
                            "Lift the phone higher",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Reset button
                OutlinedButton(
                    onClick = {
                        BarometerHeightCalibration.clearFloorPressure(context)
                        floorSet = false
                        calculatedHeight = 0f
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Reset Floor")
                }

                // Confirm button
                Button(
                    onClick = {
                        val height = abs(calculatedHeight)
                        if (height in 10f..100f) {
                            onSave(height)
                        }
                    },
                    enabled = calculatedHeight in 10f..100f && isStable,
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(
                        Icons.Default.Check,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(Modifier.width(4.dp))
                    Text("Use This")
                }
            }
        }

        // Info about accuracy
        Text(
            "Accuracy: ~8-10 cm (barometer resolution)",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
fun CalibrationButton(
    isCalibrated: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val currentDistance = remember { FixedDistanceMeasurement.getDistance(context) }

    FilledTonalButton(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.filledTonalButtonColors(
            containerColor = if (isCalibrated)
                MaterialTheme.colorScheme.primaryContainer
            else
                MaterialTheme.colorScheme.errorContainer
        )
    ) {
        Icon(
            Icons.Default.Straighten,
            contentDescription = null,
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(4.dp))
        Text(
            if (isCalibrated) "${currentDistance.toInt()}cm" else "Setup",
            style = MaterialTheme.typography.labelMedium
        )
    }
}
