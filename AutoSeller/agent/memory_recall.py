"""
AutoSeller Memory Recall Agent

session/ 디렉토리의 MD 파일을 읽고 컨텍스트를 출력합니다.
사용법: python agent/memory_recall.py [--full]
  --full : all_session 파일까지 읽음 (기본값: summary만 읽음)
"""

import os
import sys
import glob


SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "session")


def find_session_files(full: bool = False) -> list[str]:
    pattern = "all" if full else "summary"
    files = glob.glob(os.path.join(SESSION_DIR, f"auto_seller_{pattern}_session_*.md"))
    files.sort()
    return files


def recall(full: bool = False) -> None:
    files = find_session_files(full)
    if not files:
        print("세션 파일이 없습니다.")
        return

    for f in files:
        print(f"=== {os.path.basename(f)} ===\n")
        with open(f, encoding="utf-8") as fp:
            print(fp.read())
        print()


if __name__ == "__main__":
    full_mode = "--full" in sys.argv
    recall(full=full_mode)
