import sys
import threading
import os
from PyQt5 import QtWidgets
from core.audio_session import RecordingSession

class AudioRecorderGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Recorder App")
        self.session = None
        self.recording_thread = None
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

        # Start and Stop buttons.
        btn_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start Recording")
        self.start_button.clicked.connect(self.start_recording)
        btn_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop Recording")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        btn_layout.addWidget(self.stop_button)
        layout.addLayout(btn_layout)

        # Log output text area.
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def _load_audio_devices(self):
        # Use AudioRecorder from tmnt to list devices.
        from tmnt.audio_recorder import AudioRecorder
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

        # Start recording on a separate thread.
        self.recording_thread = threading.Thread(target=self.session.record)
        self.recording_thread.start()
        self._log("Recording started...")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_recording(self):
        self._log("Stopping recording...")
        if self.session:
            # Signal the session to stop recording.
            self.session.stop()
        if self.recording_thread:
            self.recording_thread.join()
        self._log("Recording stopped.")

        # Perform transcription.
        result = self.session.transcribe()
        if result:
            merged_transcript = result["merged"]
            merged_path = os.path.join(self.session.session_folder, "merged_transcript.md")
            with open(merged_path, "w", encoding="utf-8") as f:
                f.write(merged_transcript)
            self._log(f"Transcription complete and saved as: {merged_path}")
        else:
            self._log("Transcription skipped or failed.")

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
