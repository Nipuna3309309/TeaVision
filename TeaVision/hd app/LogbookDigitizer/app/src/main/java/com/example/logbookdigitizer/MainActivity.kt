package com.example.logbookdigitizer

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.card.MaterialCardView
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import java.io.FileOutputStream

class MainActivity : AppCompatActivity() {

    private lateinit var btnScanDocument: Button
    private lateinit var ivScannedPreview: ImageView

    // QA Views
    private lateinit var layoutQaError: LinearLayout
    private lateinit var tvQaErrorMessage: TextView
    private lateinit var btnRetryScan: Button
    private lateinit var tvQaSuccess: TextView

    // Metadata Views
    private lateinit var cardMetadataForm: MaterialCardView
    private lateinit var etDivision: EditText
    private lateinit var etFieldId: EditText
    private lateinit var etStartDate: EditText
    private lateinit var etEndDate: EditText
    private lateinit var btnUpload: Button

    private var scannedImageUri: Uri? = null

    private val scannerLauncher = registerForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
        if (result.resultCode == RESULT_OK) {
            val scanResult = com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult.fromActivityResultIntent(result.data)
            scanResult?.pages?.let { pages ->
                if (pages.isNotEmpty()) {
                    handleScannedImage(pages[0].imageUri)
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Bind Views
        btnScanDocument = findViewById(R.id.btnScanDocument)
        ivScannedPreview = findViewById(R.id.ivScannedPreview)
        layoutQaError = findViewById(R.id.layoutQaError)
        tvQaErrorMessage = findViewById(R.id.tvQaErrorMessage)
        btnRetryScan = findViewById(R.id.btnRetryScan)
        tvQaSuccess = findViewById(R.id.tvQaSuccess)

        cardMetadataForm = findViewById(R.id.cardMetadataForm)
        etDivision = findViewById(R.id.etDivision)
        etFieldId = findViewById(R.id.etFieldId)
        etStartDate = findViewById(R.id.etStartDate)
        etEndDate = findViewById(R.id.etEndDate)
        btnUpload = findViewById(R.id.btnUpload)

        btnScanDocument.setOnClickListener { launchScanner() }
        btnRetryScan.setOnClickListener { launchScanner() }

        btnUpload.setOnClickListener {
            val division = etDivision.text.toString().trim()
            val fieldId = etFieldId.text.toString().trim()
            val start = etStartDate.text.toString().trim()
            val end = etEndDate.text.toString().trim()

            if (division.isEmpty() || fieldId.isEmpty() || start.isEmpty() || end.isEmpty() || scannedImageUri == null) {
                Toast.makeText(this, "Please complete all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            uploadToCloud(scannedImageUri!!, division, fieldId, start, end)
        }
    }

    private fun launchScanner() {
        val options = GmsDocumentScannerOptions.Builder()
            .setGalleryImportAllowed(true)
            .setPageLimit(1)
            .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
            .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
            .build()

        GmsDocumentScanning.getClient(options).getStartScanIntent(this)
            .addOnSuccessListener { intentSender ->
                scannerLauncher.launch(IntentSenderRequest.Builder(intentSender).build())
            }
    }

    private fun handleScannedImage(uri: Uri) {
        scannedImageUri = uri
        ivScannedPreview.visibility = View.VISIBLE
        ivScannedPreview.setImageURI(uri)

        // Reset UI
        layoutQaError.visibility = View.GONE
        tvQaSuccess.visibility = View.GONE
        cardMetadataForm.visibility = View.GONE
        btnScanDocument.text = "Checking Quality..."
        btnScanDocument.isEnabled = false

        CoroutineScope(Dispatchers.Main).launch {
            val bitmap = withContext(Dispatchers.IO) { getScaledBitmap(uri) }

            if (bitmap != null) {
                val qaResult = withContext(Dispatchers.Default) { runQualityChecks(bitmap) }

                btnScanDocument.isEnabled = true
                btnScanDocument.text = "📷 Tap to Scan Logbook"

                if (qaResult == "PASS") {
                    tvQaSuccess.visibility = View.VISIBLE
                    cardMetadataForm.visibility = View.VISIBLE
                } else {
                    tvQaErrorMessage.text = " $qaResult"
                    layoutQaError.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun runQualityChecks(bitmap: Bitmap): String {
        // 1. Fold & Crease Detection
        if (detectFolds(bitmap)) {
            return "Fold detected! Please flatten the paper and align edges carefully."
        }

        // 2. Blur Check (Glare Check completely removed)
        var sum = 0L
        var sqSum = 0L
        var totalPixels = 0

        val step = 2
        for (y in 0 until bitmap.height step step) {
            for (x in 0 until bitmap.width step step) {
                val pixel = bitmap.getPixel(x, y)
                val r = (pixel shr 16) and 0xff
                val g = (pixel shr 8) and 0xff
                val b = pixel and 0xff

                // Blur Check (Grayscale intensity)
                val gray = (r + g + b) / 3
                sum += gray
                sqSum += gray * gray
                totalPixels++
            }
        }

        val mean = sum.toDouble() / totalPixels
        val variance = (sqSum.toDouble() / totalPixels) - (mean * mean)

        // Blur Check
        if (variance < 250.0) {
            return "Image is blurry. Please hold the phone steady and retake."
        }

        return "PASS"
    }

    // --- FOLD DETECTOR ---
    private fun detectFolds(bitmap: Bitmap): Boolean {
        val width = bitmap.width
        val height = bitmap.height
        val step = 4

        // TEST 1: Detect warped missing corners (black triangles caused by folded edges)
        val cornerSize = width / 10
        val corners = listOf(
            Pair(0, 0), // Top-Left
            Pair(width - cornerSize, 0), // Top-Right
            Pair(0, height - cornerSize), // Bottom-Left
            Pair(width - cornerSize, height - cornerSize) // Bottom-Right
        )

        for ((startX, startY) in corners) {
            var darkPixels = 0
            for (x in startX until startX + cornerSize step step) {
                for (y in startY until startY + cornerSize step step) {
                    val p = bitmap.getPixel(x, y)
                    val r = (p shr 16) and 0xff
                    // If pixel is near pure black (scanner artifact padding)
                    if (r < 30) darkPixels++
                }
            }
            val totalSample = (cornerSize / step) * (cornerSize / step)
            if (darkPixels.toFloat() / totalSample > 0.4f) {
                return true // A corner is 40% black, meaning the paper was folded/warped
            }
        }

        // TEST 2: Detect strong horizontal creases (Shadow lines)
        var creaseCount = 0
        for (y in height / 5 until height - (height / 5) step 10) {
            var rowBrightnessSum = 0
            for (x in 0 until width step step) {
                val p = bitmap.getPixel(x, y)
                rowBrightnessSum += (p shr 16) and 0xff // Using Red channel as brightness proxy
            }
            val avgRowBrightness = rowBrightnessSum / (width / step)
            // If a row drops severely in brightness (a deep shadow line)
            if (avgRowBrightness < 90) creaseCount++
        }

        // If we find multiple deep shadow lines, it's a severely creased/folded page
        if (creaseCount > 5) return true

        return false
    }

    private fun getScaledBitmap(uri: Uri): Bitmap? {
        return try {
            val options = BitmapFactory.Options()
            options.inSampleSize = 4 // Shrink to save memory
            contentResolver.openInputStream(uri)?.use { inputStream ->
                BitmapFactory.decodeStream(inputStream, null, options)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    // --- UPLOAD ENGINE ---
    private fun uploadToCloud(uri: Uri, division: String, fieldId: String, start: String, end: String) {
        btnUpload.isEnabled = false
        btnUpload.text = "Uploading to Cloud..."

        val file = getFileFromUri(uri) ?: return

        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
        val bodyImage = MultipartBody.Part.createFormData("image", file.name, requestFile)

        val bDiv = division.toRequestBody("text/plain".toMediaTypeOrNull())
        val bField = fieldId.toRequestBody("text/plain".toMediaTypeOrNull())
        val bStart = start.toRequestBody("text/plain".toMediaTypeOrNull())
        val bEnd = end.toRequestBody("text/plain".toMediaTypeOrNull())

        RetrofitClient.instance.uploadImage(bodyImage, bDiv, bField, bStart, bEnd)
            .enqueue(object : Callback<BasicResponse> {
                override fun onResponse(call: Call<BasicResponse>, response: Response<BasicResponse>) {
                    btnUpload.isEnabled = true
                    btnUpload.text = " Save to Database"

                    if (response.isSuccessful && response.body()?.status == "success") {
                        Toast.makeText(applicationContext, " Successfully Synced!", Toast.LENGTH_LONG).show()

                        // Reset UI
                        etDivision.text?.clear()
                        etFieldId.text?.clear()
                        etStartDate.text?.clear()
                        etEndDate.text?.clear()
                        scannedImageUri = null
                        ivScannedPreview.visibility = View.GONE
                        tvQaSuccess.visibility = View.GONE
                        cardMetadataForm.visibility = View.GONE
                    } else {
                        Toast.makeText(applicationContext, "Upload failed.", Toast.LENGTH_LONG).show()
                    }
                }

                override fun onFailure(call: Call<BasicResponse>, t: Throwable) {
                    btnUpload.isEnabled = true
                    btnUpload.text = " Save to Database"
                    Toast.makeText(applicationContext, "Error: ${t.message}", Toast.LENGTH_LONG).show()
                }
            })
    }

    private fun getFileFromUri(uri: Uri): File? {
        return try {
            val inputStream = contentResolver.openInputStream(uri)
            val tempFile = File.createTempFile("upload", ".jpg", cacheDir)
            val outputStream = FileOutputStream(tempFile)
            inputStream?.copyTo(outputStream)
            inputStream?.close()
            outputStream.close()
            tempFile
        } catch (e: Exception) { null }
    }
}