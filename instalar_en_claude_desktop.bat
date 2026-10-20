@echo off
chcp 65001 >nul
title Instalador 1-Clic: multiCAD-MCP para Claude Desktop y Cursor
cls
echo =====================================================================
echo  INSTALADOR 1-CLIC: multiCAD-MCP para Claude Desktop y Cursor
echo  Conexion de LLMs con AutoCAD, ZWCAD, GstarCAD y BricsCAD
echo  Jose Manuel Caamaño Gonzalez ^| Arquitecto Tecnico ^& BIM Manager
echo =====================================================================
echo.
echo [1/2] Comprobando entorno de Python y configuracion...

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "scripts\instalar_claude_desktop.py"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        python "scripts\instalar_claude_desktop.py"
    ) else (
        echo [ERROR] No se ha encontrado Python en el sistema.
        echo Por favor, instala Python 3.10 o superior para continuar.
        pause
        exit /b 1
    )
)

echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
