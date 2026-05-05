package com.nipuna.teavision.network

import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

/**
 * Retrofit interface for the Unified Backend API
 */
interface ApiService {

    @Multipart
    @POST("/api/upload")
    suspend fun uploadCapture(
        @Part image: MultipartBody.Part,
        @Part("metadata") metadata: RequestBody
    ): Response<ResponseBody>
}
