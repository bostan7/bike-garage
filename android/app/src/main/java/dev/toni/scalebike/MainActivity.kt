package dev.toni.scalebike

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import dev.toni.scalebike.ui.BikeApp
import dev.toni.scalebike.ui.theme.ScaleBikeTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val repo = (application as BikeApplication).repository
        setContent {
            ScaleBikeTheme {
                BikeApp(repo)
            }
        }
    }
}
