import os
from groq import Groq
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pathlib import Path


class AudioTranscriber:
    def __init__(self, session_folder="."):
        load_dotenv()
        self.session_folder = session_folder

        # Initialize Groq client for generating meeting notes.
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.groq_client = Groq(api_key=groq_api_key)

        # Initialize Google Gemini client for audio transcription.
        self.gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))



    def transcribe_audio(self, audio_file, with_timestamps=True):
        """
        Transcribe recorded audio using the Google Gemini gemini-2.0-flash model.

        Accepts either a single audio file path (as a string) or a list of audio file paths.
        If with_timestamps is False, returns the transcription text.
        If with_timestamps is True, includes timestamps in the transcript.
        """
        try:
            print("Uploading audio file(s) for transcription using Gemini model...")
            
            # Check if audio_file is a list (multiple files) or a single file.
            if isinstance(audio_file, list):
                audio_file_objs = []
                for af in audio_file:
                    audio_file_obj = self.gemini_client.files.upload(
                        file=f"{af}"
                    )
                    audio_file_objs.append(audio_file_obj)
            else:
                audio_file_objs = [self.gemini_client.files.upload(
                    file=f"{audio_file}"
                )]

            if with_timestamps:
                prompt = (
                    "Generate a transcript of the speech with timestamps indicating "
                    "the start and end times for each segment with the speaker's name.eg: [HH:MM:SS] - [HH:MM:SS] -Mike: This is a test. "
                    "IMPORTANT: Do not include any other text in your response except the timestamps and the text of the transcript."
                )
            else:


                prompt = "Generate a transcript of the speech."


            # Combine the prompt with the audio file object(s).
            contents = [prompt] + audio_file_objs

            response = self.gemini_client.models.generate_content(
                model="gemini-1.5-pro",
                contents=contents
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
            # Write the whole transcription text directly
            file.write(transcription)
        print(f"Transcription saved as {md_filename}")
        return md_filename

    def make_meeting_notes(self, transcription, notes_md_filename=None):
        """Generate meeting notes from the transcription using the Groq llama-3.3-70b versatile model."""
        print("Generating meeting notes using Groq llama-3.3-70b versatile model...")
        if isinstance(transcription, list):
            try:
                transcription_text = "\n".join([seg.text for seg in transcription])
            except AttributeError:
                transcription_text = "\n".join([seg.get("text", "") for seg in transcription])
        else:
            transcription_text = transcription
        messages = [
            {"role": "system", "content": "You are a meeting notes assistant."},
            {"role": "user", "content": f"Based on the following transcription, generate concise meeting notes including key discussion points, decisions, and action items:\n\n{transcription_text}"}
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