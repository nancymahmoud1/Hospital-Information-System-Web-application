@echo off
cd /d C:\Users\yassientawfik\Documents\SBME\Semester04\Data_base\Project\Team_13_Hospital_Website
call venv\Scripts\activate
start /b python app.py
timeout /t 5 > nul
start http://127.0.0.1:5000
