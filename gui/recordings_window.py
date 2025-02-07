import os
from PyQt5 import QtWidgets, QtCore, QtGui

class RecordingsWindow(QtWidgets.QMainWindow):
    def __init__(self, recordings_path="recordings", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recordings Browser")
        self.setWindowIcon(QtGui.QIcon("resources/favicon.ico"))
        self.recordings_path = recordings_path
        self.resize(800, 600)
        
        # Create a horizontal splitter for two panels.
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        
        # Left panel: a QListWidget showing just the timestamp (folder name) of each recording.
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setFixedWidth(200)
        self.list_widget.itemClicked.connect(self.load_transcript)
        self.splitter.addWidget(self.list_widget)
        
        # Right panel: a QTextEdit that displays the transcript.
        self.transcript_text = QtWidgets.QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.splitter.addWidget(self.transcript_text)
        
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
        dirs = [d for d in os.listdir(self.recordings_path) 
                if os.path.isdir(os.path.join(self.recordings_path, d))]
        dirs.sort(reverse=True)  # Newest recordings first.
        
        self.list_widget.clear()
        for d in dirs:
            item = QtWidgets.QListWidgetItem(d)
            self.list_widget.addItem(item)
        
    def load_transcript(self, item):
        """
        When a timestamp is selected, this method loads the transcript text from
        merged_transcript.md in that folder and displays it on the right.
        """
        recording_folder = os.path.join(self.recordings_path, item.text())
        transcript_path = os.path.join(recording_folder, "merged_transcript.md")
        
        if os.path.exists(transcript_path):
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.transcript_text.setPlainText(content)
        else:
            self.transcript_text.setPlainText("No transcript available for this recording.")
