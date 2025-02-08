from PyQt5 import QtWidgets
import sys
from gui.main_window import AudioRecorderGUI
import os
from dotenv import load_dotenv
from core.utils import get_base_path  # Import our utility function

# Use the utility function to determine the base path.
base_path = get_base_path()

# Load environment variables from .env in the same directory.
dotenv_path = os.path.join(base_path, '.env')
load_dotenv(dotenv_path)

# Define a persistent recordings folder relative to the base path.
recordings_folder = os.path.join(base_path, 'recordings')

# Ensure it exists.
os.makedirs(recordings_folder, exist_ok=True)

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 