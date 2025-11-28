import asyncio
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QProgressBar, QTextEdit,
                             QLabel, QComboBox, QMessageBox, QMenuBar)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QObject
from qasync import QEventLoop, asyncSlot

from src.core.downloader import VideoDownloader
from src.core.config import config
from src.gui.settings_dialog import SettingsDialog


class OutputRedirector(QObject):
    """stdout/stderr를 GUI 로그 영역으로 리다이렉트"""
    output_written = pyqtSignal(str)

    def __init__(self, original_stream=None):
        super().__init__()
        self.original_stream = original_stream

    def write(self, text):
        if text.strip():  # 빈 줄 무시
            self.output_written.emit(text.rstrip())
        # 원래 스트림에도 출력 (디버깅용)
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

class MainWindow(QMainWindow):
    progress_signal = pyqtSignal(float)
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("비디오 다운로더")
        self.resize(600, 450)

        self.downloader = VideoDownloader()

        # Connect signals
        self.progress_signal.connect(self.update_progress)
        self.status_signal.connect(self.update_status)

        self.setup_ui()

        # stdout/stderr 리다이렉트 설정
        self.setup_output_redirect()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Menu
        menu_bar = self.menuBar()
        settings_action = menu_bar.addAction("설정")
        settings_action.triggered.connect(self.open_settings)

        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("동영상 주소를 입력하세요...")
        url_layout.addWidget(QLabel("주소:"))
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        # Quick Options (Quality & Format overrides)
        options_layout = QHBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setCurrentText(config.get("default_quality"))
        options_layout.addWidget(QLabel("화질:"))
        options_layout.addWidget(self.quality_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "ts"])
        self.format_combo.setCurrentText(config.get("default_format"))
        options_layout.addWidget(QLabel("포맷:"))
        options_layout.addWidget(self.format_combo)

        layout.addLayout(options_layout)

        # Download Button
        self.download_btn = QPushButton("다운로드")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setFixedHeight(40)
        layout.addWidget(self.download_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Refresh UI with new settings if needed
            self.quality_combo.setCurrentText(config.get("default_quality"))
            self.format_combo.setCurrentText(config.get("default_format"))
            self.log("설정이 업데이트되었습니다.")

    def log(self, message):
        self.log_area.append(message)
        self.scroll_to_bottom()

    def update_progress(self, percent):
        self.progress_bar.setValue(int(percent))

    def update_status(self, message):
        if "다운로드 중:" in message or "Downloading:" in message:
             self.statusBar().showMessage(message)
        else:
             self.log(message)

    @asyncSlot()
    async def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "오류", "주소를 입력해주세요.")
            return

        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log(f"다운로드 시작: {url}")

        config.set("default_quality", self.quality_combo.currentText())
        config.set("default_format", self.format_combo.currentText())

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self.downloader.download, 
                url, 
                self.update_progress_safe, 
                self.update_status_safe
            )
            self.log("다운로드가 성공적으로 완료되었습니다!")
            QMessageBox.information(self, "성공", "다운로드 완료.")
        except Exception as e:
            self.log(f"오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"다운로드 실패: {str(e)}")
        finally:
            self.download_btn.setEnabled(True)

    def update_progress_safe(self, percent):
        self.progress_signal.emit(percent)

    def update_status_safe(self, message):
        self.status_signal.emit(message)

    def setup_output_redirect(self):
        """stdout/stderr를 로그 영역으로 리다이렉트"""
        # stdout 리다이렉트
        self.stdout_redirector = OutputRedirector(sys.stdout)
        self.stdout_redirector.output_written.connect(self.append_log_output)
        sys.stdout = self.stdout_redirector

        # stderr 리다이렉트 (에러 메시지)
        self.stderr_redirector = OutputRedirector(sys.stderr)
        self.stderr_redirector.output_written.connect(self.append_log_error)
        sys.stderr = self.stderr_redirector

        # 초기 메시지
        print("비디오 다운로더 시작됨")
        print(f"설정 파일 위치: {config.CONFIG_FILE}")

    def append_log_output(self, text):
        """일반 출력을 로그에 추가"""
        self.log_area.append(f"<span style='color: black;'>{text}</span>")
        self.scroll_to_bottom()

    def append_log_error(self, text):
        """에러 출력을 로그에 추가 (빨간색)"""
        self.log_area.append(f"<span style='color: red;'>[ERROR] {text}</span>")
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """로그를 맨 아래로 스크롤"""
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event):
        """윈도우 닫을 때 stdout/stderr 복원"""
        if hasattr(self, 'stdout_redirector'):
            sys.stdout = self.stdout_redirector.original_stream
        if hasattr(self, 'stderr_redirector'):
            sys.stderr = self.stderr_redirector.original_stream
        event.accept()
