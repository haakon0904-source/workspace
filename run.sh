#!/bin/bash
echo "📈 주식 투자 분석 대시보드 시작 (포트 8502)"
cd "$(dirname "$0")"
streamlit run app.py --server.port 8502
