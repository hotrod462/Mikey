import os
from datetime import datetime
from tmnt.audio_recorder import AudioRecorder
from tmnt.audio_transcriber import AudioTranscriber
import threading
import time


def wait_for_enter():
    """Wait for user to press Enter."""
    input("Press Enter to stop recording...\n")


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
    
    # Initialize AudioTranscriber for transcription tasks
    transcriber = AudioTranscriber(session_folder)
    
    print("\nTranscribing system audio...")
    system_transcription = transcriber.transcribe_audio(system_file)
    print("\nTranscribing microphone audio...")
    mic_transcription = transcriber.transcribe_audio(mic_file)
    
    if system_transcription:
        print("\nSystem Audio Transcription:")
        print(system_transcription)
        transcriber.save_transcription_as_md(system_transcription, os.path.join(session_folder, "system_transcription.md"))
        
        print("\nGenerating meeting notes from system audio transcription...")
        system_notes = transcriber.make_meeting_notes(system_transcription, os.path.join(session_folder, "system_meeting_notes.md"))
        print("\nSystem Audio Meeting Notes:")
        print(system_notes)
    
    if mic_transcription:
        print("\nMicrophone Audio Transcription:")
        print(mic_transcription)
        transcriber.save_transcription_as_md(mic_transcription, os.path.join(session_folder, "mic_transcription.md"))
        
        print("\nGenerating meeting notes from microphone transcription...")
        mic_notes = transcriber.make_meeting_notes(mic_transcription, os.path.join(session_folder, "mic_meeting_notes.md"))
        print("\nMicrophone Audio Meeting Notes:")
        print(mic_notes)


if __name__ == '__main__':
    main() 