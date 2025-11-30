package ca.on.hojat.nama

import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import uk.co.caprica.vlcj.factory.discovery.NativeDiscovery

fun main() {
    // Initialize VLC native libraries
    if (!initializeVLC()) {
        println("ERROR: Failed to initialize VLC!")
        println("Please follow the instructions in libs/vlc/README.md to set up VLC libraries.")
        return
    }
    
    application {
        Window(onCloseRequest = ::exitApplication, title = "Nama Player") {
            VideoPlayer()
        }
    }
}

/**
 * Initialize VLC native libraries by trying multiple discovery methods:
 * 1. Bundled VLC in libs/vlc/
 * 2. System-installed VLC (automatic discovery)
 * 3. Custom path fallback
 */
fun initializeVLC(): Boolean {
    // Get the OS name and architecture
    val osName = System.getProperty("os.name").lowercase()
    val osArch = System.getProperty("os.arch")
    
    // Determine the platform-specific directory
    val platformDir = when {
        osName.contains("win") && osArch.contains("64") -> "windows-x64"
        osName.contains("win") -> "windows-x86"
        osName.contains("mac") -> "macos-x64"
        osName.contains("linux") && osArch.contains("64") -> "linux-x64"
        else -> null
    }
    
    // Try bundled VLC first
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
    
    // Try automatic system discovery
    println("Attempting automatic VLC discovery...")
    if (NativeDiscovery().discover()) {
        println("✓ Successfully discovered system-installed VLC")
        return true
    }
    
    // Try common installation paths as fallback
    val commonPaths = when {
        osName.contains("win") -> listOf(
            "C:\\Program Files\\VideoLAN\\VLC",
            "C:\\Program Files (x86)\\VideoLAN\\VLC",
            "D:\\Apps\\VLC"
        )
        osName.contains("mac") -> listOf(
            "/Applications/VLC.app/Contents/MacOS/lib"
        )
        else -> listOf(
            "/usr/lib",
            "/usr/local/lib"
        )
    }
    
    for (path in commonPaths) {
        if (java.io.File(path).exists()) {
            println("Trying VLC at: $path")
            System.setProperty("jna.library.path", path)
            
            if (NativeDiscovery().discover()) {
                println("✓ Successfully loaded VLC from: $path")
                return true
            }
        }
    }
    
    println("✗ VLC not found in any known location")
    return false
}