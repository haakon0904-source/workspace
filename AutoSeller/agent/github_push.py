"""
GitHub Push 에이전트
- 로컬 AutoSeller 변경분을 workspace 레포의 autoseller/ 폴더에만 동기화
- 실행: python agent/github_push.py [커밋메시지]
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REMOTE_REPO = "https://github.com/haakon0904-source/workspace.git"
REMOTE_SUBDIR = "autoseller"
LOCAL_ROOT = Path(__file__).parent.parent  # AutoSeller 루트

# 동기화 제외 패턴 (.gitignore 기준 + 추가)
EXCLUDE = {
    "pw", "__pycache__", ".git", ".env",
    "session",        # 세션 기록은 로컬 전용
    "session_notes",  # 세션 기록은 로컬 전용
}
EXCLUDE_SUFFIXES = {".pyc", ".swp"}


def _is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE:
            return True
    return path.suffix in EXCLUDE_SUFFIXES


def _collect_files() -> dict:
    """로컬 파일 수집. {상대경로: 절대경로}"""
    files = {}
    for p in LOCAL_ROOT.rglob("*"):
        if p.is_file():
            rel = p.relative_to(LOCAL_ROOT)
            if not _is_excluded(rel):
                files[rel] = p
    return files


def _run(cmd, cwd=None, check=True):
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"[오류] {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result


def push(commit_msg: str):
    local_files = _collect_files()
    print(f"[push] 로컬 파일 {len(local_files)}개")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # workspace 레포 클론 (shallow)
        print("[push] workspace 레포 클론 중...")
        _run(["git", "clone", "--depth=1", REMOTE_REPO, str(tmp / "workspace")])
        repo = tmp / "workspace"

        target = repo / REMOTE_SUBDIR
        target.mkdir(exist_ok=True)

        # 변경 파일 감지 (신규/수정)
        changed = []
        for rel, src in local_files.items():
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copy2(src, dst)
                changed.append(str(rel))

        # 삭제된 파일 감지 (remote에는 있지만 local에는 없는 것)
        deleted = []
        if target.exists():
            for dst in target.rglob("*"):
                if dst.is_file():
                    rel = dst.relative_to(target)
                    if rel not in local_files and not _is_excluded(rel):
                        dst.unlink()
                        deleted.append(str(rel))

        if not changed and not deleted:
            print("[push] 변경 없음. 종료.")
            return

        print(f"[push] 변경: {len(changed)}개, 삭제: {len(deleted)}개")
        for f in changed:
            print(f"  + {f}")
        for f in deleted:
            print(f"  - {f}")

        # git 설정 및 커밋
        _run(["git", "config", "user.email", "autoseller@push-agent"], cwd=repo)
        _run(["git", "config", "user.name", "AutoSeller Agent"], cwd=repo)
        _run(["git", "add", REMOTE_SUBDIR], cwd=repo)

        status = _run(["git", "diff", "--cached", "--name-only"], cwd=repo, check=False)
        if not status.stdout.strip():
            print("[push] 커밋할 변경 없음.")
            return

        _run(["git", "commit", "-m", commit_msg], cwd=repo)
        print("[push] 푸시 중...")
        _run(["git", "push", "origin", "main"], cwd=repo)
        print("[push] 완료.")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "AutoSeller: update"
    push(msg)
