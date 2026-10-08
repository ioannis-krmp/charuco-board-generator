import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QProgressBar, QStatusBar,
)

from boards.board_types import ARUCO_DICTS, APRILTAG_DICTS
from gui.tab_charuco import CharucoTab
from gui.tab_aruco_grid import ArucoGridTab
from gui.tab_fiducial import FiducialTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fiducial Board Generator")
        self.setMinimumSize(900, 600)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        self._status = QStatusBar()
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

        tabs = QTabWidget()
        tabs.addTab(CharucoTab(self._status, self._progress), "ChArUco")
        tabs.addTab(
            ArucoGridTab(
                self._status, self._progress, ARUCO_DICTS, "arucogrid",
                default_dict_index=5,  # DICT_5X5_250
            ),
            "ArUco",
        )
        tabs.addTab(
            ArucoGridTab(
                self._status, self._progress, APRILTAG_DICTS, "apriltag",
                default_dict_index=3,  # DICT_APRILTAG_36h11
            ),
            "AprilTag",
        )
        tabs.addTab(FiducialTab(self._status, self._progress), "Chessboard")
        tabs.setCurrentIndex(0)
        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
