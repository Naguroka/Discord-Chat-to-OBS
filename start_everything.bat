@echo off
cd /d "Location of both backend/frontend files"
start cmd /k python -m http.server 8000
start cmd /k python bot.py
