"""Native Desktop Application for Election Analysis (2009–2024).

Combines a PySide6 native Qt desktop window (QtWebEngineView Chromium)
with an embedded local Streamlit server for a seamless desktop experience.

Features:
- Fast socket and proxy-free health polling
- Explicit 127.0.0.1 IPv4 address binding (avoids IPv6 connection refused)
- Startup error capture and logging to desktop_server.log
- Dark-themed window styling matching the modern web UI
- Status bar displaying server port and connection status
- Menu items for View Reload, Fullscreen, Zoom, and PNG Screenshot export
- Clean background server termination on exit
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

# Force proxy bypass for local loopback
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

# PyInstaller / frozen executable resource resolution
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent

# Ensure src is in python path
sys.path.insert(0, str(ROOT / "src"))


def find_free_port(start_port: int = 8501, max_attempts: int = 50) -> int:
    """Finds an open TCP port on localhost without locking it in TIME_WAIT."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Fast socket-level connectivity probe that bypasses HTTP/proxy issues."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False


def wait_for_server(port: int, server_process, timeout: float = 30.0, progress_callback=None) -> bool:
    """Polls the local server until it accepts TCP connections and responds to HTTP."""
    start_time = time.time()
    url = f"http://127.0.0.1:{port}"
    health_url = f"{url}/_stcore/health"

    # Configure proxy-free urllib opener
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        pct = min(95, int((elapsed / timeout) * 100))
        if progress_callback:
            progress_callback(pct, f"Initializing analytical engine... ({pct}%)")

        # Check if subprocess exited prematurely
        if isinstance(server_process, subprocess.Popen):
            poll = server_process.poll()
            if poll is not None:
                return False

        # Socket probe first
        if is_port_open(port):
            try:
                req = urllib.request.Request(health_url, headers={"User-Agent": "DesktopApp"})
                with opener.open(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        if progress_callback:
                            progress_callback(100, "Ready! Launching interface...")
                        return True
            except Exception:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "DesktopApp"})
                    with opener.open(req, timeout=1.0) as resp:
                        if resp.status == 200:
                            if progress_callback:
                                progress_callback(100, "Ready! Launching interface...")
                            return True
                except Exception:
                    pass

        time.sleep(0.4)
    return False


def start_streamlit_server(port: int) -> subprocess.Popen | threading.Thread:
    """Launches Streamlit bound explicitly to IPv4 127.0.0.1."""
    app_script = str(ROOT / "app" / "app.py")

    # If bundled as an executable by PyInstaller, run streamlit in a background daemon thread
    if getattr(sys, "frozen", False):
        import streamlit.web.cli as stcli

        def run_thread():
            sys.argv = [
                "streamlit",
                "run",
                app_script,
                f"--server.port={port}",
                "--server.address=127.0.0.1",
                "--server.headless=true",
                "--browser.gatherUsageStats=false",
                "--client.toolbarMode=minimal",
                "--client.showErrorLinks=false",
            ]
            stcli.main()

        server_thread = threading.Thread(target=run_thread, daemon=True)
        server_thread.start()
        return server_thread

    # Standard python execution via subprocess with explicit 127.0.0.1 binding
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_script,
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--client.toolbarMode=minimal",
        "--client.showErrorLinks=false",
    ]

    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = "127.0.0.1,localhost"

    # Write logs to desktop_server.log so errors can be inspected if needed
    log_file = ROOT / "desktop_server.log"
    log_fp = open(log_file, "w", encoding="utf-8", errors="replace")

    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=log_fp,
        stderr=log_fp,
        creationflags=creation_flags,
    )
    return process


def run_qt_app(port: int, server_process: subprocess.Popen | threading.Thread) -> int:
    """Runs the PySide6 Qt desktop window with embedded Chromium browser and splash screen."""
    from PySide6 import QtCore, QtGui, QtNetwork, QtWebEngineCore, QtWebEngineWidgets, QtWidgets

    # Ensure Qt does not attempt to proxy 127.0.0.1
    QtNetwork.QNetworkProxy.setApplicationProxy(QtNetwork.QNetworkProxy(QtNetwork.QNetworkProxy.NoProxy))

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Election Analysis Application")
    app.setOrganizationName("ElectionAnalysis")

    # Dark palette for Qt window chrome
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(22, 27, 34))
    dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(14, 17, 23))
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(22, 27, 34))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(22, 27, 34))
    dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(255, 153, 51))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(dark_palette)

    # ── Splash Screen ──
    splash = QtWidgets.QWidget(None, QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
    splash.resize(460, 240)
    splash.setStyleSheet(
        """
        QWidget {
            background-color: #161B22;
            border: 1px solid rgba(255, 153, 51, 0.4);
            border-radius: 14px;
        }
        QLabel {
            color: #F0F6FC;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            border: none;
        }
        QProgressBar {
            background-color: #0E1117;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            text-align: center;
            color: #FFF;
            height: 18px;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF9933, stop:1 #138808);
            border-radius: 7px;
        }
        """
    )

    layout = QtWidgets.QVBoxLayout(splash)
    layout.setContentsMargins(30, 30, 30, 30)

    title_lbl = QtWidgets.QLabel("🇮🇳 Lok Sabha Election Analytics")
    title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #FF9933;")
    title_lbl.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(title_lbl)

    subtitle_lbl = QtWidgets.QLabel("Popular Vote Share vs Seats Analysis (2009–2024)")
    subtitle_lbl.setStyleSheet("font-size: 12px; color: #94A3B8; margin-bottom: 15px;")
    subtitle_lbl.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(subtitle_lbl)

    pbar = QtWidgets.QProgressBar()
    pbar.setRange(0, 100)
    pbar.setValue(15)
    layout.addWidget(pbar)

    status_lbl = QtWidgets.QLabel("Starting analytical server...")
    status_lbl.setStyleSheet("font-size: 11px; color: #A0AEC0; margin-top: 8px;")
    status_lbl.setAlignment(QtCore.Qt.AlignCenter)
    layout.addWidget(status_lbl)

    screen = QtGui.QGuiApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        splash.move((geo.width() - splash.width()) // 2, (geo.height() - splash.height()) // 2)
    splash.show()
    app.processEvents()

    target_url = f"http://127.0.0.1:{port}"

    def update_splash(pct: int, msg: str):
        pbar.setValue(pct)
        status_lbl.setText(msg)
        app.processEvents()

    ready = wait_for_server(port, server_process, timeout=30.0, progress_callback=update_splash)

    if not ready:
        splash.close()
        err_msg = f"The analytical engine could not be reached on 127.0.0.1:{port}.\n"
        log_path = ROOT / "desktop_server.log"
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                log_data = f.read().strip()
            if log_data:
                err_msg += f"\nServer Log:\n{log_data[-800:]}"
        QtWidgets.QMessageBox.critical(None, "Startup Error", err_msg)
        return 1

    class ElectionMainWindow(QtWidgets.QMainWindow):
        def __init__(self, target_url: str, proc):
            super().__init__()
            self.target_url = target_url
            self.server_process = proc
            self.zoom_factor = 1.0
            self._has_loaded = False

            self.setWindowTitle("🇮🇳 Lok Sabha Election Analysis (2009–2024)")
            self.resize(1340, 880)

            # Center window
            if screen:
                geom = screen.availableGeometry()
                self.move(max(0, (geom.width() - self.width()) // 2), max(0, (geom.height() - self.height()) // 2))

            # Main Web Engine View
            self.browser = QtWebEngineWidgets.QWebEngineView(self)
            self.setCentralWidget(self.browser)

            # Native Chromium Download Handler (st.download_button and export support)
            self.profile = self.browser.page().profile()
            self.profile.downloadRequested.connect(self._on_download_requested)

            # Retry reload if initial frame had a temporary connection hiccup
            self.browser.loadFinished.connect(self._on_load_finished)

            # Status Bar
            self.status_bar = self.statusBar()
            self.status_bar.setStyleSheet(
                "QStatusBar { background: #161B22; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; padding: 4px; }"
            )
            self.status_bar.showMessage(
                f"● Local Desktop Engine: Port {port} | Status: Ready | Sources: India Data Portal / ECI"
            )

            # Setup Menus and Shortcuts
            self._setup_menus()

            # Load application URL
            self.browser.setUrl(QtCore.QUrl(self.target_url))

        def _on_load_finished(self, ok: bool):
            if not ok and not self._has_loaded:
                QtCore.QTimer.singleShot(1000, self.browser.reload)
            elif ok:
                self._has_loaded = True

        def _setup_menus(self):
            menubar = self.menuBar()
            menubar.setStyleSheet(
                "QMenuBar { background: #161B22; color: #F0F6FC; } QMenuBar::item:selected { background: #21262d; } QMenu { background: #161B22; color: #F0F6FC; border: 1px solid rgba(255,255,255,0.1); } QMenu::item:selected { background: rgba(255,153,51,0.25); }"
            )

            # File Menu
            file_menu = menubar.addMenu("&File")

            screenshot_action = QtGui.QAction("📸 &Export View as PNG Screenshot...", self)
            screenshot_action.setShortcut(QtGui.QKeySequence("Ctrl+S"))
            screenshot_action.triggered.connect(self._export_screenshot)
            file_menu.addAction(screenshot_action)

            export_folder_action = QtGui.QAction("📁 Open &Exports Folder...", self)
            export_folder_action.setShortcut(QtGui.QKeySequence("Ctrl+E"))
            export_folder_action.triggered.connect(self._open_export_folder)
            file_menu.addAction(export_folder_action)

            file_menu.addSeparator()

            reload_action = QtGui.QAction("&Reload Application", self)
            reload_action.setShortcut(QtGui.QKeySequence("F5"))
            reload_action.triggered.connect(self.browser.reload)
            file_menu.addAction(reload_action)

            fullscreen_action = QtGui.QAction("Toggle &Fullscreen", self)
            fullscreen_action.setShortcut(QtGui.QKeySequence("F11"))
            fullscreen_action.triggered.connect(self._toggle_fullscreen)
            file_menu.addAction(fullscreen_action)

            file_menu.addSeparator()

            exit_action = QtGui.QAction("E&xit", self)
            exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

            # View Menu
            view_menu = menubar.addMenu("&View")

            zoom_in = QtGui.QAction("Zoom &In", self)
            zoom_in.setShortcut(QtGui.QKeySequence("Ctrl++"))
            zoom_in.triggered.connect(self._zoom_in)
            view_menu.addAction(zoom_in)

            zoom_out = QtGui.QAction("Zoom &Out", self)
            zoom_out.setShortcut(QtGui.QKeySequence("Ctrl+-"))
            zoom_out.triggered.connect(self._zoom_out)
            view_menu.addAction(zoom_out)

            zoom_reset = QtGui.QAction("&Reset Zoom", self)
            zoom_reset.setShortcut(QtGui.QKeySequence("Ctrl+0"))
            zoom_reset.triggered.connect(self._zoom_reset)
            view_menu.addAction(zoom_reset)

            # Help Menu
            help_menu = menubar.addMenu("&Help")
            about_action = QtGui.QAction("&About Election Analysis App", self)
            about_action.triggered.connect(self._show_about)
            help_menu.addAction(about_action)

        def _toggle_fullscreen(self):
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        def _zoom_in(self):
            self.zoom_factor = min(2.5, self.zoom_factor + 0.1)
            self.browser.setZoomFactor(self.zoom_factor)

        def _zoom_out(self):
            self.zoom_factor = max(0.5, self.zoom_factor - 0.1)
            self.browser.setZoomFactor(self.zoom_factor)

        def _zoom_reset(self):
            self.zoom_factor = 1.0
            self.browser.setZoomFactor(self.zoom_factor)

        def _export_screenshot(self):
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export View as PNG Screenshot", "election_analysis_view.png", "PNG Images (*.png)"
            )
            if filename:
                pix = self.browser.grab()
                if pix.save(filename, "PNG"):
                    QtWidgets.QMessageBox.information(self, "Screenshot Saved", f"Successfully saved view to:\n{filename}")
                else:
                    QtWidgets.QMessageBox.warning(self, "Export Error", "Failed to save screenshot image.")

        def _open_export_folder(self):
            export_dir = ROOT / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(export_dir.resolve())))

        def _on_download_requested(self, download: QtWebEngineCore.QWebEngineDownloadRequest):
            """Handles file downloads initiated from within the embedded web engine."""
            suggested_name = download.suggestedFileName() or download.downloadFileName() or "exported_election_data.csv"
            default_dir = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DownloadLocation)
            if not default_dir or not os.path.exists(default_dir):
                default_dir = str(ROOT / "exports")
                os.makedirs(default_dir, exist_ok=True)

            default_path = os.path.join(default_dir, suggested_name)

            save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save Exported Data File",
                default_path,
                "CSV Files (*.csv);;All Files (*.*)",
            )

            if save_path:
                save_file = Path(save_path)
                save_file.parent.mkdir(parents=True, exist_ok=True)
                download.setDownloadDirectory(str(save_file.parent))
                download.setDownloadFileName(save_file.name)

                def on_state_changed(state):
                    if state == QtWebEngineCore.QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                        self.status_bar.showMessage(f"✓ Export complete: {save_file.name}", 8000)
                        QtWidgets.QMessageBox.information(
                            self,
                            "Export Succeeded",
                            f"File successfully exported and saved to:\n{save_path}",
                        )
                    elif state == QtWebEngineCore.QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
                        self.status_bar.showMessage(f"✕ Download interrupted: {save_file.name}", 8000)

                download.stateChanged.connect(on_state_changed)
                download.accept()
                self.status_bar.showMessage(f"Exporting {save_file.name}...", 4000)
            else:
                download.cancel()

        def _show_about(self):
            QtWidgets.QMessageBox.information(
                self,
                "About Election Analysis Application",
                "Lok Sabha Election Analysis Application (2009–2024)\n\n"
                "• Measures popular vote share vs seats under First-Past-The-Post.\n"
                "• Analyzes Gallagher disproportionality index and victory margins.\n"
                "• Explores coalition pacts, state footprints, and constituency breakdowns.\n"
                "• Post-delimitation general elections (2009, 2014, 2019, 2024).\n\n"
                "Data Sources: India Data Portal / ECI.",
            )

        def closeEvent(self, event: QtGui.QCloseEvent):
            """Ensure server process terminates cleanly on window exit."""
            if self.server_process:
                if isinstance(self.server_process, subprocess.Popen):
                    try:
                        if os.name == "nt":
                            self.server_process.terminate()
                            try:
                                self.server_process.wait(timeout=2)
                            except Exception:
                                self.server_process.kill()
                        else:
                            os.kill(self.server_process.pid, signal.SIGTERM)
                    except Exception:
                        pass
            event.accept()

    splash.close()
    window = ElectionMainWindow(target_url, server_process)
    window.show()
    return app.exec()


def main():
    print("=" * 65)
    print("  🇮🇳 Lok Sabha Election Analysis Application (2009–2024)")
    print("=" * 65)

    port = find_free_port(8501)
    print(f"[*] Starting local analytical server on port {port}...")

    server_proc = start_streamlit_server(port)

    print("[*] Initializing graphical desktop window...")
    try:
        exit_code = run_qt_app(port, server_proc)
        sys.exit(exit_code)
    except Exception as e:
        print(f"[!] Native desktop window error: {e}")
        if isinstance(server_proc, subprocess.Popen):
            try:
                server_proc.terminate()
                server_proc.wait(timeout=2)
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
