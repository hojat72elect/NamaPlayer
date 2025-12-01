package ca.on.hojat.nama

import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import uk.co.caprica.vlcj.factory.discovery.NativeDiscovery

fun main() {

    if (!initializeVLC()) {
        println("ERROR: Failed to initialize VLC!")
        println("Please follow the instructions in libs/vlc/README.md to set up VLC libraries correctly.")
        return
    }

    application {
        Window(onCloseRequest = ::exitApplication, title = "Nama Player") {
            VideoPlayer()
        }
    }
}

/**
 * Initialize VLC native libraries.
 */
fun initializeVLC(): Boolean {

    val osName = System.getProperty("os.name").lowercase()
    val osArch = System.getProperty("os.arch")

    // The platform-specific directory
    val platformDir = when {
        osName.contains("win") && osArch.contains("64") -> "windows-x64"
        osName.contains("win") -> "windows-x86"
        osName.contains("mac") -> "macos-x64"
        osName.contains("linux") && osArch.contains("64") -> "linux-x64"
        else -> null
    }

    if (platformDir != null) {
        val bundledVlcPath = java.io.File("libs/vlc/$platformDir").absolutePath
        if (java.io.File(bundledVlcPath).exists()) {
            println("Found bundled VLC at: $bundledVlcPath")
            System.setProperty("jna.library.path", bundledVlcPath)

            if (NativeDiscovery().discover()) {
                println("✓ Successfully loaded bundled VLC libraries")
                return true
            } else {
                println("⚠ Bundled VLC found but failed to load")
            }
        } else {
            println("ℹ No bundled VLC found at: $bundledVlcPath")
        }
    }

    return false
}