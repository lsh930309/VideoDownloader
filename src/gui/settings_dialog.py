from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QFileDialog, QComboBox,
                             QCheckBox, QSpinBox, QTabWidget, QWidget, QGroupBox,
                             QFormLayout, QMessageBox, QProgressDialog, QTextBrowser)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.core.config import config
from src.core.ffmpeg_installer import FFmpegInstaller
from src.core.ytdlp_plugin_installer import YtDlpPluginInstaller


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


class BenchmarkThread(QThread):
    """네트워크 벤치마크를 백그라운드에서 수행하는 스레드"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            from src.core.network_benchmark import NetworkBenchmark
            result = NetworkBenchmark.run_benchmark(
                progress_callback=lambda p: self.progress.emit(p),
                status_callback=lambda s: self.status.emit(s)
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PluginInstallThread(QThread):
    """yt-dlp 플러그인 설치를 백그라운드에서 수행하는 스레드"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)

    def run(self):
        try:
            success = YtDlpPluginInstaller.install_plugin(
                progress_callback=lambda p: self.progress.emit(p)
            )
            self.finished.emit(success)
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
        self.format_combo.addItems(["mp4", "mkv"])
        # 하위 호환성: 이전 설정값들을 output_format으로 마이그레이션
        output_format = config.get("output_format") or config.get("preferred_format") or config.get("default_format") or "mp4"
        # ts는 더 이상 지원하지 않으므로 mp4로 변환
        if output_format == "ts":
            output_format = "mp4"
        self.format_combo.setCurrentText(output_format)
        quality_layout.addRow("출력 포맷:", self.format_combo)

        format_note = QLabel("지정 화질의 최고 품질로 다운로드 후 선택한 포맷으로 변환합니다")
        format_note.setStyleSheet("color: gray; font-size: 9px;")
        format_note.setWordWrap(True)
        quality_layout.addRow("", format_note)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        # 쿠키/인증 설정
        cookie_group = QGroupBox("쿠키 인증 (YouTube Premium, 봇 검증 우회)")
        cookie_layout = QFormLayout()

        # 쿠키 사용 여부
        self.cookies_enabled_check = QCheckBox("쿠키 인증 사용")
        self.cookies_enabled_check.setChecked(config.get("cookies_enabled"))
        self.cookies_enabled_check.toggled.connect(self.on_cookies_enabled_toggled)
        cookie_layout.addRow("", self.cookies_enabled_check)

        # 브라우저 선택 (방법 1 - 추천)
        browser_h_layout = QHBoxLayout()
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["(사용 안 함)", "chrome", "firefox", "edge", "brave", "opera", "safari"])
        current_browser = config.get("cookies_from_browser") or "(사용 안 함)"
        if current_browser and current_browser != "(사용 안 함)":
            self.browser_combo.setCurrentText(current_browser)
        browser_h_layout.addWidget(self.browser_combo)
        cookie_layout.addRow("브라우저에서 가져오기:", browser_h_layout)

        browser_note = QLabel("브라우저에 로그인한 상태로 쿠키를 자동으로 가져옵니다 (권장)")
        browser_note.setStyleSheet("color: gray; font-size: 9px;")
        browser_note.setWordWrap(True)
        cookie_layout.addRow("", browser_note)

        # 쿠키 파일 경로 (방법 2 - 고급)
        cookie_file_h_layout = QHBoxLayout()
        self.cookies_file_edit = QLineEdit(config.get("cookies_file_path"))
        self.cookies_file_btn = QPushButton("찾아보기")
        self.cookies_file_btn.clicked.connect(self.browse_cookies_file)
        cookie_file_h_layout.addWidget(self.cookies_file_edit)
        cookie_file_h_layout.addWidget(self.cookies_file_btn)
        cookie_layout.addRow("쿠키 파일 (고급):", cookie_file_h_layout)

        file_note = QLabel("Netscape 형식 cookies.txt 파일. 브라우저 설정이 우선됩니다")
        file_note.setStyleSheet("color: gray; font-size: 9px;")
        file_note.setWordWrap(True)
        cookie_layout.addRow("", file_note)

        # Chrome 쿠키 잠금 문제 해결 버튼
        chrome_fix_layout = QHBoxLayout()
        self.install_plugin_btn = QPushButton("Chrome 쿠키 플러그인 설치")
        self.install_plugin_btn.clicked.connect(self.install_ytdlp_plugin)
        self.install_plugin_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        chrome_fix_layout.addWidget(self.install_plugin_btn)

        self.plugin_help_btn = QPushButton("?")
        self.plugin_help_btn.setFixedWidth(30)
        self.plugin_help_btn.clicked.connect(self.show_plugin_help)
        chrome_fix_layout.addWidget(self.plugin_help_btn)
        chrome_fix_layout.addStretch()

        cookie_layout.addRow("Chrome 114+ 문제 해결:", chrome_fix_layout)

        plugin_note = QLabel("Chrome이 실행 중일 때 쿠키를 가져오지 못한다면 플러그인을 설치하세요")
        plugin_note.setStyleSheet("color: #FF5722; font-size: 9px; font-weight: bold;")
        plugin_note.setWordWrap(True)
        cookie_layout.addRow("", plugin_note)

        cookie_group.setLayout(cookie_layout)
        layout.addWidget(cookie_group)

        # 초기 상태 설정
        self.on_cookies_enabled_toggled(self.cookies_enabled_check.isChecked())

        layout.addStretch()
        return widget

    def create_performance_tab(self):
        """성능 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 다운로드 성능 설정
        download_group = QGroupBox("병렬 다운로드 설정")
        download_layout = QFormLayout()

        # 동시 프래그먼트 수
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 16)
        self.concurrent_spin.setValue(config.get("concurrent_fragments"))
        self.concurrent_spin.setSuffix(" 개")
        concurrent_label = QLabel("동시 다운로드 조각 수")
        download_layout.addRow(concurrent_label, self.concurrent_spin)

        perf_note = QLabel("※ 청크 크기, 버퍼 등의 네트워크 최적화는 yt-dlp가 자동으로 처리합니다")
        perf_note.setStyleSheet("color: gray; font-size: 9px;")
        perf_note.setWordWrap(True)
        download_layout.addRow("", perf_note)

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

        # 자동 최적화 버튼
        auto_group = QGroupBox("자동 최적화")
        auto_layout = QVBoxLayout()

        auto_note = QLabel("시스템 환경(CPU)을 기반으로 간단히 설정하거나, 네트워크 벤치마크로 정밀 측정할 수 있습니다")
        auto_note.setStyleSheet("color: gray; font-size: 10px;")
        auto_note.setWordWrap(True)
        auto_layout.addWidget(auto_note)

        auto_buttons = QHBoxLayout()

        auto_btn = QPushButton("간단 자동 설정")
        auto_btn.clicked.connect(self.apply_auto_settings)
        auto_buttons.addWidget(auto_btn)

        benchmark_btn = QPushButton("네트워크 벤치마크")
        benchmark_btn.clicked.connect(self.run_benchmark)
        auto_buttons.addWidget(benchmark_btn)

        auto_layout.addLayout(auto_buttons)

        # 벤치마크 상태 표시
        benchmark_completed = config.get("benchmark_completed")
        if benchmark_completed:
            optimal_workers = config.get("benchmark_optimal_workers")
            min_size = config.get("benchmark_min_size_per_worker")
            benchmark_status = QLabel(f"✓ 벤치마크 완료 (최적 워커: {optimal_workers}개, 워커당 최소: {min_size}MB)")
            benchmark_status.setStyleSheet("color: green; font-size: 9px;")
        else:
            benchmark_status = QLabel("벤치마크 미실행 - CPU 기반 기본값 사용 중")
            benchmark_status.setStyleSheet("color: gray; font-size: 9px;")

        benchmark_status.setWordWrap(True)
        auto_layout.addWidget(benchmark_status)

        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)

        layout.addStretch()
        return widget

    def apply_auto_settings(self):
        """시스템 환경 기반 자동 설정 적용"""
        from src.core.auto_config import AutoConfig

        try:
            concurrent_fragments = AutoConfig.get_optimal_concurrent_fragments()
            self.concurrent_spin.setValue(concurrent_fragments)

            QMessageBox.information(
                self,
                "자동 설정 완료",
                f"CPU 코어 수에 맞는 최적 설정이 적용되었습니다.\n\n"
                f"병렬 다운로드 수: {concurrent_fragments}개\n\n"
                f"※ 청크 크기, 버퍼 등의 네트워크 최적화는\n"
                f"   yt-dlp가 자동으로 처리합니다"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "자동 설정 실패",
                f"자동 설정 중 오류가 발생했습니다:\n{e}"
            )

    def run_benchmark(self):
        """네트워크 벤치마크 실행"""
        import os
        cpu_count = os.cpu_count() or 4

        # 테스트 횟수 계산 (1, 2, 4, 8, 16, ... CPU 코어 수까지)
        test_count = 0
        workers = 1
        while workers <= cpu_count:
            test_count += 1
            workers *= 2

        # 예상 데이터 사용량 (A/B 테스트: 각각 824MB)
        # A 영상: 824MB * test_count
        # B 영상: 824MB * test_count (부분 다운로드)
        estimated_data_mb = 824 * test_count * 2  # A/B 테스트
        estimated_data_gb = estimated_data_mb / 1024

        # 확인 대화상자
        reply = QMessageBox.question(
            self,
            "네트워크 벤치마크",
            f"A/B 테스트 벤치마크를 실행하면 작은 파일과 큰 파일로\n"
            f"각각 테스트하여 최적의 병렬 다운로드 설정을 찾습니다.\n\n"
            f"테스트: A 영상(작은 파일) + B 영상(큰 파일 부분)\n"
            f"워커 범위: 1~{cpu_count}개 (총 {test_count}가지 설정)\n"
            f"예상 소요 시간: 10-20분\n"
            f"예상 데이터 사용량: 약 {estimated_data_gb:.1f}GB\n\n"
            f"벤치마크를 실행하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 진행 대화상자 생성
        self.benchmark_dialog = QProgressDialog("벤치마크 초기화 중...", "취소", 0, 100, self)
        self.benchmark_dialog.setWindowTitle("네트워크 벤치마크")
        self.benchmark_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.benchmark_dialog.setAutoClose(False)
        self.benchmark_dialog.setAutoReset(False)
        self.benchmark_dialog.canceled.connect(self.cancel_benchmark)

        # 벤치마크 스레드 시작
        self.benchmark_thread = BenchmarkThread()
        self.benchmark_thread.progress.connect(self.update_benchmark_progress)
        self.benchmark_thread.status.connect(self.update_benchmark_status)
        self.benchmark_thread.finished.connect(self.benchmark_finished)
        self.benchmark_thread.error.connect(self.benchmark_error)
        self.benchmark_thread.start()

        self.benchmark_dialog.show()

    def cancel_benchmark(self):
        """벤치마크 취소"""
        if hasattr(self, 'benchmark_thread') and self.benchmark_thread.isRunning():
            self.benchmark_thread.terminate()
            self.benchmark_thread.wait()

    def update_benchmark_progress(self, percent):
        """벤치마크 진행률 업데이트"""
        if hasattr(self, 'benchmark_dialog'):
            self.benchmark_dialog.setValue(percent)

    def update_benchmark_status(self, status):
        """벤치마크 상태 메시지 업데이트"""
        if hasattr(self, 'benchmark_dialog'):
            self.benchmark_dialog.setLabelText(status)

    def benchmark_finished(self, result):
        """벤치마크 완료"""
        if hasattr(self, 'benchmark_dialog'):
            self.benchmark_dialog.close()

        # 결과 저장
        optimal_workers = result['optimal_workers']
        min_size_per_worker = result['min_size_per_worker']
        best_speed = result['best_speed_mbps']
        avg_speed_mb_per_sec = result.get('avg_download_speed_mb_per_sec', best_speed / 8)

        config.set("benchmark_completed", True)
        config.set("benchmark_optimal_workers", optimal_workers)
        config.set("benchmark_min_size_per_worker", min_size_per_worker)

        # UI 업데이트
        self.concurrent_spin.setValue(optimal_workers)

        # 결과 표시
        QMessageBox.information(
            self,
            "A/B 벤치마크 완료",
            f"A/B 테스트 벤치마크가 완료되었습니다!\n\n"
            f"최고 속도: {best_speed:.1f} Mbps ({avg_speed_mb_per_sec:.1f} MB/s)\n"
            f"최적 워커 수: {optimal_workers}개 (자원 효율 고려)\n"
            f"워커당 최소 크기: {min_size_per_worker}MB (I/O 병목 방지)\n\n"
            f"※ 10% 이내 성능 차이 시 더 적은 워커 선택\n"
            f"※ 파일 크기에 따라 워커 수가 동적으로 조정됩니다\n\n"
            f"이 설정이 자동으로 적용되었습니다."
        )

    def benchmark_error(self, error_msg):
        """벤치마크 실패"""
        if hasattr(self, 'benchmark_dialog'):
            self.benchmark_dialog.close()

        QMessageBox.critical(
            self,
            "벤치마크 실패",
            f"벤치마크 중 오류가 발생했습니다:\n\n{error_msg}\n\n"
            f"네트워크 연결을 확인하거나 나중에 다시 시도해주세요."
        )

    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "다운로드 경로 선택")
        if path:
            self.path_edit.setText(path)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "FFmpeg 실행 파일 선택", filter="Executables (*.exe)")
        if path:
            self.ffmpeg_edit.setText(path)

    def browse_cookies_file(self):
        """쿠키 파일 선택"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "쿠키 파일 선택 (Netscape 형식)",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        if path:
            self.cookies_file_edit.setText(path)

    def on_cookies_enabled_toggled(self, checked):
        """쿠키 활성화 체크박스 토글 시 호출"""
        self.browser_combo.setEnabled(checked)
        self.cookies_file_edit.setEnabled(checked)
        self.cookies_file_btn.setEnabled(checked)

    def show_plugin_help(self):
        """Chrome 쿠키 플러그인 도움말 표시"""
        help_text = """
<h3>Chrome 쿠키 잠금 문제란?</h3>
<p>Chrome 114 이상 버전에서는 보안 기능으로 인해 Chrome이 <b>실행 중일 때</b> 쿠키 파일에 접근할 수 없습니다.</p>

<h3>증상</h3>
<ul>
<li>Chrome에서 쿠키를 가져오지 못하는 에러 발생</li>
<li>PermissionError: [Errno 13] Permission denied</li>
</ul>

<h3>해결 방법</h3>
<p><b>방법 1: 플러그인 설치 (권장)</b></p>
<ul>
<li>"Chrome 쿠키 플러그인 설치" 버튼 클릭</li>
<li>yt-dlp-ChromeCookieUnlock 플러그인이 자동으로 설치됩니다</li>
<li>Chrome을 닫지 않고도 쿠키를 가져올 수 있습니다</li>
</ul>

<p><b>방법 2: Chrome 종료 후 사용</b></p>
<ul>
<li>다운로드 전에 Chrome을 완전히 종료</li>
<li>백그라운드 프로세스도 모두 종료 확인</li>
</ul>

<p><b>방법 3: Firefox 사용</b></p>
<ul>
<li>브라우저를 Firefox로 변경</li>
<li>Firefox는 쿠키 잠금 문제가 없습니다</li>
</ul>

<h3>참고</h3>
<p>이 문제는 Chrome의 의도적인 보안 기능으로, yt-dlp와 무관한 Chrome 측 변경사항입니다.</p>
<p>더 자세한 정보: <a href="https://github.com/yt-dlp/yt-dlp/issues/7271">GitHub 이슈 #7271</a></p>
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Chrome 쿠키 플러그인 도움말")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def install_ytdlp_plugin(self):
        """yt-dlp Chrome 쿠키 플러그인 설치"""
        # 이미 설치되어 있는지 확인
        if YtDlpPluginInstaller.check_plugin_installed():
            QMessageBox.information(
                self,
                "플러그인 확인",
                f"{YtDlpPluginInstaller.PLUGIN_NAME} 플러그인이 이미 설치되어 있습니다.\n\n"
                "Chrome이 실행 중일 때도 쿠키를 가져올 수 있습니다."
            )
            return

        # 설치 확인
        reply = QMessageBox.question(
            self,
            "플러그인 설치",
            f"{YtDlpPluginInstaller.PLUGIN_NAME} 플러그인을 설치하시겠습니까?\n\n"
            "이 플러그인은 Chrome이 실행 중일 때도 쿠키를 가져올 수 있게 해줍니다.\n"
            "설치에는 인터넷 연결이 필요하며 몇 초가 소요됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 진행 대화상자
        progress = QProgressDialog("플러그인 설치 중...", "취소", 0, 100, self)
        progress.setWindowTitle("yt-dlp 플러그인 설치")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)  # 취소 버튼 비활성화
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # 설치 스레드 생성 및 시작
        self.plugin_thread = PluginInstallThread()
        self.plugin_thread.progress.connect(progress.setValue)
        self.plugin_thread.finished.connect(
            lambda success: self.on_plugin_install_finished(success, progress)
        )
        self.plugin_thread.error.connect(
            lambda error: self.on_plugin_install_error(error, progress)
        )
        self.plugin_thread.start()

    def on_plugin_install_finished(self, success, progress):
        """플러그인 설치 완료 콜백"""
        progress.close()

        if success:
            QMessageBox.information(
                self,
                "설치 완료",
                f"{YtDlpPluginInstaller.PLUGIN_NAME} 플러그인이 성공적으로 설치되었습니다.\n\n"
                "이제 Chrome이 실행 중일 때도 쿠키를 가져올 수 있습니다."
            )
        else:
            QMessageBox.warning(
                self,
                "설치 실패",
                f"플러그인 설치에 실패했습니다.\n\n"
                "인터넷 연결을 확인하거나 수동으로 다음 명령을 실행해보세요:\n"
                f"pip install {YtDlpPluginInstaller.PLUGIN_PACKAGE}"
            )

    def on_plugin_install_error(self, error_msg, progress):
        """플러그인 설치 오류 콜백"""
        progress.close()
        QMessageBox.critical(
            self,
            "설치 오류",
            f"플러그인 설치 중 오류가 발생했습니다:\n\n{error_msg}"
        )

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
        config.set("output_format", self.format_combo.currentText())

        # 쿠키 설정 저장
        config.set("cookies_enabled", self.cookies_enabled_check.isChecked())

        browser_selection = self.browser_combo.currentText()
        if browser_selection == "(사용 안 함)":
            config.set("cookies_from_browser", "")
        else:
            config.set("cookies_from_browser", browser_selection)

        config.set("cookies_file_path", self.cookies_file_edit.text())

        # 성능 설정 저장
        config.set("concurrent_fragments", self.concurrent_spin.value())
        config.set("speed_limit_mbps", self.speed_spin.value())
        # chunk_size_mb, buffer_size_mb는 yt-dlp 자동 최적화에 맡기므로 저장하지 않음

        self.accept()
