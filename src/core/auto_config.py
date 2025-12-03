"""
자동 성능 설정 모듈

시스템 환경(CPU) 및 파일 크기를 분석하여 최적의 병렬 다운로드 수를 자동으로 계산합니다.
작은 파일에서는 과도한 병렬화로 인한 I/O 오버헤드를 방지합니다.
"""
import os


class AutoConfig:
    """시스템 환경 기반 자동 성능 설정"""

    # 각 워커당 최소 파일 크기 (MB) - 기본값
    # 벤치마크 완료 시 실측값으로 대체됨
    DEFAULT_MIN_SIZE_PER_WORKER_MB = 100

    @staticmethod
    def get_optimal_concurrent_fragments(file_size_mb=None):
        """
        CPU 코어 수와 파일 크기를 기반으로 최적의 동시 다운로드 수를 계산
        벤치마크 결과가 있으면 이를 우선 활용

        Args:
            file_size_mb: 다운로드할 파일 크기 (MB). None이면 CPU만 고려

        Returns:
            int: 최적의 concurrent_fragments 값
        """
        from .config import config

        cpu_count = os.cpu_count() or 4

        # 벤치마크 결과 확인
        benchmark_completed = config.get("benchmark_completed")
        benchmark_optimal = config.get("benchmark_optimal_workers")
        min_size_per_worker = config.get("benchmark_min_size_per_worker") or AutoConfig.DEFAULT_MIN_SIZE_PER_WORKER_MB

        # CPU 기반 최대 워커 수 계산
        if cpu_count >= 8:
            max_workers_cpu = 8
        elif cpu_count >= 4:
            max_workers_cpu = 6
        else:
            max_workers_cpu = 4

        # 벤치마크 결과가 있으면 이를 최대값으로 사용
        if benchmark_completed and benchmark_optimal:
            max_workers = benchmark_optimal
            print(f"[AutoConfig] 벤치마크 결과 사용: 최대 {max_workers}개 워커")
        else:
            max_workers = max_workers_cpu

        # 파일 크기를 모르는 경우
        if file_size_mb is None:
            print(f"[AutoConfig] CPU 코어: {cpu_count}개")
            print(f"[AutoConfig] 파일 크기 미확인 - 최대: {max_workers}개 워커")
            return max_workers

        # 파일 크기 기반으로 최적 워커 수 계산
        optimal_workers = max(1, int(file_size_mb / min_size_per_worker))

        # 최대값과 파일 크기 기반 최적값 중 작은 값 선택
        concurrent_fragments = min(max_workers, optimal_workers)
        concurrent_fragments = max(1, concurrent_fragments)

        print(f"[AutoConfig] CPU 코어: {cpu_count}개")
        print(f"[AutoConfig] 파일 크기: {file_size_mb:.1f}MB")
        print(f"[AutoConfig] 워커당 최소 크기: {min_size_per_worker}MB {'(벤치마크)' if benchmark_completed else '(기본값)'}")
        print(f"[AutoConfig] 최대: {max_workers}개 | 파일 기반 최적: {optimal_workers}개")
        print(f"[AutoConfig] 최종 결정: {concurrent_fragments}개 워커 (워커당 ~{file_size_mb/concurrent_fragments:.1f}MB)")

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
