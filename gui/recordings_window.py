import os
from PyQt5 import QtWidgets, QtCore, QtGui
from core.utils import get_base_path, get_data_path

class RegenerateTranscriptWorker(QtCore.QThread):
    transcription_done = QtCore.pyqtSignal(dict)
    error_occurred = QtCore.pyqtSignal(str)

    def __init__(self, session, use_local, model_size=None, device=None):
        super().__init__()
        self.session = session
        self.use_local = use_local
        self.model_size = model_size
        self.device = device

    def run(self):
        try:
            result = self.session.transcribe(
                use_local=self.use_local,
                model_size=self.model_size,
                device=self.device
            )
            self.transcription_done.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class RecordingsWindow(QtWidgets.QMainWindow):
    def __init__(self, recordings_path=None, parent=None):
        super().__init__(parent)
        
        from core.utils import get_data_path
        data_path = get_data_path()
        
        # Create recordings path next to executable
        self.recordings_path = os.path.join(data_path, 'recordings')
        os.makedirs(self.recordings_path, exist_ok=True)
        
        self.setWindowTitle("Recordings Browser")
        # Build the absolute path for the favicon icon.
        icon_path = os.path.join(get_base_path(), "resources", "favicon.ico")
        self.setWindowIcon(QtGui.QIcon(icon_path))
        self.resize(800, 600)
        
        # Create a horizontal splitter for two panels.
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        
        # Left panel: a QListWidget displaying recording session folder names.
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setFixedWidth(200)
        self.list_widget.itemClicked.connect(self.load_transcript)
        self.splitter.addWidget(self.list_widget)
        
        # Right panel: a widget with vertical layout for search bar, transcript type selector, and transcript display.
        self.right_panel = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        
        # Search bar layout (includes a QLineEdit, a Search button, a Transcript type combo, and a Regenerate Transcript button)
        self.search_layout = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search transcript...")
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self.search_transcript)
        self.search_layout.addWidget(self.search_field)
        self.search_layout.addWidget(self.search_button)
        
        # Add transcription mode selector
        self.transcription_mode = QtWidgets.QComboBox()
        self.transcription_mode.addItem("Groq (Cloud)")
        self.transcription_mode.addItem("Local (faster_whisper)")
        self.transcription_mode.currentIndexChanged.connect(self.toggle_local_settings)
        self.search_layout.addWidget(self.transcription_mode)

        # Local transcription settings (hidden by default)
        self.model_size_combo = QtWidgets.QComboBox()
        self.model_size_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_size_combo.setCurrentText("base")
        self.search_layout.addWidget(self.model_size_combo)
        
        self.device_combo = QtWidgets.QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])
        self.search_layout.addWidget(self.device_combo)
        
        # Initially hide local settings
        self.model_size_combo.hide()
        self.device_combo.hide()

        # Regenerate Transcript Button
        self.regenerate_button = QtWidgets.QPushButton("Regenerate Transcript")
        self.regenerate_button.clicked.connect(self.regenerate_transcript)
        self.search_layout.addWidget(self.regenerate_button)
        
        self.right_layout.addLayout(self.search_layout)

        # Transcript text area.
        self.transcript_text = QtWidgets.QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.right_layout.addWidget(self.transcript_text)
        
        self.splitter.addWidget(self.right_panel)
        self.setCentralWidget(self.splitter)
        
        # Populate the list with session folder names.
        self.populate_list()
        
        # Store the current session name for use when switching transcript views.
        self.current_session_name = None

        # Store a reference to the current worker so it isn't garbage-collected.
        self.regen_worker = None

    def populate_list(self):
        """
        Populate the left panel list with directory names from the recordings_path.
        Each subdirectory is assumed to be a recording session.
        """
        if not os.path.exists(self.recordings_path):
            return
        
        # List only directories (recording sessions).
        dirs = [d for d in os.listdir(self.recordings_path) 
                if os.path.isdir(os.path.join(self.recordings_path, d))]
        dirs.sort(reverse=True)  # Newest recordings first.
        
        self.list_widget.clear()
        for d in dirs:
            item = QtWidgets.QListWidgetItem(d)
            self.list_widget.addItem(item)
        
    def load_transcript(self, item):
        """
        Load the transcript text based on the selected transcript type
        from the selected session folder.
        """
        self.current_session_name = item.text()
        
        session_folder = os.path.join(self.recordings_path, item.text())
        
        transcript_file = "merged_transcript.md" # Assuming merged transcript is saved as merged_transcript.md
        transcript_path = os.path.join(session_folder, transcript_file)
        
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.transcript_text.setPlainText(content)
        else:
            self.transcript_text.setPlainText(f"No transcript available for this recording.")
    
    def search_transcript(self):
        """
        Highlight all occurrences of the search query in the transcript text.
        """
        query = self.search_field.text()
        extraSelections = []
        
        if not query:
            self.transcript_text.setExtraSelections(extraSelections)
            return
        
        # Start at the beginning of the document.
        cursor = self.transcript_text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.Start)
        
        while True:
            cursor = self.transcript_text.document().find(query, cursor)
            if cursor.isNull():
                break
            selection = QtWidgets.QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(QtGui.QColor("yellow"))
            extraSelections.append(selection)
        
        self.transcript_text.setExtraSelections(extraSelections)
    
    def toggle_local_settings(self):
        """Show/hide local transcription settings based on mode selection"""
        is_local = self.transcription_mode.currentText() == "Local (faster_whisper)"
        self.model_size_combo.setVisible(is_local)
        self.device_combo.setVisible(is_local)

    def regenerate_transcript(self):
        """
        Regenerate the transcript from the source audio files in the selected session folder.
        Log changes to the transcript display area.
        """
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self.transcript_text.append("Warning: Please select a recording session first.")
            return

        # Get transcription parameters
        use_local = self.transcription_mode.currentText() == "Local (faster_whisper)"
        model_size = self.model_size_combo.currentText() if use_local else None
        device = self.device_combo.currentText() if use_local else None

        session_item = selected_items[0]
        session_name = session_item.text()
        self.transcript_text.clear()
        self.transcript_text.append(f"Starting regeneration for session: '{session_name}'")

        session_folder = os.path.join(self.recordings_path, session_name)

        try:
            from core.audio_session import RecordingSession
            # Create a session instance from the existing folder.
            rs = RecordingSession.from_existing_session(session_folder)
            self.transcript_text.append("Session initialized successfully.")
        except Exception as e:
            self.transcript_text.append(f"Error initializing session: {e}")
            return

        # Create and start the transcription worker with parameters
        self.regen_worker = RegenerateTranscriptWorker(rs, use_local, model_size, device)
        self.regen_worker.transcription_done.connect(lambda result: self.handle_regeneration_done(result, session_item))
        self.regen_worker.error_occurred.connect(self.handle_regeneration_error)
        
        self.transcript_text.append("Transcription started...")
        self.regen_worker.start()
    
    def handle_regeneration_done(self, result, session_item):
        """
        Handle successful completion of transcript regeneration.
        Log details and then reload the newly generated transcript.
        """
        try:
            from core.utils import save_transcripts
            saved_paths = save_transcripts(os.path.join(self.recordings_path, session_item.text()), result)
            
            log_msg = ("Transcript regenerated successfully!\n"
                       f"System: {saved_paths['system']}\n"
                       f"Mic: {saved_paths['mic']}\n")
            self.transcript_text.append(log_msg)
            self.transcript_text.append("Reloading transcript from file...")

            # Reload transcript based on current transcript selection.
            transcript_file = "merged_transcript.md" # Assuming merged transcript is saved as merged_transcript.md
            transcript_path = os.path.join(self.recordings_path, session_item.text(), transcript_file)
            
            if os.path.exists(transcript_path):
                with open(transcript_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.transcript_text.append("\n----- Transcript Content -----\n")
                self.transcript_text.append(content)
            else:
                self.transcript_text.append(f"No transcript available after regeneration.")
        except Exception as e:
            self.transcript_text.append(f"Error saving transcripts: {e}")
    
    def handle_regeneration_error(self, error_message):
        """
        Handle errors during the transcription process.
        Log the error message to the transcript display area.
        """
        self.transcript_text.append(f"Error: Transcription failed: {error_message}")
