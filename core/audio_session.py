import os
import threading
from datetime import datetime

from mikey.audio_recorder import AudioRecorder
from mikey.audio_transcriber import AudioTranscriber

def merge_transcriptions(system_segments, mic_segments):
    """
    Merge transcription segments from system (device) audio and microphone audio into a single transcript.
    Each segment is tagged with a speaker label and sorted by start time.
    Returns the merged transcript as a markdown-formatted string.
    """
    merged = []
    for seg in system_segments:
        merged.append({
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "speaker": "Device",
            "text": seg.get("text", "")
        })
    for seg in mic_segments:
        merged.append({
            "start": seg.get("start", 0),
            "end": seg.get("end", 0),
            "speaker": "Mic",
            "text": seg.get("text", "")
        })

    # Sort segments by start time.
    merged_sorted = sorted(merged, key=lambda x: x["start"])

    def format_time(seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    transcript_md = "# Merged Conversation Transcript\n\n"
    for seg in merged_sorted:
        transcript_md += f"[{format_time(seg['start'])} - {format_time(seg['end'])}] {seg['speaker']}: {seg['text']}\n\n"
    return transcript_md

def ensure_dict(segment):
    """
    Ensure the transcription segment is a dictionary.
    If not, try converting using __dict__.
    """
    if isinstance(segment, dict):
        return segment
    try:
        return segment.__dict__
    except Exception:
        return {"start": 0, "end": 0, "text": str(segment)}

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
        Returns a dictionary with the merged transcription.
        Transcriptions are handled by Google Gemini and are returned as a complete unified text block.
        """
        if not enable_transcription or not self.files:
            return None

        system_file, mic_file = self.files
        transcriber = AudioTranscriber(self.session_folder)
        # Pass both system and mic recordings together in one API call.
        merged_transcription_text = transcriber.transcribe_audio([system_file, mic_file], with_timestamps=True)

        return {
            "merged": merged_transcription_text
        }
