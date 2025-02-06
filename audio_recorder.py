import pyaudiowpatch as pyaudio
import wave
import time
import os
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import numpy as np
import noisereduce as nr

# Load environment variables
load_dotenv()

class AudioRecorder:
    def __init__(self):
        self.CHUNK = 1024 * 4
        self.FORMAT = pyaudio.paFloat32
        self.CHANNELS = 2
        self.RATE = 48000
        self.p = None
        self.stream = None

        # Initialize Groq client for transcription and text generation
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.groq_client = Groq(api_key=api_key)

    def list_audio_devices(self):
        """List all available WASAPI loopback devices using absolute device indices."""
        p = pyaudio.PyAudio()
        # Find the WASAPI host API index
        wasapi_host_index = None
        for i in range(p.get_host_api_count()):
            api_info = p.get_host_api_info_by_index(i)
            if api_info.get("type") == pyaudio.paWASAPI:
                wasapi_host_index = i
                break
        
        device_list = []
        if wasapi_host_index is not None:
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                # Filter to devices belonging to WASAPI and that have input channels
                if device_info.get('hostApi') == wasapi_host_index and device_info.get('maxInputChannels') > 0:
                    device_list.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'defaultSampleRate': device_info.get('defaultSampleRate')
                    })
        p.terminate()
        return device_list

    def start_recording(self, device_index=None):
        """Start recording audio from the specified WASAPI loopback device using absolute device indices."""
        self.p = pyaudio.PyAudio()
        
        # If no device index specified, select a default loopback device (one with 'Loopback' in its name)
        if device_index is None:
            devices = self.list_audio_devices()
            loopback_devices = [d for d in devices if "Loopback" in d['name']]
            if loopback_devices:
                device_index = loopback_devices[0]['index']
            else:
                raise ValueError("No loopback WASAPI device found.")
        
        # Fetch device info using absolute index
        device_info = self.p.get_device_info_by_index(device_index)
        self.RATE = int(device_info.get('defaultSampleRate'))
        self.CHANNELS = int(device_info.get('maxInputChannels'))
        # If the device reports zero channels (which may happen for some loopback devices), default to 2
        if self.CHANNELS < 1:
            self.CHANNELS = 2
        print(f"Using sample rate: {self.RATE}, channels: {self.CHANNELS} from device: {device_info.get('name')}")
        
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=device_index,
            stream_callback=self._callback
        )

        self.frames = []
        self.stream.start_stream()
        print("Recording started...")

    def _callback(self, in_data, frame_count, time_info, status):
        """Callback function for audio stream."""
        self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        """Stop recording, process noise reduction, reduce quality, and save the audio file."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.p:
            self.p.terminate()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        
        # Combine recorded frames into a single bytes object
        raw_audio = b''.join(self.frames)
        # Convert bytes to a NumPy array of float32 values (matching paFloat32)
        audio_data = np.frombuffer(raw_audio, dtype=np.float32)
        # Reshape the array if recording in multiple channels
        if self.CHANNELS > 1:
            audio_data = np.reshape(audio_data, (-1, self.CHANNELS))
        
        # Use the first second of audio as the noise sample (adjust if needed)
        noise_sample_length = self.RATE  # one second worth of frames
        if audio_data.shape[0] > noise_sample_length:
            noise_clip = audio_data[:noise_sample_length]
        else:
            noise_clip = audio_data

        # Process noise reduction:
        # noisereduce expects a 1D array; if audio is multi-channel,
        # process each channel separately.
        if audio_data.ndim == 2 and audio_data.shape[1] > 1:
            # Transpose so that shape becomes (channels, samples)
            audio_data_t = audio_data.T  # shape: (channels, samples)
            noise_clip_t = noise_clip.T  # shape: (channels, samples)
            reduced_channels = []
            for ch in range(audio_data_t.shape[0]):
                reduced_channel = nr.reduce_noise(
                    y=audio_data_t[ch],
                    y_noise=noise_clip_t[ch],
                    sr=self.RATE,
                    
                )
                reduced_channels.append(reduced_channel)
            # Stack and transpose back to shape (samples, channels)
            reduced_audio = np.vstack(reduced_channels).T
        else:
            reduced_audio = nr.reduce_noise(
                y=audio_data,
                y_noise=noise_clip,
                sr=self.RATE,
                
            )

        # Convert the reduced audio to 16-bit PCM to reduce file size and quality.
        # Clamp values to [-1.0, 1.0] then scale to the 16-bit integer range.
        reduced_audio_clipped = np.clip(reduced_audio, -1.0, 1.0)
        final_audio = (reduced_audio_clipped * 32767).astype(np.int16)
        
        # Save the processed audio as a 16-bit WAV file
        wf = wave.open(filename, 'wb')
        # Determine number of output channels
        output_channels = 1 if final_audio.ndim == 1 else final_audio.shape[1]
        wf.setnchannels(output_channels)
        wf.setsampwidth(2)  # 2 bytes per sample for 16-bit audio
        wf.setframerate(self.RATE)
        wf.writeframes(final_audio.tobytes())
        wf.close()
        
        print(f"Recording saved as {filename}")
        return filename

    def transcribe_audio(self, audio_file):
        """Transcribe recorded audio using the Groq whisper-large-v3-turbo model."""
        with open(audio_file, "rb") as f:
            audio_data = f.read()
        print("Transcribing audio using Groq whisper-large-v3-turbo model...")
        try:
            response = self.groq_client.audio.transcriptions.create(
                file=(audio_file, audio_data),
                model="whisper-large-v3-turbo",
                prompt="Transcribe the audio as accurately as possible.",
                response_format="json",
                language="en",
                temperature=0.0
            )
            # Assuming the response contains a `.text` attribute with the transcription.
            transcription = response.text
            print("Transcription complete.")
        except Exception as e:
            transcription = f"Transcription error: {e}"
        return transcription

    def save_transcription_as_md(self, transcription, md_filename=None):
        """
        Save the transcription text to a markdown (.md) file.
        If md_filename is not provided, a default file name is generated using the current timestamp.
        """
        if not md_filename:
            md_filename = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_filename, "w", encoding="utf-8") as file:
            file.write("# Transcription\n\n")
            file.write(transcription)
        print(f"Transcription saved as {md_filename}")
        return md_filename

    def make_meeting_notes(self, transcription, notes_md_filename=None):
        """
        Generate meeting notes from the transcribed text using the Groq llama3.370b versatile model,
        and save them to a markdown (.md) file.
        """
        print("Generating meeting notes using Groq llama3.370b versatile model...")
        prompt = (
            "Based on the following transcription, generate concise meeting notes including key discussion points, "
            "decisions, and action items:\n\n"
            f"{transcription}"
        )
        try:
            response = self.groq_client.text.completions.create(
                prompt=prompt,
                model="llama3.3-70b-versatile",     
                temperature=0.0
            )
            meeting_notes = response.text
            print("Meeting notes generated successfully.")
        except Exception as e:
            meeting_notes = f"Meeting notes generation error: {e}"
        
        if not notes_md_filename:
            notes_md_filename = f"meeting_notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(notes_md_filename, "w", encoding="utf-8") as file:
            file.write("# Meeting Notes\n\n")
            file.write(meeting_notes)
        print(f"Meeting notes saved as {notes_md_filename}")
        return meeting_notes


def main():
    recorder = AudioRecorder()
    
    # List available devices
    devices = recorder.list_audio_devices()
    print("Available Audio Devices:")
    # Display index as the sequential choice and show absolute device index
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
    
    recorder.start_recording(abs_device_index)
    input("Press Enter to stop recording...")
    
    # Stop recording, denoise the audio, and get the filename
    audio_file = recorder.stop_recording()
    
    # Transcribe the audio (functionality disabled)
    print("Transcribing audio...")
    transcription = recorder.transcribe_audio(audio_file)
    if transcription:
        print("\nTranscription:")
        print(transcription)
        # Save the transcription to a markdown file
        recorder.save_transcription_as_md(transcription)
        
        print("Generating meeting notes from transcription...")
        meeting_notes = recorder.make_meeting_notes(transcription)
        print("\nMeeting Notes:")
        print(meeting_notes)


if __name__ == "__main__":
    main() 