import os
import sys

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
    """
    Returns the base path for the application.

    This function checks if the application is running as a bundled executable.
    If it is (i.e., if sys.frozen is true), it returns the directory of the executable.
    Otherwise, it returns the directory of the current file.

    Returns:
        str: The base path to use for loading resources.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__) 