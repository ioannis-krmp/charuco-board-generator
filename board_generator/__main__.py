import sys

from PyQt6.QtWidgets import QApplication

from board_generator.gui import BoardGeneratorApp


def main():
    app = QApplication(sys.argv)
    window = BoardGeneratorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
