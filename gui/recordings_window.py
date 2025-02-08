import os
from PyQt5 import QtWidgets, QtCore, QtGui

class RecordingsWindow(QtWidgets.QMainWindow):
    def __init__(self, recordings_path="recordings", parent=None):
        super().__init__(parent)
        self.recordings_path = recordings_path
        self.setWindowTitle("Recordings Browser")
        self.setWindowIcon(QtGui.QIcon("resources/favicon.ico"))
        self.resize(800, 600)
        
        # Create a horizontal splitter for two panels.
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        
        # Left panel: a QListWidget showing just the timestamp (folder name) of each recording.
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setFixedWidth(200)
        self.list_widget.itemClicked.connect(self.load_transcript)
        self.splitter.addWidget(self.list_widget)
        
        # Right panel: create a widget with vertical layout for search bar and transcript display.
        self.right_panel = QtWidgets.QWidget()
        self.right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        
        # Search bar (QLineEdit, Search button, and Regenerate Transcript button)
        self.search_layout = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search transcript...")
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self.search_transcript)
        self.search_layout.addWidget(self.search_field)
        self.search_layout.addWidget(self.search_button)
        
        # Regenerate Transcript Button
        self.regenerate_button = QtWidgets.QPushButton("Regenerate Transcript")
        self.regenerate_button.clicked.connect(self.regenerate_transcript)
        self.search_layout.addWidget(self.regenerate_button)
        
        self.right_layout.addLayout(self.search_layout)

        # Transcript text area
        self.transcript_text = QtWidgets.QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.right_layout.addWidget(self.transcript_text)
        
        self.splitter.addWidget(self.right_panel)
        self.setCentralWidget(self.splitter)
        
        # Populate the list with session folder names.
        self.populate_list()
        
    def populate_list(self):
        """
        Populate the left panel list with directory names from the recordings_path.
        It assumes that each subdirectory is a recording session identified by a timestamp.
        """
        if not os.path.exists(self.recordings_path):
            return
        
        # List only directories (recording sessions)
        dirs = [
            d for d in os.listdir(self.recordings_path) 
            if os.path.isdir(os.path.join(self.recordings_path, d))
        ]
        dirs.sort(reverse=True)  # Newest recordings first.
        
        self.list_widget.clear()
        for d in dirs:
            item = QtWidgets.QListWidgetItem(d)
            self.list_widget.addItem(item)
        
    def load_transcript(self, item):
        """
        When a timestamp is selected, load the transcript text from
        merged_transcript.md in that folder and display it on the right.
        """
        recording_folder = os.path.join(self.recordings_path, item.text())
        transcript_path = os.path.join(recording_folder, "merged_transcript.md")
        
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.transcript_text.setPlainText(content)
        else:
            self.transcript_text.setPlainText("No transcript available for this recording.")
        
        # Clear any previous search highlights.
        self.transcript_text.setExtraSelections([])
    
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
    
    def regenerate_transcript(self):
        """
        Regenerate the transcript for the selected session by reusing the existing transcribe()
        method from RecordingSession. This avoids duplicating transcription logic.
        """
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select a recording session first.")
            return
        
        session_name = selected_items[0].text()
        session_folder = os.path.join(self.recordings_path, session_name)
        
        try:
            from core.audio_session import RecordingSession
            # Create a session instance from the existing folder.
            rs = RecordingSession.from_existing_session(session_folder)
            result = rs.transcribe()
            if result is None:
                QtWidgets.QMessageBox.warning(self, "Error", "Transcription could not be generated.")
                return

            merged_transcription_text = result["merged"]
            
            # Save the merged transcript to merged_transcript.md.
            md_filename = os.path.join(session_folder, "merged_transcript.md")
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(merged_transcription_text)
            
            # Reload the transcript in the text area.
            self.load_transcript(selected_items[0])
            QtWidgets.QMessageBox.information(self, "Success", "Transcript regenerated successfully.")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to regenerate transcript: {e}")
