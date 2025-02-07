import os
from datetime import datetime
from tmnt.audio_recorder import AudioRecorder
from tmnt.audio_transcriber import AudioTranscriber
import threading
import time


def wait_for_enter():
    """Wait for user to press Enter."""
    input("Press Enter to stop recording...\n")


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
    
    # Sort all segments by the start time
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
    Ensure that the transcription segment is a dictionary.
    If it is not, attempt to convert it using the __dict__ attribute.
    """
    if isinstance(segment, dict):
        return segment
    try:
        return segment.__dict__
    except Exception as e:
        return {"start": 0, "end": 0, "text": str(segment)}


def main():
    # Create an AudioRecorder instance
    recorder = AudioRecorder()
    
    # List available audio devices
    devices = recorder.list_audio_devices()
    print("Available Audio Devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']} (abs index: {device['index']})")

    # Get system audio (loopback) device selection (manual only)
    print("\nSelect the system audio (loopback) device:")
    system_choice = input("Enter device index for system audio: ")
    try:
        user_choice = int(system_choice)
        if user_choice < 0 or user_choice >= len(devices):
            raise ValueError("Invalid index")
        system_device_index = devices[user_choice]['index']
    except Exception as e:
        print("Invalid system audio device selection. Exiting.")
        return

    # Get microphone device selection (manual)
    print("\nSelect the microphone device:")
    mic_choice = input("Enter device index for microphone: ")
    try:
        user_choice = int(mic_choice)
        if user_choice < 0 or user_choice >= len(devices):
            raise ValueError("Invalid index")
        mic_device_index = devices[user_choice]['index']
    except Exception as e:
        print("Invalid microphone selection. Exiting.")
        return

    # Create a session folder under 'recordings' with a timestamp
    base_folder = "recordings"
    os.makedirs(base_folder, exist_ok=True)
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(base_folder, session_timestamp)
    os.makedirs(session_folder, exist_ok=True)
    recorder.session_folder = session_folder
    print(f"Session folder created at: {session_folder}")
    
    # Perform the microphone profile switch before prompting to start recording
    print("\nSwitching microphone profile, please wait...")
    recorder.trigger_mic_profile_switch(mic_device_index)
    print("Microphone profile switch complete.\n")
    
    print("Press Enter to start recording...")
    input()
    
    # Start recording in a separate thread to allow manual stopping
    recording_result = {}
    def record():
        files = recorder.start_dual_streams(system_device_index, mic_device_index)
        recording_result['files'] = files

    rec_thread = threading.Thread(target=record)
    rec_thread.start()
    
    print("Recording started. Press Enter to stop recording...")
    wait_for_enter()  # Manual stop using user input
    recorder.is_recording = False
    rec_thread.join()
    
    system_file, mic_file = recording_result.get('files', (None, None))
    if not system_file or not mic_file:
        print("Recording failed.")
        return
    
    print(f"\nRecording complete.")
    print(f"System audio saved as: {system_file}")
    print(f"Microphone audio saved as: {mic_file}")
    
    # Flag to enable transcription for testing purposes
    ENABLE_TRANSCRIPTION = True
    
    if ENABLE_TRANSCRIPTION:
        # Initialize AudioTranscriber for transcription tasks
        transcriber = AudioTranscriber(session_folder)
        
        print("\nTranscribing system audio with timestamps...")
        system_transcription = transcriber.transcribe_audio(system_file, with_timestamps=True)
        print("\nTranscribing microphone audio with timestamps...")
        mic_transcription = transcriber.transcribe_audio(mic_file, with_timestamps=True)
        
        # If transcriptions are not in list form (due to an error), wrap them in a list for consistency
        if not isinstance(system_transcription, list):
            system_transcription = [{"start": 0, "end": 0, "text": system_transcription}]
        if not isinstance(mic_transcription, list):
            mic_transcription = [{"start": 0, "end": 0, "text": mic_transcription}]
        
        # Ensure each segment is a dictionary (in case the API returns custom objects)
        system_transcription = [ensure_dict(seg) for seg in system_transcription]
        mic_transcription = [ensure_dict(seg) for seg in mic_transcription]
        
        print("\nSystem Audio Transcription (with timestamps):")
        for seg in system_transcription:
            print(f"[{seg.get('start', 0):.2f} - {seg.get('end', 0):.2f}] {seg.get('text', '')}")
        transcriber.save_transcription_as_md(system_transcription, os.path.join(session_folder, "system_transcription.md"))
        
        print("\nMicrophone Audio Transcription (with timestamps):")
        for seg in mic_transcription:
            print(f"[{seg.get('start', 0):.2f} - {seg.get('end', 0):.2f}] {seg.get('text', '')}")
        transcriber.save_transcription_as_md(mic_transcription, os.path.join(session_folder, "mic_transcription.md"))
        
        # Merge the two transcripts into one conversation transcript file
        merged_transcript = merge_transcriptions(system_transcription, mic_transcription)
        merged_md_filename = os.path.join(session_folder, "merged_transcript.md")
        with open(merged_md_filename, "w", encoding="utf-8") as f:
            f.write(merged_transcript)
        print(f"\nMerged conversation transcript saved as: {merged_md_filename}")
    
    else:
        print("\nTranscription is currently disabled.")


if __name__ == '__main__':
    main() 