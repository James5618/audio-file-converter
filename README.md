# Audio File Converter

A cross-platform audio file converter with GUI built using PyQt6. Convert between various audio formats and split audio files using cue sheets.

## Features

- **Multi-format Support**: Convert `.m4a`, `.flac`, and `.wv` (WavPack) files to MP3
- **Cue Sheet Splitting**: Split single audio files (FLAC/WV) into individual tracks using `.cue` files
- **Customizable Output**: Configure bitrate (128k, 192k, 320k) and sample rate (22050, 44100, 48000)
- **Batch Processing**: Convert entire folders with subdirectory support
- **Flexible Output Options**: Overwrite original files or save to a destination folder
- **Gamma Horizon Mode**: Special conversion mode for specific audio specifications (withhorizon version)
- **Cross-platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites

1. **Python 3.9+** required

2. **FFmpeg** is required for audio processing:
   - **Windows**: Included in the repository (auto-configured)
   - **macOS**: `brew install ffmpeg`
   - **Linux**:
     - Ubuntu/Debian: `sudo apt install ffmpeg`
     - Fedora: `sudo dnf install ffmpeg`
     - Arch Linux: `sudo pacman -S ffmpeg`

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Basic Version
```bash
python audioconv.py
```

### Version with Gamma Horizon Support
```bash
python audioconv-withhorizon.py
```

### Using the GUI

1. **Select Folder**: Choose a folder containing audio files to convert
2. **Select File Types**: Check the formats you want to convert (.m4a, .flac, .wv)
3. **Choose Output**:
   - Check "Overwrite original files" to replace originals
   - Or click "Select Destination Folder" to save to a new location
4. **Configure Settings**: Select bitrate and sample rate
5. **Convert**: Click "Convert" to start batch conversion

### Cue Sheet Splitting

1. Click "Split Audio with Cue Sheet"
2. Select your `.cue` file
3. Select the corresponding audio file (`.flac` or `.wv`)
4. Choose output folder
5. Individual tracks will be created with proper naming

## Files

- `audioconv.py` - Main audio converter application
- `audioconv-withhorizon.py` - Extended version with Gamma Horizon specifications
- `ffmpeg/` - FFmpeg binaries for Windows (auto-configured)

## Error Logging

Failed conversions and errors are logged to:
- `conversion_errors.log` - Conversion failures
- `cue_split_errors.log` - Cue splitting failures

## Requirements

- PyQt6
- pydub
- FFmpeg (system-installed or bundled)

## License

Open source - feel free to modify and distribute.
