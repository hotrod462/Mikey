import os
import sys
from pathlib import Path

def save_transcripts(session_folder, transcripts):
    """
    Save transcripts to separate markdown files in the given session folder.

    Parameters:
        session_folder (str): Directory where transcripts will be saved.
        transcripts (dict): A dictionary with keys 'merged', 'system', 'mic'
                            and corresponding transcript text.

    Returns:
        dict: A dictionary mapping transcript types to their saved file paths.
    """
    paths = {}
    
    merged_path = os.path.join(session_folder, "merged_transcript.md")
    with open(merged_path, "w", encoding="utf-8") as f:
        f.write(transcripts["merged"])
    paths["merged"] = merged_path

    system_path = os.path.join(session_folder, "system_transcript.md")
    with open(system_path, "w", encoding="utf-8") as f:
        f.write(transcripts["system"])
    paths["system"] = system_path

    mic_path = os.path.join(session_folder, "mic_transcript.md")
    with open(mic_path, "w", encoding="utf-8") as f:
        f.write(transcripts["mic"])
    paths["mic"] = mic_path

    return paths

def get_base_path():
    """Get base path for resources (app bundle in frozen mode) or the project root in development."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # In development mode, assume this file is in <project_root>/core/ and return the project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_path():
    """Get path for user data (next to executable in frozen mode) or the project root in development."""
    if getattr(sys, 'frozen', False):
        # Use the directory containing the executable when frozen.
        return os.path.dirname(sys.executable)
    # In development mode, use the project root as defined by get_base_path().
    return get_base_path() 