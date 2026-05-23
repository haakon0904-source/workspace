#!/bin/bash
cd "$(dirname "$0")"

# 이미 실행 중이면 종료
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Streamlit 실행
streamlit run app.py --server.port 8501 &

# 브라우저 열기 (앱 기동 대기)
sleep 3
open http://localhost:8501
