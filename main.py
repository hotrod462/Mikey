from PyQt5 import QtWidgets
import sys
from gui.main_window import AudioRecorderGUI

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AudioRecorderGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 