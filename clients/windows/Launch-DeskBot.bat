@echo off
title DeskBot Assistant
set "HTML_PATH=%~dp0DeskBot-Widget.html"

:: باز کردن مستقیم در حالت برنامه دسکتاپ (App Mode) بدون آدرس‌بار و تب‌های مرورگر
start msedge.exe --app="file:///%HTML_PATH:\=/%" --window-size=420,680 --window-position=900,100
exit
