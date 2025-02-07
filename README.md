# Mikey - Audio Recorder and Transcriber

Mikey is an application for recording audio, transcribing it using the Groq API, and generating meeting notes automatically. With a user-friendly graphical interface built in PyQt, Mikey provides a seamless experience for managing recordings, viewing transcriptions, and exploring saved sessions.

## Features

- **Audio Recording:** Records audio from WASAPI loopback devices using `pyaudiowpatch`.
- **Transcription:** Transcribes recorded audio using the Groq API (requires a valid `GROQ_API_KEY` in your environment variables).
- **Meeting Notes Generation:** Generates concise meeting notes from the transcription using a conversational model.
- **Recordings Browser:** Browse your session recordings with a dedicated two-panel window; the left panel lists session timestamps and the right panel displays the generated transcript.
- **Favicon Support:** Custom window icon for a polished appearance.

## Directory Structure

```
Mikey/
├── core/
│   └── audio_session.py      # High-level session orchestration for recording, transcription, and merging
├── gui/
│   ├── main_window.py        # PyQt-based main GUI for recording, transcription, and managing sessions
│   └── recordings_window.py  # Two-panel recordings browser: left for session timestamps, right for transcript display
├── tmnt/
│   ├── __init__.py           # Legacy initialization for the underlying functionality
│   ├── audio_recorder.py     # AudioRecorder class for capturing audio data
│   └── audio_transcriber.py  # AudioTranscriber class for transcription and meeting notes generation
├── recordings/               # Directory for storing recordings, transcripts, and meeting notes
├── main.py                   # Application entry point (launches the PyQt GUI)
├── README.md                 # Project overview and instructions
└── requirements.txt          # Project dependencies
```

## Requirements

- Python 3.7+
- `pyaudiowpatch`
- `groq`
- `python-dotenv`
- `PyQt5`
- [Other dependencies as listed in `requirements.txt`]

Install dependencies (if using `requirements.txt`):

```sh
pip install -r requirements.txt
```

## Usage

1. **Configure Environment:**  
   Create a `.env` file in the project root directory and set your environment variables (e.g., `GROQ_API_KEY`).

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

## Building an Executable

To package Mikey as a standalone executable, consider using PyInstaller. For example:

```sh
pyinstaller --onefile main.py
```

This command bundles your application and its dependencies into a single executable. Make sure to test your executable on your target platform(s).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any bugs, performance improvements, or feature suggestions.

---

Happy Recording with Mikey!
