from PyQt5 import QtWidgets
import sys
from gui.main_window import AudioRecorderGUI
import os
from dotenv import load_dotenv
from core.utils import get_base_path, get_data_path  # Updated utility import
import posthog  # Import PostHog
from pathlib import Path

# Use the utility function for all path operations
base_path = get_base_path()

# Load environment variables
env_path = Path(base_path) / '.env'

# If using python-dotenv
load_dotenv(env_path)

# Create recordings directory next to executable
recordings_folder = os.path.join(get_data_path(), 'recordings')
os.makedirs(recordings_folder, exist_ok=True)

# Initialize PostHog client
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
posthog_client = None # Initialize as None
if POSTHOG_API_KEY:
    posthog_client = posthog.Posthog(
        POSTHOG_API_KEY,
        host='https://us.i.posthog.com' # Default PostHog cloud host, change if self-hosting
    )
    print("PostHog initialized.")
else:
    print("POSTHOG_API_KEY not found in environment variables. PostHog will not be initialized.")

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI(posthog_client=posthog_client) # Pass PostHog client to GUI
    window.show()

    exit_code = app.exec_()
    if posthog_client:
        posthog_client.shutdown() # Ensure events are sent on app exit
    sys.exit(exit_code)

if __name__ == '__main__':
    main() 