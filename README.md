# NamaPlayer

A modern desktop video player built with Python, powered by the high-performance mpv media player backend.

![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-WIP-yellow.svg)

## Overview

NamaPlayer is a lightweight yet powerful desktop video player which uses playback capabilities of MPV. It aims to
provide a clean, responsive video playback experience for desktop users.

## Features

- **High-Quality Playback**: Powered by mpv with GPU-accelerated video output.
- **Simple Interface**: Clean UI with minimal controls.
- **Wide Format Support**: Leverages mpv's extensive codec support.
- **Lightweight**: Minimal dependencies and fast startup.

### Prerequisites

- Python 3.14 or higher
- [mpv](https://mpv.io/installation/) must be installed on your system

### Setup

1. Clone the repository:

```bash
git clone https://github.com/hojat72elect/NamaPlayer.git
cd NamaPlayer
```

2. Install dependencies using uv:

```bash
uv sync
```

## Usage

Run the application:

```bash
uv run python src/main.py
```

Or directly with Python:

```bash
python src/main.py
```

Once launched:

1. Click the "Open Video" button
2. Select a video file from the file dialog
3. The video will begin playing in the embedded window

## Development

Run linting:

```bash
uv run ruff check src/
```

Format code:

```bash
uv run ruff format src/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
