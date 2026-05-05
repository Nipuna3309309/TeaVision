package com.nipuna.teavision.network

import android.graphics.Bitmap
import android.util.Log
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream

/**
 * Handles uploading captures to the unified backend.
 * Designed to be called after local save succeeds (best-effort upload).
 */
object UploadWorker {

    private const val TAG = "UploadWorker"

    /**
     * Upload a bitmap and its metadata JSON to the server.
     * Returns true on success, false on failure.
     * This should be called from a coroutine on Dispatchers.IO.
     */
    suspend fun uploadToServer(
        bitmap: Bitmap,
        metadataJson: String,
        filename: String
    ): Boolean {
        return try {
            // Compress bitmap to JPEG bytes
            val baos = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 95, baos)
            val imageBytes = baos.toByteArray()

            // Build multipart image part
            val imageBody = imageBytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
            val imagePart = MultipartBody.Part.createFormData("image", "$filename.jpg", imageBody)

            // Build metadata part
            val metadataBody = metadataJson.toRequestBody("text/plain".toMediaTypeOrNull())

            // Execute upload
            val response = ApiClient.service.uploadCapture(imagePart, metadataBody)

            if (response.isSuccessful) {
                Log.i(TAG, "Upload successful: $filename")
                true
            } else {
                Log.w(TAG, "Upload failed: ${response.code()} ${response.message()}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Upload error for $filename: ${e.message}")
            false
        }
    }
}
