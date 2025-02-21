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
        self.use_local = False
        self.model_size = "base"
        self.device = "cpu"

    def set_transcription_params(self, use_local, model_size, device):
        self.use_local = use_local
        self.model_size = model_size
        self.device = device

    def run(self):
        # This call runs in a separate thread so it won't freeze the UI.
        result = self.session.transcribe(
            enable_transcription=True,
            use_local=self.use_local,
            model_size=self.model_size,
            device=self.device
        )
        # Add service type to result
        result['service'] = 'local (faster_whisper)' if self.use_local else 'groq'
        self.transcription_done.emit(result)


class AudioRecorderGUI(QtWidgets.QMainWindow):
    # Signal to indicate a new recording has been finished.
    recording_finished = QtCore.pyqtSignal()

    def __init__(self, posthog_client=None):
        super().__init__()
        self.setWindowTitle("Mikey")
        # Set the favicon for your main window.
        self.setWindowIcon(QtGui.QIcon("resources/favicon.ico"))
        self.session = None       # Instance of RecordingSession
        self.recording_thread = None
        self.transcription_worker = None  # Worker for transcription
        self.recordings_window = None       # Instance of the recordings browser window
        self.posthog_client = posthog_client # Store the PostHog client
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

        # Add transcription options
        transcribe_group = QtWidgets.QGroupBox("Transcription Settings")
        transcribe_layout = QtWidgets.QVBoxLayout()
        
        # Local transcription checkbox
        self.local_transcribe_check = QtWidgets.QCheckBox("Use Local Transcription")
        self.local_transcribe_check.setChecked(True)  # Checked by default
        transcribe_layout.addWidget(self.local_transcribe_check)
        
        # Container for conditional settings
        self.config_container = QtWidgets.QWidget()
        config_layout = QtWidgets.QVBoxLayout(self.config_container)
        
        # Model size selection
        model_layout = QtWidgets.QHBoxLayout()
        model_layout.addWidget(QtWidgets.QLabel("Model Size:"))
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentIndex(1)
        model_layout.addWidget(self.model_combo)
        config_layout.addLayout(model_layout)
        
        # Device selection (removed mps)
        device_layout = QtWidgets.QHBoxLayout()
        device_layout.addWidget(QtWidgets.QLabel("Compute Device:"))
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])  # Removed mps
        device_layout.addWidget(self.device_combo)
        config_layout.addLayout(device_layout)
        
        transcribe_layout.addWidget(self.config_container)
        transcribe_group.setLayout(transcribe_layout)
        layout.addWidget(transcribe_group)

        # Connect checkbox to toggle visibility
        self.local_transcribe_check.toggled.connect(self.config_container.setVisible)
        self.config_container.setVisible(True)  # Initial state matches checkbox

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

        system_default_index = None  # Index of first device with "Loopback" in its name for system audio.
        mic_default_index = None     # Index of first device that is NOT a loopback and does NOT have "Microphone Array".

        for i, device in enumerate(devices):
            name = device['name']
            display = f"{name} (index: {device['index']})"
            self.system_combo.addItem(display, device['index'])
            self.mic_combo.addItem(display, device['index'])
            
            # Set the system default to the first device with "Loopback" in its name.
            if system_default_index is None and "Loopback" in name:
                system_default_index = i
            
            # Set the mic (headphones) default to the first non-loopback device that doesn't have "Microphone Array" in its name.
            if mic_default_index is None and "Loopback" not in name and "Microphone Array" not in name:
                mic_default_index = i

        # If a preferred system audio device was found, select it.
        if system_default_index is not None:
            self.system_combo.setCurrentIndex(system_default_index)
        
        # If a preferred mic device was found, select it.
        if mic_default_index is not None:
            self.mic_combo.setCurrentIndex(mic_default_index)

    def _log(self, message):
        self.log_text.append(message)

    def start_recording(self):
        self._log("Starting recording session...")
        system_index = self.system_combo.currentData()
        mic_index = self.mic_combo.currentData()
        self.session = RecordingSession(system_index, mic_index)
        self._log(f"Session folder: {self.session.session_folder}")

        # --- PostHog Event Capture: Recording Started ---
        if self.posthog_client:
            # For simplicity, let's generate a unique user ID if you don't have user accounts yet.
            # In a real app, you'd use actual user IDs.
            user_id = QtCore.QSettings().value("posthog_user_id")
            if not user_id:
                import uuid
                user_id = str(uuid.uuid4())
                QtCore.QSettings().setValue("posthog_user_id", user_id)

            self.posthog_client.capture(
                user_id,
                'recording_started',
                properties={
                    'system_device_index': system_index,
                    'mic_device_index': mic_index,
                    
                }
            )
            print(f"PostHog event captured: recording_started for user {user_id}")
        else:
            print("PostHog client not initialized, event not captured.")
        # --- End PostHog Event Capture ---

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

        #To avoid blocking the UI, we'll start transcription in a separate thread.
        # Get transcription parameters from UI
        use_local = self.local_transcribe_check.isChecked()
        model_size = self.model_combo.currentText()
        device = self.device_combo.currentText()
        
        # Pass parameters to worker
        self.transcription_worker = TranscriptionWorker(self.session)
        self.transcription_worker.set_transcription_params(use_local, model_size, device)
        self.transcription_worker.transcription_done.connect(self.handle_transcription_done)
        self.transcription_worker.start()

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        # Emit the signal that a recording has finished.
        self.recording_finished.emit()

    def handle_transcription_done(self, result):
        if result:
            self._log(f"Transcription complete using {result['service']}")
            from core.utils import save_transcripts
            saved_paths = save_transcripts(self.session.session_folder, result)
            self._log("Saved transcripts:")
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
        # Connect the recording_finished signal to the populate_list slot of the recordings window.
        self.recording_finished.connect(self.recordings_window.populate_list)
        self.recordings_window.show()
        self.recordings_window.raise_()  # Bring window to the front

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI()
    window.resize(600, 500)
    window.show()
    sys.exit(app.exec_())
