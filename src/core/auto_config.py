"""
자동 성능 설정 모듈

시스템 환경(CPU)을 분석하여 기본 병렬 다운로드 수를 계산합니다.
벤치마크 수행 후에는 벤치마크 결과를 우선 사용합니다.
"""
import os


class AutoConfig:
    """시스템 환경 기반 자동 성능 설정"""

    @staticmethod
    def get_optimal_concurrent_fragments():
        """
        CPU 코어 수를 기반으로 기본 동시 다운로드 수를 계산
        벤치마크 결과가 있으면 이를 우선 사용

        Returns:
            int: 최적의 concurrent_fragments 값
        """
        from .config import config

        cpu_count = os.cpu_count() or 4

        # 벤치마크 결과 확인
        benchmark_completed = config.get("benchmark_completed")
        benchmark_optimal = config.get("benchmark_optimal_workers")

        # 벤치마크 결과가 있으면 이를 사용
        if benchmark_completed and benchmark_optimal:
            print(f"[AutoConfig] 벤치마크 결과 사용: {benchmark_optimal}개 워커")
            return benchmark_optimal

        # 벤치마크가 없으면 CPU 기반 계산
        if cpu_count >= 8:
            max_workers = 8
        elif cpu_count >= 4:
            max_workers = 6
        else:
            max_workers = 4

        print(f"[AutoConfig] CPU 코어: {cpu_count}개")
        print(f"[AutoConfig] CPU 기반 기본값: {max_workers}개 워커")

        return max_workers

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
