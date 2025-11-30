# VLC Native Libraries

This directory contains the native VLC libraries required for the NamaPlayer application.

## How to Install VLC Libraries

### Windows (64-bit)

1. **Download VLC 64-bit**
   - Go to: https://www.videolan.org/vlc/download-windows.html
   - Download the **64-bit Windows installer** (e.g., `vlc-3.0.20-win64.exe`)
   - Or download the **64-bit ZIP package** for easier extraction

2. **Extract the Required Files**
   
   **Option A: Using the Installer**
   - Install VLC to a temporary location (e.g., `C:\Temp\VLC`)
   - Navigate to the installation directory
   
   **Option B: Using the ZIP Package (Recommended)**
   - Download the ZIP package from: https://get.videolan.org/vlc/last/win64/
   - Extract the ZIP file to a temporary location

3. **Copy Files to This Project**
   
   From the VLC installation/extraction folder, copy these files to `libs/vlc/windows-x64/`:
   
   ```
   ✅ libvlc.dll
   ✅ libvlccore.dll
   ✅ plugins/ (entire directory with all subdirectories)
   ```
   
   **Important**: You MUST copy the entire `plugins` folder with all its subdirectories!

4. **Final Structure**
   
   After copying, your directory should look like this:
   ```
   libs/vlc/windows-x64/
   ├── libvlc.dll
   ├── libvlccore.dll
   └── plugins/
       ├── access/
       ├── audio_filter/
       ├── audio_mixer/
       ├── audio_output/
       ├── codec/
       ├── control/
       ├── demux/
       ├── keystore/
       ├── logger/
       ├── meta_engine/
       ├── misc/
       ├── packetizer/
       ├── services_discovery/
       ├── stream_filter/
       ├── stream_out/
       ├── text_renderer/
       ├── video_chroma/
       ├── video_filter/
       ├── video_output/
       └── visualization/
   ```

### macOS (Optional - for future cross-platform support)

Create `libs/vlc/macos-x64/` and follow similar steps with the macOS VLC build.

### Linux (Optional - for future cross-platform support)

Create `libs/vlc/linux-x64/` and follow similar steps with the Linux VLC build.

## Verification

After copying the files, run the application with:
```bash
.\gradlew.bat run
```

The application should now find the bundled VLC libraries automatically!

## Notes

- **Architecture**: Ensure you download 64-bit VLC to match your 64-bit JVM
- **Version**: VLC 3.x or 4.x should work with vlcj 4.8.3
- **Size**: The plugins folder is approximately 100-200 MB
- **Git**: Consider adding `libs/vlc/*/` to `.gitignore` if distributing separately
