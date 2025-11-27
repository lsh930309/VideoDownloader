#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Video Downloader Build Script
포터블 패키지와 인스톨러 패키지를 생성합니다.
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path


class BuildManager:
    def __init__(self):
        # 경로 설정
        self.script_dir = Path(__file__).parent.resolve()
        self.project_root = self.script_dir.parent
        self.spec_file = self.script_dir / "video_downloader.spec"
        self.iss_file = self.script_dir / "setup_script.iss"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.release_dir = self.project_root / "release"
        self.app_name = "VideoDownloader"

        # Inno Setup 컴파일러 경로 (일반적인 설치 경로)
        self.iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup\ISCC.exe",
            r"C:\Program Files\Inno Setup\ISCC.exe",
        ]
        self.iscc_exe = None

    def print_step(self, message):
        """단계 출력"""
        print(f"\n{'='*60}")
        print(f"  {message}")
        print(f"{'='*60}\n")

    def print_success(self, message):
        """성공 메시지 출력"""
        print(f"✓ {message}")

    def print_error(self, message):
        """에러 메시지 출력"""
        print(f"✗ {message}", file=sys.stderr)

    def find_iscc(self):
        """Inno Setup 컴파일러 찾기"""
        for path in self.iscc_paths:
            if os.path.exists(path):
                self.iscc_exe = path
                return True
        return False

    def clean_build_dirs(self):
        """빌드 디렉토리 정리"""
        self.print_step("빌드 디렉토리 정리 중...")

        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.print_success(f"삭제됨: {dir_path}")

        print()

    def build_with_pyinstaller(self):
        """PyInstaller로 실행 파일 빌드"""
        self.print_step("PyInstaller로 실행 파일 빌드 중...")

        if not self.spec_file.exists():
            self.print_error(f"spec 파일을 찾을 수 없습니다: {self.spec_file}")
            return False

        try:
            # PyInstaller 실행
            cmd = ["pyinstaller", str(self.spec_file), "--clean"]
            print(f"실행 명령: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root, check=True)

            # 빌드 결과 확인
            app_dir = self.dist_dir / self.app_name
            if not app_dir.exists():
                self.print_error("빌드된 애플리케이션 폴더를 찾을 수 없습니다.")
                return False

            self.print_success(f"빌드 완료: {app_dir}")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"PyInstaller 빌드 실패: {e}")
            return False
        except FileNotFoundError:
            self.print_error("PyInstaller를 찾을 수 없습니다. 설치되어 있는지 확인하세요.")
            return False

    def create_portable_package(self):
        """포터블 패키지 생성 (ZIP)"""
        self.print_step("포터블 패키지 생성 중...")

        app_dir = self.dist_dir / self.app_name
        if not app_dir.exists():
            self.print_error("빌드된 애플리케이션 폴더를 찾을 수 없습니다.")
            return False

        # release 디렉토리 생성
        self.release_dir.mkdir(exist_ok=True)

        # ZIP 파일 생성
        zip_path = self.release_dir / f"{self.app_name}_Portable.zip"

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(app_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(app_dir.parent)
                        zipf.write(file_path, arcname)
                        print(f"  추가: {arcname}")

            # 파일 크기 확인
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            self.print_success(f"포터블 패키지 생성 완료: {zip_path} ({size_mb:.2f} MB)")
            return True

        except Exception as e:
            self.print_error(f"포터블 패키지 생성 실패: {e}")
            return False

    def create_installer_package(self):
        """인스톨러 패키지 생성 (Inno Setup)"""
        self.print_step("인스톨러 패키지 생성 중...")

        # Inno Setup 컴파일러 찾기
        if not self.find_iscc():
            self.print_error("Inno Setup 컴파일러를 찾을 수 없습니다.")
            print("다음 경로에서 찾았습니다:")
            for path in self.iscc_paths:
                print(f"  - {path}")
            print("\nInno Setup을 설치하세요: https://jrsoftware.org/isinfo.php")
            return False

        print(f"Inno Setup 컴파일러: {self.iscc_exe}")

        if not self.iss_file.exists():
            self.print_error(f"ISS 파일을 찾을 수 없습니다: {self.iss_file}")
            return False

        try:
            # Inno Setup 컴파일러 실행
            cmd = [self.iscc_exe, str(self.iss_file)]
            print(f"실행 명령: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.script_dir, check=True,
                                  capture_output=True, text=True)

            print(result.stdout)

            # 생성된 인스톨러 찾기
            installer_path = self.dist_dir / "VideoDownloaderSetup.exe"
            if not installer_path.exists():
                self.print_error("인스톨러 파일을 찾을 수 없습니다.")
                return False

            # release 디렉토리로 이동
            self.release_dir.mkdir(exist_ok=True)
            dest_path = self.release_dir / installer_path.name
            shutil.move(str(installer_path), str(dest_path))

            # 파일 크기 확인
            size_mb = dest_path.stat().st_size / (1024 * 1024)
            self.print_success(f"인스톨러 패키지 생성 완료: {dest_path} ({size_mb:.2f} MB)")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"Inno Setup 컴파일 실패: {e}")
            if e.stderr:
                print(e.stderr)
            return False
        except Exception as e:
            self.print_error(f"인스톨러 패키지 생성 실패: {e}")
            return False

    def list_release_files(self):
        """릴리스 파일 목록 출력"""
        self.print_step("릴리스 패키지")

        if not self.release_dir.exists():
            print("릴리스 폴더가 없습니다.")
            return

        files = list(self.release_dir.glob("*"))
        if not files:
            print("릴리스 파일이 없습니다.")
            return

        print(f"폴더: {self.release_dir}\n")
        for file in sorted(files):
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  - {file.name} ({size_mb:.2f} MB)")
        print()

    def run(self, clean=True):
        """빌드 프로세스 실행"""
        print("\n" + "="*60)
        print("  Video Downloader 빌드 스크립트")
        print("="*60)

        # 1. 빌드 디렉토리 정리
        if clean:
            self.clean_build_dirs()

        # 2. PyInstaller로 빌드
        if not self.build_with_pyinstaller():
            self.print_error("빌드 실패: PyInstaller 단계에서 오류 발생")
            return False

        # 3. 포터블 패키지 생성
        portable_success = self.create_portable_package()

        # 4. 인스톨러 패키지 생성
        installer_success = self.create_installer_package()

        # 5. 결과 출력
        self.list_release_files()

        # 6. 최종 결과
        if portable_success and installer_success:
            self.print_step("빌드 완료!")
            print("모든 패키지가 성공적으로 생성되었습니다.\n")
            return True
        elif portable_success or installer_success:
            self.print_step("빌드 부분 완료")
            if not portable_success:
                print("포터블 패키지 생성 실패")
            if not installer_success:
                print("인스톨러 패키지 생성 실패 (Inno Setup 미설치 가능성)")
            print()
            return True
        else:
            self.print_error("빌드 실패: 패키지 생성 단계에서 오류 발생")
            return False


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Video Downloader 빌드 스크립트")
    parser.add_argument("--no-clean", action="store_true",
                       help="빌드 전에 디렉토리를 정리하지 않습니다")
    args = parser.parse_args()

    builder = BuildManager()
    success = builder.run(clean=not args.no_clean)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
