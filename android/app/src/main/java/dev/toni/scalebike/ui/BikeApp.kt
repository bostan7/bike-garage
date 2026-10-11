package dev.toni.scalebike.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.toni.scalebike.data.BikeRepository
import dev.toni.scalebike.garage.GarageController
import dev.toni.scalebike.garage.GarageView
import dev.toni.scalebike.ui.game.GameScreen
import dev.toni.scalebike.ui.screens.SetupScreen

val LocalRepo = staticCompositionLocalOf<BikeRepository> { error("Repository not provided") }

@Composable
fun BikeApp(repo: BikeRepository) {
    val data by repo.data.collectAsStateWithLifecycle()
    CompositionLocalProvider(LocalRepo provides repo) {
        if (!data.setupDone) {
            Scaffold(
                containerColor = MaterialTheme.colorScheme.background,
                contentWindowInsets = WindowInsets.safeDrawing,
            ) { pad ->
                SetupScreen(data, Modifier.padding(pad))
            }
            return@CompositionLocalProvider
        }

        // the 3D garage underneath, the NFS game UI on top (it handles every touch and drives the garage);
        // every other screen is a panel inside the game UI
        var garage by remember { mutableStateOf<GarageController?>(null) }
        Box(Modifier.fillMaxSize()) {
            GarageView(Modifier.fillMaxSize(), onReady = { garage = it })
            GameScreen(data, garage, Modifier.fillMaxSize())
        }
    }
}
