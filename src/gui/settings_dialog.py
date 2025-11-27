from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt
from src.core.config import config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setFixedWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Download Path
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(config.get("download_path"))
        self.path_btn = QPushButton("찾아보기")
        self.path_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(QLabel("다운로드 경로:"))
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.path_btn)
        layout.addLayout(path_layout)

        # FFmpeg Path
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_edit = QLineEdit(config.get("ffmpeg_path"))
        self.ffmpeg_btn = QPushButton("찾아보기")
        self.ffmpeg_btn.clicked.connect(self.browse_ffmpeg)
        ffmpeg_layout.addWidget(QLabel("FFmpeg 경로:"))
        ffmpeg_layout.addWidget(self.ffmpeg_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_btn)
        layout.addLayout(ffmpeg_layout)

        # Default Quality
        quality_layout = QHBoxLayout()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "2160p", "1440p", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setCurrentText(config.get("default_quality"))
        quality_layout.addWidget(QLabel("기본 화질:"))
        quality_layout.addWidget(self.quality_combo)
        layout.addLayout(quality_layout)

        # Default Format
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "ts"])
        self.format_combo.setCurrentText(config.get("default_format"))
        format_layout.addWidget(QLabel("기본 포맷:"))
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Save Button
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "다운로드 경로 선택")
        if path:
            self.path_edit.setText(path)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "FFmpeg 실행 파일 선택", filter="Executables (*.exe)")
        if path:
            self.ffmpeg_edit.setText(path)

    def save_settings(self):
        config.set("download_path", self.path_edit.text())
        config.set("ffmpeg_path", self.ffmpeg_edit.text())
        config.set("default_quality", self.quality_combo.currentText())
        config.set("default_format", self.format_combo.currentText())
        self.accept()
