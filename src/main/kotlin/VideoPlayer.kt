package ca.on.hojat.nama

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.awt.SwingPanel
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.delay
import uk.co.caprica.vlcj.player.component.EmbeddedMediaPlayerComponent
import javax.swing.JFileChooser

@Composable
fun VideoPlayer() {

    val mediaPlayerComponent = remember { EmbeddedMediaPlayerComponent() }
    var isPlaying by remember { mutableStateOf(false) }
    var currentTime by remember { mutableStateOf(0F) }
    var totalTime by remember { mutableStateOf(1F) }
    var volume by remember { mutableStateOf(50F) }

    LaunchedEffect(Unit) {
        while (true) {
            val player = mediaPlayerComponent.mediaPlayer()
            if (player.status().isPlaying) {
                currentTime = player.status().time().toFloat()
                totalTime = player.status().length().toFloat()
                isPlaying = true
            } else {
                isPlaying = false
            }
            delay(500)
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            mediaPlayerComponent.release()
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {

        SwingPanel(
            background = Color.Black,
            modifier = Modifier.weight(1f).fillMaxSize(),
            factory = {
                mediaPlayerComponent
            }
        )


        PlayerControls(
            isPlaying = isPlaying,
            onPlayPause = {
                val player = mediaPlayerComponent.mediaPlayer()
                if (player.status().isPlaying) {
                    player.controls().pause()
                } else {
                    player.controls().play()
                }
                isPlaying = !isPlaying
            },
            currentTime = currentTime,
            totalTime = totalTime,
            onSeek = { time ->
                mediaPlayerComponent.mediaPlayer().controls().setTime(time.toLong())
                currentTime = time
            },
            volume = volume,
            onVolumeChange = { vol ->
                volume = vol
                mediaPlayerComponent.mediaPlayer().audio().setVolume(vol.toInt())
            },
            onOpenFile = {
                val fileChooser = JFileChooser()
                val result = fileChooser.showOpenDialog(null)
                if (result == JFileChooser.APPROVE_OPTION) {
                    val file = fileChooser.selectedFile
                    mediaPlayerComponent.mediaPlayer().media().play(file.absolutePath)
                }
            }
        )
    }
}
