"""Launch the optional desktop application with installed Qt for Python."""

import sys
from pathlib import Path


def main() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont, QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "STEMLab desktop memerlukan PySide6 pada interpreter ini. "
            "Gunakan Python sistem yang memiliki PySide6; tidak ada paket yang dipasang otomatis.",
            file=sys.stderr,
        )
        return 1

    from stemlab.desktop.window import MainWindow

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_Use96Dpi)
    app = QApplication(sys.argv)
    app.setApplicationName("STEMLab")
    app.setOrganizationName("STEMLab")
    app.setDesktopFileName("STEMLab")
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("icon.svg"))))
    app.setFont(QFont("DejaVu Sans", 10))
    window = MainWindow()
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(min(1380, available.width() - 50), min(900, available.height() - 70))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
