import pyaudiowpatch as pyaudio
import wave


def list_devices(p):
    print("Available audio devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Device Index: {i}")
        print(f"  Name: {info.get('name')}")
        print(f"  Max Input Channels: {info.get('maxInputChannels')}")
        print(f"  Default Sample Rate: {info.get('defaultSampleRate')}")
        print("-" * 40)


def test_stream_format(device_index, sample_format, format_name):
    p = pyaudio.PyAudio()
    try:
        info = p.get_device_info_by_index(device_index)
        channels = int(info.get('maxInputChannels'))
        rate = int(info.get('defaultSampleRate'))
        print(f"\nTesting device {device_index} ({info.get('name')}) with {channels} channel(s), sample rate: {rate}, format: {format_name}")
        if channels < 1:
            print("Device has less than 1 input channel, skipping.")
            return

        stream = p.open(
            format=sample_format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        print("Stream opened successfully. Reading one chunk...")
        data = stream.read(1024)
        print(f"Read {len(data)} bytes from the stream.")
        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"Error testing device {device_index} with {format_name}: {e}")
    finally:
        p.terminate()


# New function to open an input stream for a set duration to trigger profile switch
def trigger_profile_switch(device_index, duration_seconds):
    p = pyaudio.PyAudio()
    try:
        info = p.get_device_info_by_index(device_index)
        channels = int(info.get('maxInputChannels'))
        rate = int(info.get('defaultSampleRate'))
        sample_format = pyaudio.paInt16
        print(f"\nTriggering profile switch by opening input stream on device {device_index} ({info.get('name')}) for {duration_seconds} seconds.")
        stream = p.open(
            format=sample_format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        num_chunks = int(rate / 1024 * duration_seconds)
        for i in range(num_chunks):
            stream.read(1024)
        stream.stop_stream()
        stream.close()
        print("Finished triggering profile switch.")
    except Exception as e:
        print(f"Error triggering profile switch: {e}")
    finally:
        p.terminate()


# New function to record audio for a specified duration and save to a WAV file
def record_and_save(device_index, sample_format, format_name, duration_seconds, filename):
    p = pyaudio.PyAudio()
    try:
        info = p.get_device_info_by_index(device_index)
        channels = int(info.get('maxInputChannels'))
        rate = int(info.get('defaultSampleRate'))
        frames = []
        num_chunks = int(rate / 1024 * duration_seconds)
        print(f"Recording from device {device_index} ({info.get('name')}) for {duration_seconds} seconds using {format_name}.")
        stream = p.open(
            format=sample_format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        for i in range(num_chunks):
            data = stream.read(1024)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        wf = wave.open(filename, "wb")
        wf.setnchannels(channels)
        sample_width = p.get_sample_size(sample_format)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(b"".join(frames))
        wf.close()
        print(f"Recording saved as {filename}.")
    except Exception as e:
        print(f"Error recording device {device_index} with {format_name}: {e}")
    finally:
        p.terminate()


if __name__ == '__main__':
    # List all available audio devices so you can choose the right ones
    p = pyaudio.PyAudio()
    list_devices(p)
    p.terminate()

    # Replace with the appropriate device indices based on the printed device list:
    # For microphone audio (e.g., AirPods microphone)
    microphone_device_index = 15  # Modify this value according to your setup
    # For system audio capture (e.g., loopback or 'Stereo Mix' device)
    system_audio_device_index = 16  # Modify this value according to your setup

    # --- Testing System Audio ---
    print("\n--- Testing System Audio ---")
    test_stream_format(system_audio_device_index, pyaudio.paFloat32, "paFloat32")
    test_stream_format(system_audio_device_index, pyaudio.paInt16, "paInt16")
    print("\nRecording system audio for 5 seconds:")
    record_and_save(system_audio_device_index, pyaudio.paInt16, "paInt16", 5, "system_audioint16.wav")
    record_and_save(system_audio_device_index, pyaudio.paFloat32, "paFloat32", 5, "system_audiofloat32.wav")


    # --- Testing Microphone Audio ---
    # If needed, trigger the OS to switch the microphone profile (applicable for some Bluetooth devices)
    trigger_profile_switch(microphone_device_index, 5)
    print("\n--- Testing Microphone Audio ---")
    test_stream_format(microphone_device_index, pyaudio.paFloat32, "paFloat32")
    test_stream_format(microphone_device_index, pyaudio.paInt16, "paInt16")
    print("\nRecording microphone audio for 5 seconds:")
    record_and_save(microphone_device_index, pyaudio.paInt16, "paInt16", 5, "microphone_audio.wav") 