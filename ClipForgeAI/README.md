# ClipForge AI — Local Prototype

This starter app creates clips from uploaded videos using local speech recognition and FFmpeg.

## Requirements
- Windows 10/11
- Python 3.10 or 3.11 recommended
- FFmpeg (includes ffprobe)
- Internet connection for first-time Python package/model installation

## Setup
1. Install Python from https://www.python.org/downloads/ and enable "Add Python to PATH".
2. Install FFmpeg. A Windows guide: https://www.gyan.dev/ffmpeg/builds/
   Add FFmpeg's `bin` folder to your PATH.
3. Extract this ZIP.
4. Open the extracted folder.
5. Double-click `START_CLIPFORGE.bat`.

If the batch file doesn't work:
```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

The app opens in your browser at a local address, usually http://localhost:8501.

## What works
- Upload video files
- Transcribe speech using Faster-Whisper (local)
- Pick candidate windows using a simple scoring heuristic
- Render vertical clips with optional burned-in subtitles
- Suggested clip titles
- Download individual clips or ZIP

## Limitations
This is an early prototype. The "viral score" is a rough heuristic, not a guarantee. Captions are plain subtitles, not animated word-by-word captions yet. The app does not download arbitrary URLs or automatically publish to YouTube in this version. Only process videos you own or have permission to use.

## Troubleshooting
- FFmpeg not found: install FFmpeg and add its `bin` directory to PATH, then restart terminal/app.
- Model download: first launch may download the speech model.
- Slow processing: use the `tiny` model.
- If a video is portrait, turn off vertical crop if it distorts the framing.
