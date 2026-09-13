import tkinter as tk
from tkinter import messagebox
import argparse
import gui
import os


APP_VERSION = "1.1.1"
IMG_PATH = "./img"


parser = argparse.ArgumentParser(description="Barium")
parser.add_argument("-path", type=str)
parser.add_argument("-backup_now", action="store_true")
# parser.add_argument("")
args = parser.parse_args()


def find_cw2_path():
    if args.path and os.path.exists(f"{args.path}/Class Widgets 2.exe"):
        return args.path
    if os.path.exists("./Class Widgets 2.exe"):
        return os.path.abspath(".")
    if os.path.exists("../../Class Widgets 2.exe"):
        return os.path.abspath("../..")
    return None


def main():
    cw_path = find_cw2_path()
    if cw_path:
        root = tk.Tk()
        gui.App(root, cw_path)
        root.mainloop()
    else:
        gui.CwNoFound()


if __name__ == "__main__":
    main()
