@echo off
rem Local dev launcher (Windows). Sets the working dir to this script's folder.
cd /d %~dp0
streamlit run app.py