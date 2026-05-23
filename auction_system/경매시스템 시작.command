#!/bin/bash
cd /Users/parkyongjin/Workspace/auction_system

# 기존 프로세스 종료
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 1

# 브라우저 열기 (3초 후)
sleep 3 && open http://localhost:8501 &

# Streamlit 실행 (포그라운드 - 터미널 유지)
/Library/Frameworks/Python.framework/Versions/3.13/bin/streamlit run app.py --server.port 8501
