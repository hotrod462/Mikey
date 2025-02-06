# Dictaker - AI Audio Note Taking App

Dictaker is a local AI note-taking application that records audio from your system's WASAPI loopback devices and transcribes it using Groq's Whisper model. It can capture both system audio and microphone input, making it perfect for taking notes during meetings, lectures, or any audio content.

## Features
- Records audio from any WASAPI loopback device (system audio or microphone)
- Automatically saves recordings as WAV files
- Transcribes audio using Groq's Whisper model
- Saves transcriptions as text files

## Requirements
- Windows OS (WASAPI support)
- Python 3.8 or higher
- Groq API key

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/dictaker.git
cd dictaker
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and add your Groq API key:
```
GROQ_API_KEY=your_api_key_here
```

## Usage

1. Run the application:
```bash
python audio_recorder.py
```

2. Select an audio device from the list of available WASAPI devices
3. Press Enter to start recording
4. Press Enter again to stop recording
5. The application will automatically save the audio file and generate a transcription

## Output Files
- Audio recordings are saved as WAV files with timestamps: `recording_YYYYMMDD_HHMMSS.wav`
- Transcriptions are saved as text files: `recording_YYYYMMDD_HHMMSS_transcription.txt`

## Note
Make sure you have the appropriate permissions to record audio from your system's devices.
