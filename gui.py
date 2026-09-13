import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import main

from core import CATEGORIES, do_backup, do_restore, list_backups, delete_backup, format_size


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.argv[0]).parent
    else:
        base = Path(__file__).parent
    return str(base / relative_path)


def CwNoFound():
    root = tk.Tk()
    root.title("Barium")
    root.geometry("300x100")
    root.resizable(False, False)

    ttk.Label(root, text="找不到 Class Widgets 2.exe").pack()

    tk.mainloop()


class ProgressWindow(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.progress_var = tk.IntVar()
        ttk.Progressbar(self, variable=self.progress_var, maximum=100).pack(fill=tk.X, padx=10, pady=(10, 5))
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var).pack(anchor=tk.W, padx=10)

        log_frame = ttk.Frame(self)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log = tk.Text(log_frame, height=5, wrap=tk.WORD)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(fill=tk.BOTH, expand=True)

        self.close_btn = ttk.Button(self, text="完成", command=self.destroy)
        self.close_btn.pack(pady=10)
        self.close_btn.state(["disabled"])

    def append_log(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def finish(self):
        self.progress_var.set(100)
        self.close_btn.state(["!disabled"])

    def start_thread(self, target, args=()):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()


class BackupTab:
    def __init__(self, parent, cw_path):
        self.cw_path = cw_path
        self.frame = ttk.Frame(parent)

        cat_frame = ttk.LabelFrame(self.frame, text="选择备份内容")
        cat_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.cat_vars = {}
        row = ttk.Frame(cat_frame)
        row.pack(fill=tk.X, padx=5, pady=5)
        for i, name in enumerate(CATEGORIES):
            if i > 0 and i % 6 == 0:
                row = ttk.Frame(cat_frame)
                row.pack(fill=tk.X, padx=5)
            var = tk.BooleanVar(value=True)
            self.cat_vars[name] = var
            ttk.Checkbutton(row, text=name, variable=var).pack(side=tk.LEFT, padx=6, pady=2)

        ttk.Button(self.frame, text="开始备份", command=self._start).pack(pady=10)

    def _start(self):
        selected = [n for n, v in self.cat_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("Barium", "请至少选择一项备份内容")
            return

        backup_dir = Path(self.cw_path) / "Backup"
        backup_dir.mkdir(exist_ok=True)

        win = ProgressWindow(self.frame.winfo_toplevel(), "Barium - 正在备份")
        win.start_thread(self._run, (self.cw_path, str(backup_dir), selected, win))

    def _run(self, src, dst, cats, win):
        success, error = do_backup(src, dst, cats, win.progress_var.set, win.append_log, win.status_var.set)
        if success:
            win.append_log("已完成")
        else:
            win.append_log(f"{error}")
        win.finish()


class RestoreTab:
    def __init__(self, parent, cw_path):
        self.cw_path = cw_path
        self.frame = ttk.Frame(parent)

        self.found_icon = tk.PhotoImage(file=resource_path("img/found.png"))

        file_frame = ttk.LabelFrame(self.frame, text="选择备份文件")
        file_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="浏览…", image=self.found_icon, compound="left", command=self._browse_zip).pack(side=tk.RIGHT, padx=5, pady=5)

        ttk.Button(self.frame, text="开始恢复", command=self._start).pack(pady=10)

    def _browse_zip(self):
        init = str(Path(self.cw_path) / "Backup")
        d = filedialog.askopenfilename(
            title="选择备份文件",
            initialdir=init,
            filetypes=[("ZIP", "*.zip")],
        )
        if d:
            self.file_var.set(d)

    def _start(self):
        zf = self.file_var.get().strip()
        if not zf:
            messagebox.showwarning("Barium", "请选择备份文件")
            return
        if not messagebox.askokcancel("Barium", "这会替换掉现有文件，被替换的文件将会被永久删除（真的非常非常久！）\n若要继续，请轻触”确定“按钮"):
            return

        win = ProgressWindow(self.frame.winfo_toplevel(), "正在恢复备份，请坐和放宽。")
        win.start_thread(self._run, (zf, self.cw_path, win))

    def _run(self, zf, target, win):
        success, error = do_restore(zf, target, win.progress_var.set, win.append_log, win.status_var.set)
        if success:
            win.append_log("已完成")
        else:
            win.append_log(f"{error}")
        win.finish()


class ManageTab:
    def __init__(self, parent, cw_path):
        self.cw_path = cw_path
        self.frame = ttk.Frame(parent)

        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        columns = ("name", "size")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="文件名")
        self.tree.heading("size", text="大小")
        self.tree.column("name", width=250)
        self.tree.column("size", width=80)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.delete_icon = tk.PhotoImage(file=resource_path("img/del.png"))
        self.refresh_icon = tk.PhotoImage(file=resource_path("img/refresh.png"))
        self.restore_icon = tk.PhotoImage(file=resource_path("img/restore.png"))

        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="刷新", image=self.refresh_icon, compound="left", command=self.refresh).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="还原", image=self.restore_icon, compound="left", command=self._restore).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="删除", image=self.delete_icon, compound="left", command=self._delete).pack(side=tk.LEFT, padx=4)

        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        backup_dir = Path(self.cw_path) / "Backup"
        for b in list_backups(str(backup_dir)):
            self.tree.insert("", tk.END, values=(b["name"], format_size(b["size"])))

    def _get_selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        backup_dir = Path(self.cw_path) / "Backup"
        return str(backup_dir / values[0])

    def _restore(self):
        path = self._get_selected()
        if not path:
            messagebox.showwarning("Barium", "请先选择一个备份文件")
            return
        if not messagebox.askokcancel("Barium", "这会替换掉现有文件，被替换的文件将会被永久删除（真的非常非常久！）\n若要继续，请轻触“确定”按钮"):
            return

        win = ProgressWindow(self.frame.winfo_toplevel(), "Barium - 正在恢复")
        win.start_thread(self._run_restore, (path, self.cw_path, win))

    def _run_restore(self, zf, target, win):
        success, error = do_restore(zf, target, win.progress_var.set, win.append_log, win.status_var.set)
        if success:
            win.append_log("已完成")
        else:
            win.append_log(f"{error}")
        win.finish()

    def _delete(self):
        path = self._get_selected()
        if not path:
            messagebox.showwarning("Barium", "请先选择一个备份文件")
            return
        name = Path(path).name
        if not messagebox.askokcancel("Barium", f"确定要删除备份文件 {name} 吗？"):
            return
        delete_backup(path)
        self.refresh()


class App:
    def __init__(self, root, cw_path):
        root.title(f"Barium - {main.APP_VERSION}")
        root.geometry("430x340")
        # root.resizable(False, False)

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.backup_tab = BackupTab(notebook, cw_path)
        self.restore_tab = RestoreTab(notebook, cw_path)
        self.manage_tab = ManageTab(notebook, cw_path)

        notebook.add(self.backup_tab.frame, text="备份 CW2")
        notebook.add(self.restore_tab.frame, text="恢复备份")
        notebook.add(self.manage_tab.frame, text="管理备份")
