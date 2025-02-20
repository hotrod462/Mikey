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
        self.base_folder = base_folder
        self.session_folder = None  # Will be created when record() is called.
        self.recorder = None
        self.files = None

    def record(self):
        """
        Switch microphone profile and record both streams.
        """
        if not self.session_folder:
            # Create a session folder with a timestamp at the actual start of recording.
            os.makedirs(self.base_folder, exist_ok=True)
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_folder = os.path.join(self.base_folder, session_timestamp)
            os.makedirs(self.session_folder, exist_ok=True)
            # Now that the folder is created, instantiate the recorder.
            self.recorder = AudioRecorder(session_folder=self.session_folder)

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

    def transcribe(self, enable_transcription=True, use_local: bool = False,
                   model_size: str = "base", device: str = "cpu"):
        """
        Perform transcription on the recorded files using AudioTranscriber.
        Processes the transcription of the system (device) audio and mic audio in separate requests.
        Uses merge_device_and_mic_transcripts to merge the two transcripts for a natural conversation flow.
        Returns a dictionary with the merged transcription as well as individual transcriptions.
        
        Parameters match AudioTranscriber defaults:
        - use_local: False (cloud-based transcription)
        - model_size: "base" (Whisper model size)
        - device: "cpu" (compute device)
        """
        if not enable_transcription or not self.files:
            return None

        system_file, mic_file = self.files

        print("Transcribing system audio...")
        system_transcriber = AudioTranscriber(
            Path(system_file), 
            session_folder=Path(self.session_folder),
            use_local=use_local,
            model_size=model_size,
            device=device
        )
        system_transcription_result = system_transcriber.transcribe()
        print("System audio transcription complete.")

        print("Transcribing mic audio...")
        mic_transcriber = AudioTranscriber(
            Path(mic_file), 
            session_folder=Path(self.session_folder),
            use_local=use_local,
            model_size=model_size,
            device=device
        )
        mic_transcription_result = mic_transcriber.transcribe()
        print("Mic audio transcription complete.")

        # Merge the two transcripts using the new method in AudioTranscriber
        merged_transcript = system_transcriber.merge_device_and_mic_transcripts(
            system_transcription_result, mic_transcription_result
        )

        return {
            "merged": merged_transcript.get("text", ""),
            "merged_segments": merged_transcript.get("segments", []),
            "system": system_transcription_result.get("text", ""),
            "mic": mic_transcription_result.get("text", "")
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

        # Filter for raw audio files only
        valid_extensions = {'.wav', '.mp3', '.flac', '.m4a'}
        audio_files = [
            os.path.join(session_folder, f)
            for f in os.listdir(session_folder)
            if os.path.isfile(os.path.join(session_folder, f)) and os.path.splitext(f)[1].lower() in valid_extensions
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
