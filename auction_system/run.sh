#!/bin/bash
echo "🏠 부동산 경매 자동화 대시보드 시작 (포트 8501)"
cd "$(dirname "$0")"
streamlit run app.py --server.port 8501
