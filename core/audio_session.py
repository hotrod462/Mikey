import os
import threading
from datetime import datetime
import re
from pathlib import Path

from mikey.audio_recorder import AudioRecorder
from mikey.audio_transcriber import AudioTranscriber

class RecordingSession:
    def __init__(self, system_device_index, mic_device_index, base_folder="recordings"):
        self.system_device_index = system_device_index
        self.mic_device_index = mic_device_index

        # Create a session folder with a timestamp.
        os.makedirs(base_folder, exist_ok=True)
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = os.path.join(base_folder, session_timestamp)
        os.makedirs(self.session_folder, exist_ok=True)

        # Create an AudioRecorder instance.
        self.recorder = AudioRecorder(session_folder=self.session_folder)
        self.files = None

    def record(self):
        """
        Switch microphone profile and record both streams.
        Calls AudioRecorder.trigger_mic_profile_switch first; then starts dual streams.
        """
        # Do the profile switch for the microphone.
        self.recorder.trigger_mic_profile_switch(self.mic_device_index)
        # This call will record both system and mic audio.
        self.files = self.recorder.start_dual_streams(self.system_device_index, self.mic_device_index)
        return self.files

    def stop(self):
        """
        Signal the recorder to stop recording.
        """
        self.recorder.is_recording = False

    def transcribe(self, enable_transcription=True):
        """
        Perform transcription on the recorded files using AudioTranscriber.
        Processes the transcription of the system (device) audio and mic audio in separate requests.
        Returns a dictionary with the merged transcription as well as individual transcriptions.
        """
        if not enable_transcription or not self.files:
            return None

        system_file, mic_file = self.files

        print("Transcribing system audio...")
        system_transcriber = AudioTranscriber(Path(system_file), session_folder=Path(self.session_folder))
        system_transcription_result = system_transcriber.transcribe()
        print("System audio transcription complete.")

        print("Transcribing mic audio...")
        mic_transcriber = AudioTranscriber(Path(mic_file), session_folder=Path(self.session_folder))
        mic_transcription_result = mic_transcriber.transcribe()
        print("Mic audio transcription complete.")

        system_transcription_text = system_transcription_result.get("text", "")
        mic_transcription_text = mic_transcription_result.get("text", "")

        return {
            "merged": system_transcription_text + "\n\n" + mic_transcription_text,
            "system": system_transcription_text,
            "mic": mic_transcription_text
        }

    @classmethod
    def from_existing_session(cls, session_folder, system_device_index=0, mic_device_index=0):
        """
        Create a RecordingSession instance from an existing session folder.
        This method does not create a new session folder but sets up the instance using the provided folder.
        It also attempts to auto-detect audio files in the folder and set them as the files attribute.
        """
        # Instantiate without creating a new folder.
        obj = cls(system_device_index, mic_device_index, base_folder=os.path.dirname(session_folder))
        obj.session_folder = session_folder
        # Auto-detect audio files (excluding markdown files).
        audio_files = [
            os.path.join(session_folder, f)
            for f in os.listdir(session_folder)
            if os.path.isfile(os.path.join(session_folder, f)) and not f.endswith(".md")
        ]
        if len(audio_files) >= 2:
            system_file = None
            mic_file = None
            for af in audio_files:
                lower_af = af.lower()
                if "mic" in lower_af:
                    mic_file = af
                elif "system" in lower_af or "device" in lower_af:
                    system_file = af
            if system_file is None or mic_file is None:
                audio_files.sort()
                system_file = audio_files[0]
                mic_file = audio_files[1]
            obj.files = (system_file, mic_file)
        return obj
