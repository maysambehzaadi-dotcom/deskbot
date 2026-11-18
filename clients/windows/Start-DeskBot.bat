@echo off
title DeskBot Windows Actuator
echo Starting DeskBot Agent...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0DeskBot.ps1"
pause
