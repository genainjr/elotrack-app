@echo off
title Elo Track - Inicializando...
cd /d "%~dp0"
python run_gui.py
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao iniciar o Elo Track.
    pause
)
