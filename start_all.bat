@echo off
title Facebook Marketing Tool Runner (Docker)
echo ====================================================
echo DANG KHOI DONG HE THONG FACEBOOK MARKETING TOOL...
echo ====================================================

echo [1/2] Khoi dong Cloudflare Tunnel...
start "Cloudflare Tunnel" /min "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --protocol http2 run --token eyJhIjoiNWU4ZmM4ZGYyZGRlOTQyMjk1ZjM5ZDQ3ZDEyNDdkYTYiLCJ0IjoiZmU2ZWZhYzctYWFlYy00NDQ4LWEyYTEtZjNiMWIyMjNhMjJlIiwicyI6IlpHRTRPRFkxWXpRdE1ESmlZeTAwTkdWbExUZzRNREl0TXpCbE16QTJOemM1T0RBMCJ9

echo [2/2] Khoi dong Frontend va Backend voi Docker Compose...
cd /d "%~dp0"
docker compose up -d

echo ====================================================
echo TAT CA DA DUOC KHOI DONG THANH CONG!
echo - Web Public : https://toolmarketting.online
echo - API Public : https://api.toolmarketting.online
echo ====================================================
pause
