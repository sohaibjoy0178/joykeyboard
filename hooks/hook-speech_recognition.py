from PyInstaller.utils.hooks import collect_data_files

# This app uses Google/Whisper, never PocketSphinx or non-Windows FLAC binaries.
datas = collect_data_files("speech_recognition", includes=["version.txt", "flac-win32.exe"])
