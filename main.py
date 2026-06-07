import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("FileDiff")
    app.setOrganizationName("FileDiff")

    window = MainWindow()
    window.show()

    # If two file paths are passed via CLI, load them immediately
    args = sys.argv[1:]
    if len(args) >= 1:
        window._left_path = args[0]
    if len(args) >= 2:
        window._right_path = args[1]
    if len(args) >= 2:
        window._run_diff()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
