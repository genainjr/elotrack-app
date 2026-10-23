@echo off
title Elo Track Launcher
if exist "dist\EloTrack\EloTrack.exe" (
    start "" "dist\EloTrack\EloTrack.exe"
) else (
    python run_gui.py
)
exit
