package dev.toni.scalebike

import android.app.Application
import dev.toni.scalebike.data.BikeRepository

class BikeApplication : Application() {
    lateinit var repository: BikeRepository
        private set

    override fun onCreate() {
        super.onCreate()
        repository = BikeRepository(this)
    }
}
