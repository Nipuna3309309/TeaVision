package com.example.logbookdigitizer

import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import java.util.concurrent.TimeUnit

data class BasicResponse(val status: String, val message: String?, val error: String?)

interface LogbookApiService {
    @Multipart
    @POST("/upload-logbook")
    fun uploadImage(
        @Part image: MultipartBody.Part,
        @Part("division") division: RequestBody,
        @Part("field_id") fieldId: RequestBody,
        @Part("start_date") startDate: RequestBody,
        @Part("end_date") endDate: RequestBody
    ): Call<BasicResponse>
}

object RetrofitClient {
    // ⚠️ Replace with your Laptop's Wi-Fi IP Address
    private const val BASE_URL = "http://192.168.1.3:5000/"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    val instance: LogbookApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(LogbookApiService::class.java)
    }
}