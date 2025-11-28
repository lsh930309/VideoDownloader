import sys
import os

# run.py가 있는 위치(프로젝트 루트)를 sys.path에 추가하여 src 패키지를 찾을 수 있게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
