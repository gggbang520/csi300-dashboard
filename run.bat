@echo off
chcp 65001 >nul
title Streamlit 应用一键启动器
echo ===================================================
echo 正在检查并启动 Streamlit 服务，请勿关闭本窗口...
echo ===================================================

streamlit run app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ---------------------------------------------------
    echo [错误提示] 程序异常退出或未找到 streamlit 命令！
    echo 请确认已在 CMD 中运行: pip install streamlit
    echo ---------------------------------------------------
)

pause