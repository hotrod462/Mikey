import os
import json
import time
import subprocess
import tempfile
import re
from datetime import datetime
from pathlib import Path
from pydub import AudioSegment
from groq import Groq, RateLimitError
from core.utils import get_base_path, get_ffmpeg_path

# Set AudioSegment.converter to our bundled ffmpeg path
AudioSegment.converter = get_ffmpeg_path()

class AudioTranscriber:
    def __init__(self, audio_path: Path, chunk_length: int = 600, overlap: int = 10, session_folder: Path = None):
        """
        Initialize the AudioTranscriber with the given parameters.
        """
        self.audio_path = audio_path
        self.chunk_length = chunk_length  # in seconds
        self.overlap = overlap  # in seconds
        self.session_folder = session_folder or Path("recordings/session_temp")
        self.session_folder.mkdir(parents=True, exist_ok=True)
        
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        self.client = Groq(api_key=self.api_key, max_retries=0)

    def preprocess_audio(self) -> Path:
        """
        Preprocess audio file to 16kHz mono FLAC for transcription.
        """
        if not self.audio_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.audio_path}")
        
        with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as temp_file:
            output_path = Path(temp_file.name)
        
        print("Converting audio to 16kHz mono FLAC...")
        base_path = get_base_path()
        
        # Instead of manually constructing the path, we can use get_ffmpeg_path
        ffmpeg_path = get_ffmpeg_path()

        if not os.path.exists(ffmpeg_path):
            raise FileNotFoundError(f"FFmpeg binary not found at: {ffmpeg_path}")

        try:
            subprocess.run([
                ffmpeg_path,
                '-hide_banner',
                '-loglevel', 'error',
                '-i', str(self.audio_path),
                '-ar', '16000',
                '-ac', '1',
                '-c:a', 'flac',
                '-y',
                str(output_path)
            ], check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"FFmpeg conversion failed: {str(e)}")

    def transcribe_single_chunk(self, chunk: AudioSegment, chunk_num: int, total_chunks: int) -> tuple[dict, float]:
        """
        Transcribe a single audio chunk using the Groq API.
        Returns a tuple of (transcription result, API processing time).
        """
        total_api_time = 0
        
        while True:
            temp_file = tempfile.NamedTemporaryFile(suffix=".flac", delete=False, dir=str(self.session_folder))
            temp_file.close()  # Release the file handle

            try:
                chunk.export(temp_file.name, format='flac')
                start_time = time.time()
                with open(temp_file.name, 'rb') as f:
                    try:
                        result = self.client.audio.transcriptions.create(
                            file=("chunk.flac", f, "audio/flac"),
                            model="whisper-large-v3",
                            language="en",
                            response_format="verbose_json"
                        )
                        api_time = time.time() - start_time
                        total_api_time += api_time
                        print(f"Chunk {chunk_num}/{total_chunks} processed in {api_time:.2f}s")
                        return result, total_api_time
                    except RateLimitError:
                        print(f"\nRate limit hit for chunk {chunk_num} - retrying in 60 seconds...")
                        time.sleep(60)
                        continue
                    except Exception as e:
                        print(f"Error transcribing chunk {chunk_num}: {str(e)}")
                        raise
            finally:
                os.unlink(temp_file.name)

    @staticmethod
    def find_longest_common_sequence(sequences: list[str], match_by_words: bool = True) -> str:
        """
        Find and return the merged sequence with optimal alignment between sequences.
        """
        if not sequences:
            return ""

        if match_by_words:
            sequences = [
                [word for word in re.split(r'(\s+\w+)', seq) if word]
                for seq in sequences
            ]
        else:
            sequences = [list(seq) for seq in sequences]

        left_sequence = sequences[0]
        left_length = len(left_sequence)
        total_sequence = []

        for right_sequence in sequences[1:]:
            max_matching = 0.0
            right_length = len(right_sequence)
            max_indices = (left_length, left_length, 0, 0)

            for i in range(1, left_length + right_length + 1):
                eps = float(i) / 10000.0

                left_start = max(0, left_length - i)
                left_stop = min(left_length, left_length + right_length - i)
                left = left_sequence[left_start:left_stop]

                right_start = max(0, i - left_length)
                right_stop = min(right_length, i)
                right = right_sequence[right_start:right_stop]

                if len(left) != len(right):
                    raise RuntimeError("Mismatched subsequences detected during transcript merging.")

                matches = sum(a == b for a, b in zip(left, right))
                matching = matches / float(i) + eps
                if matches > 1 and matching > max_matching:
                    max_matching = matching
                    max_indices = (left_start, left_stop, right_start, right_stop)
            
            left_start, left_stop, right_start, right_stop = max_indices
            left_mid = (left_stop + left_start) // 2
            right_mid = (right_stop + right_start) // 2

            total_sequence.extend(left_sequence[:left_mid])
            left_sequence = right_sequence[right_mid:]
            left_length = len(left_sequence)

        total_sequence.extend(left_sequence)
        return ''.join(total_sequence) if not match_by_words else ''.join(total_sequence)

    @staticmethod
    def merge_transcripts(results: list[tuple[dict, int]]) -> dict:
        """
        Merge transcription chunks and handle overlaps between them.
        """
        print("\nMerging results...")
        final_segments = []
        processed_chunks = []
        
        for i, (chunk, _) in enumerate(results):
            data = chunk.model_dump() if hasattr(chunk, 'model_dump') else chunk
            segments = data['segments']
            
            if i < len(results) - 1:
                next_start = results[i + 1][1]
                current_segments = []
                overlap_segments = []
                
                for segment in segments:
                    if segment['end'] * 1000 > next_start:
                        overlap_segments.append(segment)
                    else:
                        current_segments.append(segment)
                
                if overlap_segments:
                    merged_overlap = overlap_segments[0].copy()
                    merged_overlap.update({
                        'text': ' '.join(s['text'] for s in overlap_segments),
                        'end': overlap_segments[-1]['end']
                    })
                    current_segments.append(merged_overlap)
                
                processed_chunks.append(current_segments)
            else:
                processed_chunks.append(segments)
        
        for i in range(len(processed_chunks) - 1):
            final_segments.extend(processed_chunks[i][:-1])
            last_segment = processed_chunks[i][-1]
            first_segment = processed_chunks[i + 1][0]
            merged_text = AudioTranscriber.find_longest_common_sequence([last_segment['text'], first_segment['text']])
            merged_segment = last_segment.copy()
            merged_segment.update({
                'text': merged_text,
                'end': first_segment['end']
            })
            final_segments.append(merged_segment)
        
        if processed_chunks:
            final_segments.extend(processed_chunks[-1])
        
        final_text = ' '.join(segment['text'] for segment in final_segments)
        return {
            "text": final_text,
            "segments": final_segments
        }

    def save_results(self, result: dict, processed_audio_path: Path) -> Path:
        """
        Save the transcription results in different formats to the session folder.
        """
        try:
            output_dir = self.session_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = output_dir / f"{self.audio_path.stem}_{timestamp}"
            
            with open(f"{base_path}.txt", 'w', encoding='utf-8') as f:
                f.write(result["text"])
                
            with open(f"{base_path}_full.json", 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            with open(f"{base_path}_segments.json", 'w', encoding='utf-8') as f:
                json.dump(result["segments"], f, indent=2, ensure_ascii=False)
            
            print(f"\nResults saved to session folder:")
            print(f"- {base_path}.txt")
            print(f"- {base_path}_full.json")
            print(f"- {base_path}_segments.json")
            return base_path
        except IOError as e:
            print(f"Error saving results: {str(e)}")
            raise

    def transcribe(self) -> dict:
        """
        Main method to transcribe the audio file into text by processing chunks.
        """
        print(f"\nStarting transcription of: {self.audio_path}")
        processed_audio = None
        try:
            processed_audio = self.preprocess_audio()
            try:
                audio = AudioSegment.from_file(processed_audio, format="flac")
            except Exception as e:
                raise RuntimeError(f"Failed to load audio: {str(e)}")
            
            duration = len(audio)
            print(f"Audio duration: {duration/1000:.2f}s")
            
            chunk_ms = self.chunk_length * 1000
            overlap_ms = self.overlap * 1000
            total_chunks = (duration // (chunk_ms - overlap_ms)) + 1
            print(f"Processing {total_chunks} chunks...")
            
            results = []
            total_transcription_time = 0
            
            for i in range(total_chunks):
                start = i * (chunk_ms - overlap_ms)
                end = min(start + chunk_ms, duration)
                print(f"\nProcessing chunk {i+1}/{total_chunks}")
                print(f"Time range: {start/1000:.1f}s - {end/1000:.1f}s")
                
                chunk = audio[start:end]
                result, chunk_time = self.transcribe_single_chunk(chunk, i+1, total_chunks)
                total_transcription_time += chunk_time
                results.append((result, start))
            
            final_result = AudioTranscriber.merge_transcripts(results)
            self.save_results(final_result, self.audio_path)
            print(f"\nTotal Groq API transcription time: {total_transcription_time:.2f}s")
            return final_result
        finally:
            if processed_audio:
                Path(processed_audio).unlink(missing_ok=True)

    def merge_device_and_mic_transcripts(self, device_transcript: dict, mic_transcript: dict) -> dict:
        """
        Merge the device and mic transcripts by simply appending the mic transcript after the device transcript,
        while preserving the timestamps for each segment. The final transcript text shows each segment with its
        formatted start and end times.

        Args:
            device_transcript (dict): Transcript dictionary from the device (must include a "segments" key).
            mic_transcript (dict): Transcript dictionary from the microphone (must include a "segments" key).

        Returns:
            dict: A merged transcript containing:
                  - "text": The final transcript text with timestamps.
                  - "segments": A simple concatenation of the device and mic transcript segments.
        """
        # --- Original merging logic commented out ---
        # [complex merging and synchronization logic is commented out for now].
        # --- End of original logic ---

        # Tag segments with their source identifier.
        device_segments = device_transcript.get("segments", [])
        for seg in device_segments:
            seg["source"] = "device"
        mic_segments = mic_transcript.get("segments", [])
        for seg in mic_segments:
            seg["source"] = "mic"

        # Simple merging: just append the mic segments to the device segments.
        merged_segments = device_segments + mic_segments

        # Helper function to format timestamps (in seconds).
        def format_timestamp(seconds):
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h:
                return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
            else:
                return f"{int(m):02d}:{int(s):02d}"

        # Build the final transcript text from each segment.
        final_lines = []
        for seg in merged_segments:
            start_formatted = format_timestamp(seg["start"])
            end_formatted = format_timestamp(seg["end"])
            speaker = "Device" if seg["source"] == "device" else "Mic"
            final_lines.append(f"[{start_formatted} - {end_formatted}] {speaker}: {seg['text'].strip()}")
        
        merged_text = "\n".join(final_lines)

        return {
            "text": merged_text,
            "segments": merged_segments
        }

if __name__ == "__main__":
    transcriber = AudioTranscriber(Path("path_to_your_audio"))
    transcriber.transcribe()
