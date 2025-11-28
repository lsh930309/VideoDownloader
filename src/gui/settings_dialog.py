from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QCheckBox, QSpinBox, QTabWidget, QWidget, QGroupBox,
                             QFormLayout, QMessageBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.core.config import config
from src.core.ffmpeg_installer import FFmpegInstaller


class FFmpegInstallThread(QThread):
    """FFmpeg 설치를 백그라운드에서 수행하는 스레드"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def run(self):
        try:
            ffmpeg_path = FFmpegInstaller.download_ffmpeg(
                progress_callback=lambda p: self.progress.emit(p)
            )
            self.finished.emit(ffmpeg_path)
        except Exception as e:
            self.error.emit(str(e))


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 탭 위젯 생성
        tab_widget = QTabWidget()

        # 일반 설정 탭
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "일반")

        # 성능 설정 탭
        performance_tab = self.create_performance_tab()
        tab_widget.addTab(performance_tab, "성능")

        layout.addWidget(tab_widget)

        # 저장/취소 버튼
        button_layout = QHBoxLayout()
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def create_general_tab(self):
        """일반 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 다운로드 경로
        path_group = QGroupBox("다운로드 설정")
        path_layout = QFormLayout()

        path_h_layout = QHBoxLayout()
        self.path_edit = QLineEdit(config.get("download_path"))
        self.path_btn = QPushButton("찾아보기")
        self.path_btn.clicked.connect(self.browse_path)
        path_h_layout.addWidget(self.path_edit)
        path_h_layout.addWidget(self.path_btn)
        path_layout.addRow("다운로드 경로:", path_h_layout)

        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # FFmpeg 설정
        ffmpeg_group = QGroupBox("FFmpeg 설정")
        ffmpeg_layout = QFormLayout()

        ffmpeg_h_layout = QHBoxLayout()
        self.ffmpeg_edit = QLineEdit(config.get("ffmpeg_path"))
        self.ffmpeg_btn = QPushButton("찾아보기")
        self.ffmpeg_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_h_layout.addWidget(self.ffmpeg_edit)
        ffmpeg_h_layout.addWidget(self.ffmpeg_btn)
        ffmpeg_layout.addRow("FFmpeg 경로:", ffmpeg_h_layout)

        ffmpeg_note = QLabel("비어있으면 시스템 PATH에서 찾습니다")
        ffmpeg_note.setStyleSheet("color: gray; font-size: 10px;")
        ffmpeg_layout.addRow("", ffmpeg_note)

        # FFmpeg 자동 설치 버튼
        auto_install_layout = QHBoxLayout()
        self.check_ffmpeg_btn = QPushButton("FFmpeg 확인")
        self.check_ffmpeg_btn.clicked.connect(self.check_ffmpeg)
        auto_install_layout.addWidget(self.check_ffmpeg_btn)

        self.auto_install_btn = QPushButton("FFmpeg 자동 설치")
        self.auto_install_btn.clicked.connect(self.auto_install_ffmpeg)
        auto_install_layout.addWidget(self.auto_install_btn)
        auto_install_layout.addStretch()

        ffmpeg_layout.addRow("", auto_install_layout)

        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)

        # 기본 품질 설정
        quality_group = QGroupBox("기본 설정")
        quality_layout = QFormLayout()

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setCurrentText(config.get("default_quality"))
        quality_layout.addRow("기본 화질:", self.quality_combo)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "ts"])
        self.format_combo.setCurrentText(config.get("default_format"))
        quality_layout.addRow("기본 포맷:", self.format_combo)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        layout.addStretch()
        return widget

    def create_performance_tab(self):
        """성능 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 다운로드 성능 설정
        download_group = QGroupBox("다운로드 성능")
        download_layout = QFormLayout()

        # 동시 프래그먼트 수
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 16)
        self.concurrent_spin.setValue(config.get("concurrent_fragments"))
        self.concurrent_spin.setSuffix(" 개")
        concurrent_label = QLabel("동시 다운로드 조각 수 (높을수록 빠름)")
        download_layout.addRow(concurrent_label, self.concurrent_spin)

        # 청크 크기
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1, 50)
        self.chunk_spin.setValue(config.get("chunk_size_mb"))
        self.chunk_spin.setSuffix(" MB")
        chunk_label = QLabel("청크 크기")
        download_layout.addRow(chunk_label, self.chunk_spin)

        # 버퍼 크기
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(4, 64)
        self.buffer_spin.setValue(config.get("buffer_size_mb"))
        self.buffer_spin.setSuffix(" MB")
        buffer_label = QLabel("버퍼 크기")
        download_layout.addRow(buffer_label, self.buffer_spin)

        download_group.setLayout(download_layout)
        layout.addWidget(download_group)

        # 속도 제한 설정
        speed_group = QGroupBox("속도 제한")
        speed_layout = QFormLayout()

        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 1000)
        self.speed_spin.setValue(config.get("speed_limit_mbps"))
        self.speed_spin.setSuffix(" Mbps")
        self.speed_spin.setSpecialValueText("무제한")
        speed_label = QLabel("최대 다운로드 속도 (0 = 무제한)")
        speed_layout.addRow(speed_label, self.speed_spin)

        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)

        # 성능 프리셋
        preset_group = QGroupBox("빠른 설정")
        preset_layout = QVBoxLayout()

        preset_note = QLabel("아래 버튼을 클릭하면 권장 설정이 자동으로 적용됩니다")
        preset_note.setStyleSheet("color: gray; font-size: 10px;")
        preset_layout.addWidget(preset_note)

        preset_buttons = QHBoxLayout()

        fast_btn = QPushButton("빠른 속도 (권장)")
        fast_btn.clicked.connect(lambda: self.apply_preset("fast"))
        preset_buttons.addWidget(fast_btn)

        balanced_btn = QPushButton("균형 (기본)")
        balanced_btn.clicked.connect(lambda: self.apply_preset("balanced"))
        preset_buttons.addWidget(balanced_btn)

        safe_btn = QPushButton("안정적")
        safe_btn.clicked.connect(lambda: self.apply_preset("safe"))
        preset_buttons.addWidget(safe_btn)

        preset_layout.addLayout(preset_buttons)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        layout.addStretch()
        return widget

    def apply_preset(self, preset):
        """성능 프리셋 적용"""
        if preset == "fast":
            self.concurrent_spin.setValue(16)
            self.chunk_spin.setValue(20)
            self.buffer_spin.setValue(32)
            self.speed_spin.setValue(0)
        elif preset == "balanced":
            self.concurrent_spin.setValue(8)
            self.chunk_spin.setValue(10)
            self.buffer_spin.setValue(16)
            self.speed_spin.setValue(0)
        elif preset == "safe":
            self.concurrent_spin.setValue(4)
            self.chunk_spin.setValue(5)
            self.buffer_spin.setValue(8)
            self.speed_spin.setValue(0)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "다운로드 경로 선택")
        if path:
            self.path_edit.setText(path)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "FFmpeg 실행 파일 선택", filter="Executables (*.exe)")
        if path:
            self.ffmpeg_edit.setText(path)

    def check_ffmpeg(self):
        """FFmpeg 설치 여부 확인"""
        ffmpeg_path = FFmpegInstaller.check_ffmpeg()
        if ffmpeg_path:
            QMessageBox.information(
                self,
                "FFmpeg 확인",
                f"FFmpeg가 설치되어 있습니다.\n\n경로: {ffmpeg_path}"
            )
            self.ffmpeg_edit.setText(ffmpeg_path)
        else:
            reply = QMessageBox.question(
                self,
                "FFmpeg 확인",
                "FFmpeg가 설치되어 있지 않습니다.\n\n지금 자동으로 설치하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.auto_install_ffmpeg()

    def auto_install_ffmpeg(self):
        """FFmpeg 자동 설치"""
        # 이미 설치되어 있는지 확인
        existing_path = FFmpegInstaller.check_ffmpeg()
        if existing_path:
            reply = QMessageBox.question(
                self,
                "FFmpeg 자동 설치",
                f"FFmpeg가 이미 설치되어 있습니다.\n경로: {existing_path}\n\n다시 설치하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 진행 대화상자 생성
        self.progress_dialog = QProgressDialog("FFmpeg 다운로드 중...", "취소", 0, 100, self)
        self.progress_dialog.setWindowTitle("FFmpeg 설치")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.canceled.connect(self.cancel_install)

        # 설치 스레드 시작
        self.install_thread = FFmpegInstallThread()
        self.install_thread.progress.connect(self.update_install_progress)
        self.install_thread.finished.connect(self.install_finished)
        self.install_thread.error.connect(self.install_error)
        self.install_thread.start()

        self.progress_dialog.show()

    def cancel_install(self):
        """설치 취소"""
        if hasattr(self, 'install_thread') and self.install_thread.isRunning():
            self.install_thread.terminate()
            self.install_thread.wait()

    def update_install_progress(self, percent):
        """설치 진행률 업데이트"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.setValue(percent)

    def install_finished(self, ffmpeg_path):
        """설치 완료"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        QMessageBox.information(
            self,
            "FFmpeg 설치 완료",
            f"FFmpeg 설치가 완료되었습니다!\n\n경로: {ffmpeg_path}\n\n설정에 자동으로 저장되었습니다."
        )
        self.ffmpeg_edit.setText(ffmpeg_path)

    def install_error(self, error_msg):
        """설치 실패"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()

        QMessageBox.critical(
            self,
            "FFmpeg 설치 실패",
            f"FFmpeg 설치 중 오류가 발생했습니다:\n\n{error_msg}\n\n수동으로 설치하거나 다시 시도해주세요."
        )

    def save_settings(self):
        # 일반 설정 저장
        config.set("download_path", self.path_edit.text())
        config.set("ffmpeg_path", self.ffmpeg_edit.text())
        config.set("default_quality", self.quality_combo.currentText())
        config.set("default_format", self.format_combo.currentText())

        # 성능 설정 저장
        config.set("concurrent_fragments", self.concurrent_spin.value())
        config.set("chunk_size_mb", self.chunk_spin.value())
        config.set("buffer_size_mb", self.buffer_spin.value())
        config.set("speed_limit_mbps", self.speed_spin.value())

        self.accept()
