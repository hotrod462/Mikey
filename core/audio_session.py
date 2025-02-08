import os
import threading
from datetime import datetime
import re

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

def convert_time_str_to_seconds(time_str):
    """
    Convert a time string in HH:MM:SS format to total seconds.
    """
    h, m, s = map(int, time_str.split(":"))
    return h * 3600 + m * 60 + s

def parse_transcript_text(transcript_text, default_speaker):
    """
    Parse a transcript text in markdown format into a list of segments.
    Assumes each segment line is formatted as:
    [HH:MM:SS] - [HH:MM:SS] - [OptionalSpeaker: ]Text
    Returns a list of dictionaries with keys: start, end, speaker, text.
    """
    segments = []
    lines = transcript_text.splitlines()
    pattern = r"^\[(\d{2}:\d{2}:\d{2})\]\s*-\s*\[(\d{2}:\d{2}:\d{2})\]\s*(?:-\s*)?(?:(\w+):)?\s*(.+)$"
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(pattern, line)
        if match:
            start_str = match.group(1)
            end_str = match.group(2)
            # Override any speaker information with the provided default.
            text = match.group(4)
            start = convert_time_str_to_seconds(start_str)
            end = convert_time_str_to_seconds(end_str)
            segments.append({
                "start": start,
                "end": end,
                "speaker": default_speaker,
                "text": text
            })
    return segments

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
        Parses each transcript based on timestamps and then stitches them together in a merged markdown transcript.
        Returns a dictionary with the merged transcription as well as individual transcriptions.
        """
        if not enable_transcription or not self.files:
            return None

        system_file, mic_file = self.files
        transcriber = AudioTranscriber(self.session_folder)

        # Transcribe each audio file separately.
        system_transcription_text = transcriber.transcribe_audio(system_file, with_timestamps=True)
        mic_transcription_text = transcriber.transcribe_audio(mic_file, with_timestamps=True)

        # Parse the individual transcription texts into segments.
        system_segments = parse_transcript_text(system_transcription_text, default_speaker="Device")
        mic_segments = parse_transcript_text(mic_transcription_text, default_speaker="Mic")

        # Merge the segments based on their timestamps.
        merged_transcription_md = merge_transcriptions(system_segments, mic_segments)

        return {
            "merged": merged_transcription_md,
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
