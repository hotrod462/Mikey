import sys
import threading
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from core.audio_session import RecordingSession
from gui.recordings_window import RecordingsWindow  # Import the new recordings window
from core.utils import get_base_path

class TranscriptionWorker(QtCore.QThread):
    # This signal will emit the transcription result (a dict) back to the GUI.
    transcription_done = QtCore.pyqtSignal(dict)

    def __init__(self, session):
        super().__init__()
        self.session = session

    def run(self):
        # This call runs in a separate thread so it won't freeze the UI.
        result = self.session.transcribe()
        self.transcription_done.emit(result)


class AudioRecorderGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Recorder App")
        # Set the favicon for your main window.
        self.setWindowIcon(QtGui.QIcon("resources/favicon.ico"))
        self.session = None       # Instance of RecordingSession
        self.recording_thread = None
        self.transcription_worker = None  # Worker for transcription
        self.recordings_window = None       # Instance of the recordings browser window
        self._setup_ui()
        self._load_audio_devices()

    def _setup_ui(self):
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Device selection combo boxes.
        layout.addWidget(QtWidgets.QLabel("Select System Audio Device:"))
        self.system_combo = QtWidgets.QComboBox()
        layout.addWidget(self.system_combo)

        layout.addWidget(QtWidgets.QLabel("Select Microphone Device:"))
        self.mic_combo = QtWidgets.QComboBox()
        layout.addWidget(self.mic_combo)

        # Buttons for controlling recording.
        btn_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start Recording")
        self.start_button.clicked.connect(self.start_recording)
        btn_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop Recording")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.stop_button)
        layout.addLayout(btn_layout)

        # Additional button for opening the recordings browser window.
        self.recordings_button = QtWidgets.QPushButton("Show Recordings")
        self.recordings_button.clicked.connect(self.show_recordings_window)
        layout.addWidget(self.recordings_button)

        # Log output text area.
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def _load_audio_devices(self):
        # Use AudioRecorder to list devices.
        from mikey.audio_recorder import AudioRecorder
        recorder = AudioRecorder()
        devices = recorder.list_audio_devices()
        self.system_combo.clear()
        self.mic_combo.clear()
        for device in devices:
            display = f"{device['name']} (index: {device['index']})"
            self.system_combo.addItem(display, device['index'])
            self.mic_combo.addItem(display, device['index'])

    def _log(self, message):
        self.log_text.append(message)

    def start_recording(self):
        self._log("Starting recording session...")
        system_index = self.system_combo.currentData()
        mic_index = self.mic_combo.currentData()
        self.session = RecordingSession(system_index, mic_index)
        self._log(f"Session folder: {self.session.session_folder}")

        # Start recording in a separate Python thread.
        self.recording_thread = threading.Thread(target=self.session.record)
        self.recording_thread.start()
        self._log("Recording started...")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_recording(self):
        self._log("Stopping recording...")
        if self.session:
            self.session.stop()
        if self.recording_thread:
            self.recording_thread.join()
        self._log("Recording stopped.")

        # Start transcription in a separate QThread to avoid blocking the UI.
        self.transcription_worker = TranscriptionWorker(self.session)
        self.transcription_worker.transcription_done.connect(self.handle_transcription_done)
        self.transcription_worker.start()

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def handle_transcription_done(self, result):
        if result:
            from core.utils import save_transcripts
            saved_paths = save_transcripts(self.session.session_folder, result)
            self._log("Transcription complete and saved as:")
            self._log(f"Merged: {saved_paths['merged']}")
            self._log(f"System: {saved_paths['system']}")
            self._log(f"Mic: {saved_paths['mic']}")
        else:
            self._log("Transcription skipped or failed.")

    def show_recordings_window(self):
        base_path = get_base_path()
        recordings_path = os.path.join(base_path, "recordings")
        
        if self.recordings_window is None:
            self.recordings_window = RecordingsWindow(recordings_path=recordings_path)
        self.recordings_window.show()
        self.recordings_window.raise_()  # Bring window to the front

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
