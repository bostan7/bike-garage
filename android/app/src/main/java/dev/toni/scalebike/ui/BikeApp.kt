package dev.toni.scalebike.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Handyman
import androidx.compose.material.icons.filled.PedalBike
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Timeline
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import dev.toni.scalebike.data.BikeRepository
import dev.toni.scalebike.garage.Garage3D
import dev.toni.scalebike.ui.screens.GarageScreen
import dev.toni.scalebike.ui.screens.HomeScreen
import dev.toni.scalebike.ui.screens.PartDetailScreen
import dev.toni.scalebike.ui.screens.SetupScreen
import dev.toni.scalebike.ui.screens.TimelineScreen
import dev.toni.scalebike.ui.screens.ToolsScreen

val LocalRepo = staticCompositionLocalOf<BikeRepository> { error("Repository not provided") }

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val tabs = listOf(
    Tab("home", "Bike", Icons.Filled.PedalBike),
    Tab("timeline", "Timeline", Icons.Filled.Timeline),
    Tab("tools", "Tools", Icons.Filled.Handyman),
    Tab("garage", "Garage", Icons.Filled.Settings),
)

@Composable
fun BikeApp(repo: BikeRepository) {
    val data by repo.data.collectAsStateWithLifecycle()
    CompositionLocalProvider(LocalRepo provides repo) {
        if (!data.setupDone) {
            Scaffold(containerColor = MaterialTheme.colorScheme.background) { pad ->
                SetupScreen(data, Modifier.padding(pad))
            }
            return@CompositionLocalProvider
        }

        val nav = rememberNavController()
        val entry by nav.currentBackStackEntryAsState()
        val route = entry?.destination?.route
        val openPart: (String) -> Unit = { nav.navigate("part/$it") }

        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            bottomBar = {
                if (tabs.any { it.route == route }) {
                    NavigationBar(containerColor = MaterialTheme.colorScheme.surfaceContainerLow) {
                        tabs.forEach { t ->
                            NavigationBarItem(
                                selected = route == t.route,
                                onClick = {
                                    nav.navigate(t.route) {
                                        popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                },
                                icon = { Icon(t.icon, contentDescription = null) },
                                label = { Text(t.label) },
                            )
                        }
                    }
                }
            },
        ) { pad ->
            NavHost(nav, startDestination = "home", modifier = Modifier.padding(pad)) {
                composable("home") { Garage3D(Modifier.fillMaxSize()) }   // Phase 2: 3D garage is home
                composable("timeline") { TimelineScreen(data, openPart) }
                composable("tools") { ToolsScreen(data) }
                composable("garage") { GarageScreen(data) }
                composable("part/{id}") { e ->
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
