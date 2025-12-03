import asyncio
import sys
import os
import subprocess
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QProgressBar, QTextEdit,
                             QLabel, QComboBox, QMessageBox, QMenuBar, QApplication)
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
        self.last_status_line = None  # \r 효과를 위한 마지막 상태 라인 추적

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

        # 붙여넣기 버튼
        paste_btn = QPushButton("붙여넣기")
        paste_btn.clicked.connect(self.paste_url)
        paste_btn.setFixedWidth(80)
        url_layout.addWidget(paste_btn)

        layout.addLayout(url_layout)

        # Quick Options (Quality & Format overrides)
        options_layout = QHBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setCurrentText(config.get("default_quality"))
        options_layout.addWidget(QLabel("화질:"))
        options_layout.addWidget(self.quality_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv"])
        # 하위 호환성: 이전 설정값들을 output_format으로 마이그레이션
        output_format = config.get("output_format") or config.get("preferred_format") or config.get("default_format") or "mp4"
        if output_format == "ts":
            output_format = "mp4"
        self.format_combo.setCurrentText(output_format)
        options_layout.addWidget(QLabel("출력 포맷:"))
        options_layout.addWidget(self.format_combo)

        layout.addLayout(options_layout)

        # Download Buttons
        download_layout = QHBoxLayout()

        self.download_btn = QPushButton("다운로드 시작")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setFixedHeight(40)
        download_layout.addWidget(self.download_btn)

        # 다운로드 폴더 열기 버튼
        open_folder_btn = QPushButton("다운로드 폴더")
        open_folder_btn.clicked.connect(self.open_download_folder)
        open_folder_btn.setFixedHeight(40)
        open_folder_btn.setFixedWidth(120)
        download_layout.addWidget(open_folder_btn)

        layout.addLayout(download_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def paste_url(self):
        """클립보드 내용을 URL 입력란에 붙여넣기"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.url_input.setText(text)
            self.log(f"클립보드에서 URL 붙여넣기: {text}")

    def open_download_folder(self):
        """다운로드 폴더를 탐색기로 열기"""
        download_path = config.get("download_path")

        # 폴더가 존재하지 않으면 생성
        if not os.path.exists(download_path):
            os.makedirs(download_path)
            self.log(f"다운로드 폴더 생성: {download_path}")

        # Windows Explorer로 폴더 열기
        if os.name == 'nt':  # Windows
            os.startfile(download_path)
        else:  # Linux/Mac
            subprocess.Popen(['xdg-open', download_path])

        self.log(f"다운로드 폴더 열기: {download_path}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Refresh UI with new settings if needed
            self.quality_combo.setCurrentText(config.get("default_quality"))
            output_format = config.get("output_format") or config.get("preferred_format") or config.get("default_format") or "mp4"
            if output_format == "ts":
                output_format = "mp4"
            self.format_combo.setCurrentText(output_format)
            self.log("설정이 업데이트되었습니다.")

    def log(self, message):
        self.log_area.append(message)
        self.scroll_to_bottom()

    def update_progress(self, percent):
        self.progress_bar.setValue(int(percent))

    def update_status(self, message):
        # 다운로드 진행 상황 메시지는 같은 줄에 덮어쓰기 (\r 효과)
        if "다운로드 중:" in message or "Downloading:" in message:
            # 상태바에도 표시
            self.statusBar().showMessage(message)

            # 로그 영역에서 마지막 줄 덮어쓰기
            if self.last_status_line is not None:
                # 마지막 줄 삭제
                cursor = self.log_area.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deletePreviousChar()  # 줄바꿈 문자 제거

            # 새 상태 추가
            self.log_area.append(f"<span style='color: blue;'>{message}</span>")
            self.scroll_to_bottom()
            self.last_status_line = message
        else:
            # 일반 메시지는 새 줄로 추가
            self.last_status_line = None
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
        config.set("output_format", self.format_combo.currentText())

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
