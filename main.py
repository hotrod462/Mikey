import os
from datetime import datetime
from tmnt.recorder import AudioRecorder


def main():
    recorder = AudioRecorder()
    
    # List available devices
    devices = recorder.list_audio_devices()
    print("Available Audio Devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']} (abs index: {device['index']})")

    choice = input("Select device index to record from (or press Enter for default): ")
    if choice.strip() == "":
        abs_device_index = None
    else:
        try:
            user_choice = int(choice)
            if user_choice < 0 or user_choice >= len(devices):
                raise ValueError("Invalid index")
            abs_device_index = devices[user_choice]['index']
        except Exception as e:
            print("Invalid selection. Using default device.")
            abs_device_index = None

    # Create a session folder under 'recordings' with a timestamp
    base_folder = "recordings"
    os.makedirs(base_folder, exist_ok=True)
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join(base_folder, session_timestamp)
    os.makedirs(session_folder, exist_ok=True)
    recorder.session_folder = session_folder
    print(f"Session folder created at: {session_folder}")
    
    recorder.start_recording(abs_device_index)
    input("Press Enter to stop recording...")
    
    # Stop recording, process noise reduction, and get the filename
    audio_file = recorder.stop_recording()
    
    # Transcribe the audio
    print("Transcribing audio...")
    transcription = recorder.transcribe_audio(audio_file)
    if transcription:
        print("\nTranscription:")
        print(transcription)
        recorder.save_transcription_as_md(transcription)
        
        print("Generating meeting notes from transcription...")
        meeting_notes = recorder.make_meeting_notes(transcription)
        print("\nMeeting Notes:")
        print(meeting_notes)


if __name__ == '__main__':
    main() 