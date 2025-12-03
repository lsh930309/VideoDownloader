"""
자동 성능 설정 모듈

시스템 환경(CPU)을 분석하여 최적의 병렬 다운로드 수를 자동으로 계산합니다.
나머지 네트워크 최적화는 yt-dlp의 자동 조절에 맡깁니다.
"""
import os


class AutoConfig:
    """시스템 환경 기반 자동 성능 설정"""

    @staticmethod
    def get_optimal_concurrent_fragments():
        """
        CPU 코어 수를 기반으로 최적의 동시 다운로드 수를 계산

        Returns:
            int: 최적의 concurrent_fragments 값
        """
        cpu_count = os.cpu_count() or 4

        # CPU 코어 수 기반 동시 다운로드 수 계산
        # 과도한 병렬화를 방지하기 위해 보수적으로 설정
        # 경험적으로 4-8개가 대부분의 환경에서 최적
        if cpu_count >= 8:
            concurrent_fragments = 8
        elif cpu_count >= 4:
            concurrent_fragments = 6
        else:
            concurrent_fragments = 4

        print(f"[AutoConfig] CPU 코어: {cpu_count}개")
        print(f"[AutoConfig] 최적 병렬 다운로드 수: {concurrent_fragments}개")
        print(f"[AutoConfig] 참고: 청크 크기, 버퍼 등은 yt-dlp가 자동으로 최적화합니다")

        return concurrent_fragments

    @staticmethod
    def apply_auto_settings():
        """
        자동 설정을 계산하고 config에 적용

        Returns:
            int: 적용된 concurrent_fragments 값
        """
        from .config import config

        concurrent_fragments = AutoConfig.get_optimal_concurrent_fragments()
        config.set('concurrent_fragments', concurrent_fragments)

        return concurrent_fragments
