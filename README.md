# Mikey - Audio Recorder and Transcriber
 ## API for meeting recording
If you’re looking for a hosted meeting recording API, consider checking out [Recall.ai](https://www.recall.ai/?utm_source=github&utm_medium=sponsorship&utm_campaign=mikey), an API that records Zoom, Google Meet, Microsoft Teams, In-person meetings, and more.

##Mikey
Mikey is an application for recording audio, transcribing it locally or using the Groq API. Mikey provides a seamless experience for managing recordings, viewing transcriptions, and exploring saved sessions.

## Features

- **Audio Recording:** Records audio from WASAPI loopback devices using `pyaudiowpatch`.
- **Transcription Options:**
  - Local transcription using faster-whisper (supports CPU/CUDA)
  - Model size selection (tiny, base, small, medium, large)
  - Cloud-based transcription via Groq API (requires `GROQ_API_KEY`)

- **Recordings Browser:** Browse your session recordings with a dedicated two-panel window; the left panel lists session timestamps and the right panel displays the generated transcript.
- **Standalone Executable:** Option to build a standalone executable for easy distribution and use without Python environment setup.

## Directory Structure

```
Mikey/
├── core/
│   └── audio_session.py      # High-level session orchestration for recording, transcription, and merging
├── gui/
│   ├── main_window.py        # PyQt-based main GUI for recording, transcription, and managing sessions
│   └── recordings_window.py  # Two-panel recordings browser: left for session timestamps, right for transcript display
├── mikey/
│   ├── __init__.py           # Legacy initialization for the underlying functionality
│   ├── audio_recorder.py     # AudioRecorder class for capturing audio data
│   └── audio_transcriber.py  # AudioTranscriber class for transcription and meeting notes generation
├── recordings/               # Directory for storing recordings, transcripts, and meeting notes
├── bin/                      # Directory for FFmpeg binaries (included in executable builds)
├── resources/                # Directory for resources like favicon
├── main.py                   # Application entry point (launches the PyQt GUI)
├── README.md                 # Project overview and instructions
├── requirements.txt          # Project dependencies
├── main.spec                 # PyInstaller configuration file
└── .env                      # Environment variables file
```

## Requirements

- Python 3.7+
- `pyaudiowpatch`
- `groq`
- `faster-whisper`
- `python-dotenv`
- `PyQt5`
- [Other dependencies as listed in `requirements.txt`]

Install dependencies (if using `requirements.txt`):

```sh
pip install -r requirements.txt
```

## Usage

1. **Configure Environment:**
   Create a `.env` file in the project root directory and set your environment variables, most importantly your `GROQ_API_KEY`.  This file should be in the same directory as `main.py`.

   ```
   GROQ_API_KEY=YOUR_API_KEY_HERE
   ```

2. **Launch the Application:**
   Run the following command to launch Mikey's GUI:

   ```sh
   python main.py
   ```

   The graphical interface lets you:
   - Select system and microphone audio devices.
   - Start and stop audio recording.
   - View live logs and monitor transcription progress.
   - Open the recordings browser to explore saved sessions and view corresponding transcripts.

3. **Transcription Settings:**
   The GUI now provides several transcription options:
   - ☁️ Cloud-based (Groq) vs 🖥️ Local (faster-whisper) transcription
   - Model size selection (tradeoff between speed and accuracy)
   - Compute device selection (CPU, CUDA for Nvidia GPUs, MPS for Apple Silicon)

   Local transcription recommendations:
   - CPU: Use "tiny" or "base" models
   - CUDA: Up to "large" model

## Building an Executable

To package Mikey as a standalone executable, PyInstaller is used. The configuration is already set up in `main.spec`.

Before building, ensure you have FFmpeg binaries in the `bin` directory.  The `main.spec` (startLine: 5, endLine: 9) is configured to include FFmpeg based on your operating system (Windows, Linux, or macOS). You might need to download FFmpeg and place the executable in the `bin` folder.

To build the executable, run PyInstaller from the project root:

```sh
pyinstaller main.spec
```

This command will generate a `dist` folder containing the standalone executable. The `.env` file and `resources/favicon.ico` are automatically included in the executable, as configured in `main.spec` (startLine: 20, endLine: 23).

The executable will be located in `dist/MikeyV3` (or a similar name based on the `name` field in `main.spec` (startLine: 40)).

Make sure to test your executable on your target platform(s).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any bugs, performance improvements, or feature suggestions.

---

Happy Recording with Mikey!
