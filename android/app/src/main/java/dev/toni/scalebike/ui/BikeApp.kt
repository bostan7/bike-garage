package dev.toni.scalebike.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import dev.toni.scalebike.data.BikeRepository
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import dev.toni.scalebike.garage.GarageController
import dev.toni.scalebike.garage.GarageView
import dev.toni.scalebike.ui.game.GameScreen
import dev.toni.scalebike.ui.screens.GarageScreen
import dev.toni.scalebike.ui.screens.HomeScreen
import dev.toni.scalebike.ui.screens.PartDetailScreen
import dev.toni.scalebike.ui.screens.SetupScreen
import dev.toni.scalebike.ui.screens.TimelineScreen
import dev.toni.scalebike.ui.screens.ToolsScreen

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

        val nav = rememberNavController()
        val openPart: (String) -> Unit = { nav.navigate("part/$it") }
        // full-screen app: the 3D garage fills everything, the old 2D pages keep clear of the camera cutout
        val page = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .windowInsetsPadding(WindowInsets.safeDrawing)

        NavHost(nav, startDestination = "home", modifier = Modifier.fillMaxSize()) {
            composable("home") {
                // the 3D garage underneath, the NFS game UI on top (it handles every touch and drives the garage)
                var garage by remember { mutableStateOf<GarageController?>(null) }
                Box(Modifier.fillMaxSize()) {
                    GarageView(Modifier.fillMaxSize(), onReady = { garage = it })
                    GameScreen(data, garage, Modifier.fillMaxSize())
                }
            }
            composable("parts") { Box(page) { HomeScreen(data, openPart) } }
            composable("timeline") { Box(page) { TimelineScreen(data, openPart) } }
            composable("tools") { Box(page) { ToolsScreen(data) } }
            composable("garage") { Box(page) { GarageScreen(data) } }
            composable("part/{id}") { e ->
                Box(page) {
                    PartDetailScreen(
                        data = data,
                        partId = e.arguments?.getString("id").orEmpty(),
                        onBack = { nav.popBackStack() },
                        onOpenPart = openPart,
                    )
                }
            }
        }
    }
}
