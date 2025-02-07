import os
from groq import Groq
from dotenv import load_dotenv


class AudioTranscriber:
    def __init__(self, session_folder="."):
        load_dotenv()
        self.session_folder = session_folder
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.groq_client = Groq(api_key=api_key)

    def transcribe_audio(self, audio_file):
        """Transcribe recorded audio using the Groq whisper-large-v3 model."""
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        print("Transcribing audio using Groq whisper-large-v3 model...")
        try:
            response = self.groq_client.audio.transcriptions.create(
                file=(audio_file, audio_data),
                model="distil-whisper-large-v3-en",
                prompt="Transcribe the audio as accurately as possible.",
                response_format="json",
                language="en",
                temperature=0.0
            )
            transcription = response.text
            print("Transcription complete.")
        except Exception as e:
            transcription = f"Transcription error: {e}"
        return transcription

    def save_transcription_as_md(self, transcription, md_filename=None):
        """Save the transcription text to a markdown file."""
        folder = self.session_folder
        if not md_filename:
            md_filename = os.path.join(folder, "transcription.md")
        with open(md_filename, "w", encoding="utf-8") as file:
            file.write("# Transcription\n\n")
            file.write(transcription)
        print(f"Transcription saved as {md_filename}")
        return md_filename

    def make_meeting_notes(self, transcription, notes_md_filename=None):
        """Generate meeting notes from the transcription using the Groq llama-3.3-70b versatile model."""
        print("Generating meeting notes using Groq llama-3.3-70b versatile model...")
        messages = [
            {"role": "system", "content": "You are a meeting notes assistant."},
            {"role": "user", "content": f"Based on the following transcription, generate concise meeting notes including key discussion points, decisions, and action items:\n\n{transcription}"}
        ]
        try:
            response = self.groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.0
            )
            meeting_notes = response.choices[0].message.content
            print("Meeting notes generated successfully.")
        except Exception as e:
            meeting_notes = f"Meeting notes generation error: {e}"
        folder = self.session_folder
        if not notes_md_filename:
            notes_md_filename = os.path.join(folder, "meeting_notes.md")
        with open(notes_md_filename, "w", encoding="utf-8") as file:
            file.write("# Meeting Notes\n\n")
            file.write(meeting_notes)
        print(f"Meeting notes saved as {notes_md_filename}")
        return meeting_notes 