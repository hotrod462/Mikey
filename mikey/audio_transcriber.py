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
                    "do not transcribe filler words like 'um', 'like', 'you know', 'okay', 'mhm', etc."
                    "IMPORTANT: Do not include any other text in your response except the timestamps and the text of the transcript."
                )
            else:


                prompt = "Generate a transcript of the speech."


            # Combine the prompt with the audio file object(s).
            contents = [prompt] + audio_file_objs

            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents
            )
            transcription = response.text
            print("Transcription complete.")
        except Exception as e:
            transcription = f"Transcription error: {e}"
        return transcription

    def make_meeting_notes(self, transcription, notes_md_filename=None):
        """
        Generate meeting notes from the transcription using the Google Gemini model.
        The function now only returns the meeting notes without saving them to disk.
        """
        print("Generating meeting notes using Google Gemini model...")
        if isinstance(transcription, list):
            try:
                transcription_text = "\n".join([seg.text for seg in transcription])
            except AttributeError:
                transcription_text = "\n".join([seg.get("text", "") for seg in transcription])
        else:
            transcription_text = transcription

        prompt = (
            "You are a meeting notes assistant. Based on the following transcription, generate concise meeting notes "
            "including key discussion points, decisions, and action items:\n\n"
            f"{transcription_text}"
        )

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
            meeting_notes = response.text
            print("Meeting notes generated successfully.")
        except Exception as e:
            meeting_notes = f"Meeting notes generation error: {e}"
        
        # Removed the file-saving code here since saving is now handled via core/utils.py.
        return meeting_notes