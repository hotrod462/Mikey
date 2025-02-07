import pyaudiowpatch as pyaudio
import wave
import time
import os
import numpy as np
import noisereduce as nr
import threading
from queue import Queue


class AudioRecorder:
    def __init__(self, session_folder="."):
        self.CHUNK = 1024 *4
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 2
        self.RATE = 48000
        self.p = None
        self.stream = None
        self.session_folder = session_folder
        self.is_recording = False

    def list_audio_devices(self):
        p = pyaudio.PyAudio()
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
                if device_info.get('hostApi') == wasapi_host_index and device_info.get('maxInputChannels') > 0:
                    device_list.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'defaultSampleRate': device_info.get('defaultSampleRate')
                    })
        p.terminate()
        return device_list

    def start_recording(self, device_index=None):
        self.p = pyaudio.PyAudio()
        if device_index is None:
            devices = self.list_audio_devices()
            loopback_devices = [d for d in devices if "Loopback" in d['name']]
            if loopback_devices:
                device_index = loopback_devices[0]['index']
            else:
                raise ValueError("No loopback WASAPI device found.")
        device_info = self.p.get_device_info_by_index(device_index)
        self.RATE = int(device_info.get('defaultSampleRate'))
        self.CHANNELS = int(device_info.get('maxInputChannels'))
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
        self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def stop_recording(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        folder = self.session_folder
        filename = os.path.join(folder, "recording.wav")
        raw_audio = b''.join(self.frames)
        audio_data = np.frombuffer(raw_audio, dtype=np.float32)
        if self.CHANNELS > 1:
            audio_data = np.reshape(audio_data, (-1, self.CHANNELS))
        noise_sample_length = self.RATE
        if audio_data.shape[0] > noise_sample_length:
            noise_clip = audio_data[:noise_sample_length]
        else:
            noise_clip = audio_data
        if audio_data.ndim == 2 and audio_data.shape[1] > 1:
            audio_data_t = audio_data.T
            noise_clip_t = noise_clip.T
            reduced_channels = []
            for ch in range(audio_data_t.shape[0]):
                reduced_channel = nr.reduce_noise(
                    y=audio_data_t[ch],
                    y_noise=noise_clip_t[ch],
                    sr=self.RATE
                )
                reduced_channels.append(reduced_channel)
            reduced_audio = np.vstack(reduced_channels).T
        else:
            reduced_audio = nr.reduce_noise(
                y=audio_data,
                y_noise=noise_clip,
                sr=self.RATE
            )
        reduced_audio_clipped = np.clip(reduced_audio, -1.0, 1.0)
        final_audio = (reduced_audio_clipped * 32767).astype(np.int16)
        wf = wave.open(filename, 'wb')
        output_channels = 1 if final_audio.ndim == 1 else final_audio.shape[1]
        wf.setnchannels(output_channels)
        wf.setsampwidth(2)
        wf.setframerate(self.RATE)
        wf.writeframes(final_audio.tobytes())
        wf.close()
        print(f"Recording saved as {filename}")
        return filename

    def trigger_mic_profile_switch(self, mic_device_index, duration=2):
        print("Triggering microphone profile switch...")
        p = pyaudio.PyAudio()
        try:
            info = p.get_device_info_by_index(mic_device_index)
            channels = int(info.get('maxInputChannels'))
            rate = int(info.get('defaultSampleRate'))
            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=mic_device_index,
                frames_per_buffer=self.CHUNK
            )
            for _ in range(int(rate / self.CHUNK * duration)):
                stream.read(self.CHUNK, exception_on_overflow=False)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Error during profile switch: {e}")
        finally:
            p.terminate()
        print("Profile switch complete.")

    def _record_stream(self, device_index, format, channels, rate, queue, stream_type):
        """
        Modified _record_stream method with periodic flushing.
        This method records audio from a given device and, every `flush_interval` seconds,
        writes the current frames to a temporary file in the session folder. 
        At the end of the recording, all segments are merged and the temporary files are removed.
        """
        import time  # ensure time is imported here if not already

        segment_files = []         # List to store flushed segment file names.
        current_frames = []        # Buffer to accumulate frames between flushes.
        flush_interval = 60        # Flush every 60 seconds. Adjust as needed.
        last_flush_time = time.time()

        try:
            # Choose a smaller chunk size for system audio if desired.
            chunk_size = 1024 if stream_type == "system audio" else self.CHUNK

            # Build stream keyword arguments.
            stream_kwargs = {
                "format": format,
                "channels": channels,
                "rate": rate,
                "input": True,
                "input_device_index": device_index,
                "frames_per_buffer": chunk_size
            }

            # Open the stream using the shared PyAudio instance (self.p).
            stream = self.p.open(**stream_kwargs)
            print(f"Started recording {stream_type}")
            while self.is_recording:
                try:
                    # Read and buffer the incoming audio frames.
                    data = stream.read(chunk_size, exception_on_overflow=False)
                    current_frames.append(data)
                    
                    # Check if it's time to flush the buffer to disk.
                    if time.time() - last_flush_time >= flush_interval:
                        # Construct a temporary filename.
                        segment_filename = f"temp_{stream_type}_{int(time.time())}.raw"
                        full_path = os.path.join(self.session_folder, segment_filename)
                        # Write the buffered data to disk.
                        with open(full_path, "wb") as f:
                            f.write(b"".join(current_frames))
                        segment_files.append(full_path)
                        print(f"Flushed {stream_type} segment to {full_path}")
                        # Clear the in-memory buffer and update the last flush time.
                        current_frames = []
                        last_flush_time = time.time()
                except Exception as e:
                    print(f"Error reading from {stream_type}: {e}")
                    break  # Exit loop if there is a read error.

            # After the recording stops, flush any remaining frames.
            if current_frames:
                segment_filename = f"temp_{stream_type}_{int(time.time())}.raw"
                full_path = os.path.join(self.session_folder, segment_filename)
                with open(full_path, "wb") as f:
                    f.write(b"".join(current_frames))
                segment_files.append(full_path)
                print(f"Flushed final {stream_type} segment to {full_path}")

            stream.stop_stream()
            stream.close()

            # Merge all flushed segments into a single buffer.
            merged_frames = b"".join([open(seg, "rb").read() for seg in segment_files])

            # Optionally clean up the temporary segment files.
            for seg in segment_files:
                try:
                    os.remove(seg)
                except Exception as ee:
                    print(f"Could not remove temporary file {seg}: {ee}")

            # Pass a list with the merged buffer to the processing function.
            queue.put(([merged_frames], rate, channels, format))
            print(f"Finished recording {stream_type}")
        except Exception as e:
            print(f"Error setting up {stream_type} stream: {e}")
            queue.put(None)

    def _post_process_and_save(self, stream_data, filename):
        frames, rate, channels, format = stream_data
        if format == pyaudio.paFloat32:
            audio_data = np.frombuffer(b''.join(frames), dtype=np.float32)
        else:
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio_data = np.reshape(audio_data, (-1, channels))
        if audio_data.shape[0] > rate:
            noise_sample = audio_data[:rate]
            if audio_data.ndim == 2:
                reduced_channels = []
                for ch in range(channels):
                    reduced_channel = nr.reduce_noise(
                        y=audio_data[:, ch],
                        y_noise=noise_sample[:, ch],
                        sr=rate
                    )
                    reduced_channels.append(reduced_channel)
                reduced_audio = np.stack(reduced_channels, axis=1)
            else:
                reduced_audio = nr.reduce_noise(
                    y=audio_data,
                    y_noise=noise_sample,
                    sr=rate
                )
        else:
            reduced_audio = audio_data
        reduced_audio = np.clip(reduced_audio, -1.0, 1.0)
        final_audio = (reduced_audio * 32767).astype(np.int16)
        output_path = os.path.join(self.session_folder, filename)
        wf = wave.open(output_path, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(final_audio.tobytes())
        wf.close()
        print(f"Processed and saved {filename}")

    def start_dual_streams(self, system_device_index, mic_device_index):
        if system_device_index is None:
            raise ValueError("No system audio device selected. Please choose a system audio device manually.")
        
        # Create a shared PyAudio instance for both streams.
        self.p = pyaudio.PyAudio()
        
        try:
            sys_info = self.p.get_device_info_by_index(system_device_index)
            sys_channels = int(sys_info.get('maxInputChannels'))
            sys_rate = int(sys_info.get('defaultSampleRate'))
            mic_info = self.p.get_device_info_by_index(mic_device_index)
            mic_channels = int(mic_info.get('maxInputChannels'))
            mic_rate = int(mic_info.get('defaultSampleRate'))
        except Exception as e:
            self.p.terminate()
            raise e

        system_queue = Queue()
        mic_queue = Queue()
        self.is_recording = True
        system_thread = threading.Thread(
            target=self._record_stream,
            args=(system_device_index, self.FORMAT, sys_channels, sys_rate, system_queue, "system audio")
        )
        mic_thread = threading.Thread(
            target=self._record_stream,
            args=(mic_device_index, pyaudio.paInt16, mic_channels, mic_rate, mic_queue, "microphone")
        )
        print("Starting parallel recording...")
        system_thread.start()
        mic_thread.start()
        system_thread.join()
        mic_thread.join()
        
        system_data = system_queue.get()
        mic_data = mic_queue.get()
        if system_data is None or mic_data is None:
            self.p.terminate()
            raise RuntimeError("Recording failed for one or both streams")
        
        self._post_process_and_save(system_data, "system_audio.wav")
        self._post_process_and_save(mic_data, "mic_audio.wav")
        
        # Terminate the shared PyAudio instance once done.
        self.p.terminate()
        return os.path.join(self.session_folder, "system_audio.wav"), os.path.join(self.session_folder, "mic_audio.wav") 