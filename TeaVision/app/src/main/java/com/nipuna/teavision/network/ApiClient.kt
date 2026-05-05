package com.nipuna.teavision.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Retrofit singleton for backend communication.
 * Uses 10.0.2.2 which maps to host localhost from Android emulator.
 * For physical device on same network, change to the PC's local IP.
 */
object ApiClient {

    // Emulator: 10.0.2.2 maps to host machine's localhost
    // Physical device: use your PC's IP (e.g. "http://192.168.1.100:8000")
    private const val BASE_URL = "http://192.168.1.58:8000"

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val httpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(httpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val service: ApiService = retrofit.create(ApiService::class.java)
}
