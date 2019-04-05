SET TARGET=work_diary
pyinstaller %TARGET%.py --onefile --windowed --icon=resouce\WorkDiary.ico -p "D:\ProgramData\Python36\Lib\site-packages\PyQt5\Qt\bin"
move dist\%TARGET%.exe WorkDiary.exe
pause