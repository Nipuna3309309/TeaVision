package com.nipuna.teavision.composables

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun GridOverlay(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.fillMaxSize()) {
        val gridSize = 40.dp.toPx()
        val strokeWidth = 1.dp.toPx()
        val color = Color.White.copy(alpha = 0.5f)

        val verticalLines = (size.width / gridSize).toInt()
        val horizontalLines = (size.height / gridSize).toInt()

        // Draw vertical lines
        for (i in 1..verticalLines) {
            val x = i * gridSize
            drawLine(
                color = color,
                start = Offset(x, 0f),
                end = Offset(x, size.height),
                strokeWidth = strokeWidth
            )
        }

        // Draw horizontal lines
        for (i in 1..horizontalLines) {
            val y = i * gridSize
            drawLine(
                color = color,
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = strokeWidth
            )
        }
    }
}