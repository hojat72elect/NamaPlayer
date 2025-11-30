package ca.on.hojat.nama

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.Button
import androidx.compose.material.Slider
import androidx.compose.material.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun PlayerControls(
    isPlaying: Boolean,
    onPlayPause: () -> Unit,
    currentTime: Float,
    totalTime: Float,
    onSeek: (Float) -> Unit,
    volume: Float,
    onVolumeChange: (Float) -> Unit,
    onOpenFile: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(16.dp)
    ) {

        Slider(
            value = currentTime,
            onValueChange = onSeek,
            valueRange = 0f..totalTime,
            modifier = Modifier.fillMaxWidth()
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {

            Button(onClick = onPlayPause) {
                Text(if (isPlaying) "Pause" else "Play")
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Vol: ")
                Slider(
                    value = volume,
                    onValueChange = onVolumeChange,
                    valueRange = 0f..100f,
                    modifier = Modifier.width(100.dp)
                )
            }

            // Open File Button
            Button(onClick = onOpenFile) {
                Text("Open File")
            }
        }
    }
}
