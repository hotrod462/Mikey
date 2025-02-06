# TMNT - Too Many Note Takers

TMNT (Too Many Note Takers) is an application for recording audio, transcribing it, and generating meeting notes automatically. It utilizes a modular design where core functionality is provided in the TMNT package, and a main entry point in main.py orchestrates the workflow.

## Features

- **Audio Recording:** Records audio from WASAPI loopback devices using pyaudiowpatch.
- **Noise Reduction & Processing:** Processes audio recordings using noisereduce to improve transcription quality.
- **Transcription:** Transcribes recorded audio using the Groq API (requires a valid GROQ_API_KEY).
- **Meeting Notes Generation:** Generates concise meeting notes from the transcription using a conversational model.

## Directory Structure

```
TMNT/
├── tmnt/
│   ├── __init__.py     # TMNT package initialization
│   └── recorder.py     # AudioRecorder class with all recording, transcription, and meeting notes functionality
├── recordings/         # Runtime folder for storing recordings, transcriptions, and meeting notes
├── main.py             # Application entry point
├── README.md           # Project overview and instructions
└── requirements.txt    # Project dependencies (optional)
```

## Requirements

- Python 3.7+
- pyaudiowpatch
- wave
- groq
- python-dotenv
- numpy
- noisereduce

Install dependencies (if using requirements.txt):

```sh
pip install -r requirements.txt
```

## Usage

1. Create a `.env` file in the root directory and set your environment variables (e.g., `GROQ_API_KEY`).
2. Run the application:

```sh
python main.py
```

Follow the prompts to select an audio device, start/stop the recording, and view the resulting transcription and meeting notes.

## Building an Executable

To compile TMNT as a standalone executable, consider using PyInstaller. For example:

```sh
pyinstaller --onefile main.py
```

This command bundles your application and dependencies into a single executable. Make sure to test the executable on your target platform(s).



## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any bugs or feature suggestions.
