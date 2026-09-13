python -m nuitka --standalone --onefile --lto=yes --python-flag=-OO --windows-console-mode="attach" --enable-plugins="tk-inter" --output-filename="Barium" --main="main.py"

D:\UPX\upx.exe --best --lzma Barium.exe