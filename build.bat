python -m nuitka --standalone --onefile --lto=yes --python-flag=-OO --windows-console-mode="attach" --enable-plugins="tk-inter" --output-filename="Barium" --main="main.py" --include-data-dir="./img=img" --include-data-files="./logo.png=logo.png"

D:\UPX\upx.exe --best --lzma Barium.exe