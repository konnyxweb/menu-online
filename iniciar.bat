@echo off
title MENU ONLINE - Catalogo Digital & Generador PDF
echo =======================================================
echo     MENU ONLINE - Restaurante & Carta Digital
echo =======================================================
echo   Catalogo Publico: http://localhost:5000/
echo   Panel Admin:      http://localhost:5000/admin
echo =======================================================
echo.
if exist "env\Scripts\python.exe" (
    "env\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
