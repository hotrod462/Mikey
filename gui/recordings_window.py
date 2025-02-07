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
        
        # Search bar (QLineEdit and Search button)
        self.search_layout = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search transcript...")
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(self.search_transcript)
        self.search_layout.addWidget(self.search_field)
        self.search_layout.addWidget(self.search_button)
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
        dirs = [d for d in os.listdir(self.recordings_path) 
                if os.path.isdir(os.path.join(self.recordings_path, d))]
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
