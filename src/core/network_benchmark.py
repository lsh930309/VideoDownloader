"""
네트워크 벤치마크 모듈

실제 YouTube 다운로드로 다양한 워커 설정을 테스트하여 최적값을 찾습니다.
"""
import time
import tempfile
import os
from pathlib import Path
import yt_dlp


class NetworkBenchmark:
    """네트워크 성능 벤치마크"""

    # A/B 테스트용 YouTube 영상
    # A: 1440p60, 10분, 10k 비트레이트, 최대 품질 mp4 약 824MB
    TEST_VIDEO_A_URL = "https://youtu.be/p_lrljKEVQY"

    # B: 1440p60, 80분, 최대 품질 약 6.24GB (824MB까지만 다운로드하여 테스트)
    TEST_VIDEO_B_URL = "https://youtu.be/QNlIlfT3N58"

    # 부분 다운로드 제한 (MB)
    PARTIAL_DOWNLOAD_LIMIT_MB = 824

    # 성능 차이 임계값 (10% 이내면 더 적은 워커 선택)
    PERFORMANCE_THRESHOLD = 0.10

    @staticmethod
    def run_benchmark(progress_callback=None, status_callback=None):
        """
        다양한 워커 수로 벤치마크를 실행하여 최적값 찾기

        Args:
            progress_callback: 진행률 콜백 (0-100)
            status_callback: 상태 메시지 콜백

        Returns:
            dict: {
                'optimal_workers': int,  # 최적 워커 수
                'min_size_per_worker': int,  # 워커당 권장 최소 크기 (MB)
                'results': list  # 각 테스트 결과
            }
        """
        # CPU 코어 수 확인
        cpu_count = os.cpu_count() or 4

        # 1부터 CPU 코어 수까지 2의 제곱수로 테스트 설정 생성
        test_configs = []
        workers = 1
        while workers <= cpu_count:
            test_configs.append({
                'workers': workers,
                'name': f'{workers}개 워커'
            })
            workers *= 2  # 1, 2, 4, 8, 16, ...

        print(f"[Benchmark] CPU 코어 수: {cpu_count}개")
        print(f"[Benchmark] 테스트 워커 설정: {[c['workers'] for c in test_configs]}")

        results_a = []
        results_b = []
        total_tests = len(test_configs) * 2  # A/B 테스트

        print("[Benchmark] A/B 네트워크 벤치마크 시작")
        print(f"[Benchmark] A 영상 (작은 파일): {NetworkBenchmark.TEST_VIDEO_A_URL}")
        print(f"[Benchmark] B 영상 (큰 파일): {NetworkBenchmark.TEST_VIDEO_B_URL}")

        # A 영상 테스트 (작은 파일)
        print("\n[Benchmark] === A 영상 테스트 시작 (작은 파일) ===")
        for idx, config in enumerate(test_configs):
            workers = config['workers']
            test_name = config['name']

            if status_callback:
                status_callback(f"A 영상 테스트 중: {test_name}")

            if progress_callback:
                progress = int((idx / total_tests) * 100)
                progress_callback(progress)

            print(f"\n[Benchmark] A 테스트 {idx + 1}/{len(test_configs)}: {test_name}")

            try:
                result = NetworkBenchmark._run_single_test(
                    workers,
                    NetworkBenchmark.TEST_VIDEO_A_URL,
                    partial_download=False
                )
                results_a.append(result)

                print(f"[Benchmark] {test_name} 완료: {result['speed_mbps']:.1f} Mbps, {result['duration']:.1f}초, {result['file_size_mb']:.1f}MB")

            except Exception as e:
                print(f"[Benchmark] {test_name} 실패: {e}")
                results_a.append({
                    'workers': workers,
                    'success': False,
                    'error': str(e)
                })

        # B 영상 테스트 (큰 파일, 부분 다운로드)
        print("\n[Benchmark] === B 영상 테스트 시작 (큰 파일, 부분 다운로드) ===")
        for idx, config in enumerate(test_configs):
            workers = config['workers']
            test_name = config['name']

            if status_callback:
                status_callback(f"B 영상 테스트 중: {test_name}")

            if progress_callback:
                progress = int(((len(test_configs) + idx) / total_tests) * 100)
                progress_callback(progress)

            print(f"\n[Benchmark] B 테스트 {idx + 1}/{len(test_configs)}: {test_name}")

            try:
                result = NetworkBenchmark._run_single_test(
                    workers,
                    NetworkBenchmark.TEST_VIDEO_B_URL,
                    partial_download=True
                )
                results_b.append(result)

                print(f"[Benchmark] {test_name} 완료: {result['speed_mbps']:.1f} Mbps, {result['duration']:.1f}초, {result['file_size_mb']:.1f}MB (부분)")

            except Exception as e:
                print(f"[Benchmark] {test_name} 실패: {e}")
                results_b.append({
                    'workers': workers,
                    'success': False,
                    'error': str(e)
                })

        if progress_callback:
            progress_callback(100)

        # A/B 결과 분석
        successful_a = [r for r in results_a if r.get('success', False)]
        successful_b = [r for r in results_b if r.get('success', False)]

        if not successful_a and not successful_b:
            raise Exception("모든 벤치마크 테스트가 실패했습니다")

        # A, B 결과 통합 (평균 속도 계산)
        combined_results = {}
        for result_a in successful_a:
            workers = result_a['workers']
            combined_results[workers] = {
                'workers': workers,
                'speed_a': result_a['speed_mbps'],
                'speed_b': 0,
                'avg_speed': result_a['speed_mbps'],
                'count': 1
            }

        for result_b in successful_b:
            workers = result_b['workers']
            if workers in combined_results:
                combined_results[workers]['speed_b'] = result_b['speed_mbps']
                combined_results[workers]['avg_speed'] = (
                    combined_results[workers]['speed_a'] + result_b['speed_mbps']
                ) / 2
                combined_results[workers]['count'] = 2
            else:
                combined_results[workers] = {
                    'workers': workers,
                    'speed_a': 0,
                    'speed_b': result_b['speed_mbps'],
                    'avg_speed': result_b['speed_mbps'],
                    'count': 1
                }

        # 평균 속도로 정렬
        sorted_results = sorted(combined_results.values(), key=lambda x: x['avg_speed'], reverse=True)

        if not sorted_results:
            raise Exception("유효한 벤치마크 결과가 없습니다")

        # 최고 속도 찾기
        best_result = sorted_results[0]
        best_speed = best_result['avg_speed']
        best_workers = best_result['workers']

        # 10% 이내 성능 차이면 더 적은 워커 선택 (자원 절약)
        optimal_workers = best_workers
        for result in sorted_results:
            speed_diff_ratio = (best_speed - result['avg_speed']) / best_speed
            if speed_diff_ratio <= NetworkBenchmark.PERFORMANCE_THRESHOLD:
                # 성능 차이가 10% 이내면 더 적은 워커 수 선택
                if result['workers'] < optimal_workers:
                    optimal_workers = result['workers']
                    print(f"[Benchmark] {result['workers']}개 워커: {result['avg_speed']:.1f} Mbps (차이: {speed_diff_ratio*100:.1f}% - 자원 절약 우선)")

        # 다운로드 속도 기반 최소 chunk size 계산
        # 평균 다운로드 속도에서 I/O 병목 방지를 위한 최소 크기
        # 목표: 각 chunk를 최소 2-3초 이상 다운로드하도록
        avg_download_speed_mbps = best_speed
        avg_download_speed_mb_per_sec = avg_download_speed_mbps / 8

        # 2초 다운로드 기준 최소 chunk size
        min_chunk_duration_sec = 2
        min_size_per_worker = max(
            50,  # 최소 50MB
            int(avg_download_speed_mb_per_sec * min_chunk_duration_sec)
        )

        print(f"\n[Benchmark] === A/B 벤치마크 완료! ===")
        print(f"[Benchmark] 최고 속도: {best_speed:.1f} Mbps ({best_workers}개 워커)")
        print(f"[Benchmark] 최적 워커 수: {optimal_workers}개 (자원 효율 고려)")
        print(f"[Benchmark] 평균 다운로드 속도: {avg_download_speed_mb_per_sec:.1f} MB/s")
        print(f"[Benchmark] 워커당 권장 최소 크기: {min_size_per_worker}MB (I/O 병목 방지)")

        print("\n[Benchmark] A/B 테스트 상세 결과:")
        for result in sorted_results:
            print(f"  {result['workers']}개 워커: A={result['speed_a']:.1f} Mbps, B={result['speed_b']:.1f} Mbps, 평균={result['avg_speed']:.1f} Mbps")

        return {
            'optimal_workers': optimal_workers,
            'min_size_per_worker': min_size_per_worker,
            'best_speed_mbps': best_speed,
            'avg_download_speed_mb_per_sec': avg_download_speed_mb_per_sec,
            'results_a': results_a,
            'results_b': results_b,
            'combined_results': sorted_results
        }

    @staticmethod
    def _run_single_test(workers, video_url, partial_download=False):
        """
        단일 워커 설정으로 테스트 다운로드 수행

        Args:
            workers: 테스트할 워커 수
            video_url: 테스트할 YouTube URL
            partial_download: True면 PARTIAL_DOWNLOAD_LIMIT_MB까지만 다운로드

        Returns:
            dict: 테스트 결과
        """
        # 임시 디렉토리에 다운로드
        temp_dir = tempfile.mkdtemp()

        # 부분 다운로드 제어용 변수
        download_state = {
            'cancelled': False,
            'downloaded_mb': 0,
            'start_time': None
        }

        def progress_hook(d):
            """부분 다운로드 제어용 progress hook"""
            if not partial_download:
                return

            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                downloaded_mb = downloaded / (1024 * 1024)
                download_state['downloaded_mb'] = downloaded_mb

                # 제한 크기 도달 시 다운로드 중단
                if downloaded_mb >= NetworkBenchmark.PARTIAL_DOWNLOAD_LIMIT_MB:
                    download_state['cancelled'] = True
                    raise yt_dlp.utils.DownloadError(f"부분 다운로드 완료: {downloaded_mb:.1f}MB")

        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',  # 최대 품질 다운로드
                'outtmpl': os.path.join(temp_dir, 'benchmark_test.%(ext)s'),
                'merge_output_format': 'mp4',  # mp4로 병합
                'quiet': True,
                'no_warnings': True,
                'concurrent_fragment_downloads': workers,
                'retries': 3,
                'fragment_retries': 3,
                'progress_hooks': [progress_hook],
            }

            start_time = time.time()
            download_state['start_time'] = start_time

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    file_size = info.get('filesize') or info.get('filesize_approx') or 0
                    file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0
            except yt_dlp.utils.DownloadError as e:
                # 부분 다운로드 완료로 인한 에러는 정상 처리
                if download_state['cancelled']:
                    file_size_mb = download_state['downloaded_mb']
                else:
                    raise

            end_time = time.time()
            duration = end_time - start_time

            # 다운로드 속도 계산 (Mbps)
            if duration > 0 and file_size_mb > 0:
                speed_mbps = (file_size_mb * 8) / duration
            else:
                speed_mbps = 0

            return {
                'workers': workers,
                'success': True,
                'duration': duration,
                'file_size_mb': file_size_mb,
                'speed_mbps': speed_mbps,
                'partial': partial_download
            }

        finally:
            # 임시 파일 정리
            try:
                for file in Path(temp_dir).glob('*'):
                    file.unlink()
                Path(temp_dir).rmdir()
            except Exception:
                pass
