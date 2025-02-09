from PyQt5 import QtWidgets
import sys
from gui.main_window import AudioRecorderGUI
import os
from dotenv import load_dotenv
from core.utils import get_base_path  # Import our utility function
import posthog  # Import PostHog

# Use the utility function to determine the base path.
base_path = get_base_path()

# Load environment variables from .env in the same directory.
dotenv_path = os.path.join(base_path, '.env')
load_dotenv(dotenv_path)

# Define a persistent recordings folder relative to the base path.
recordings_folder = os.path.join(base_path, 'recordings')

# Ensure it exists.
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