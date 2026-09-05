import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from frontend.app_window import WeatherApp, get_resource_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Yo Weather")
    app.setStyle("Fusion")

    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = WeatherApp()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
        
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()