import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


BACKUP_META_FILE = ".backup_meta.json"

CATEGORIES = {
    "设置": ["configs"],
    "课程表": ["configs/schedules"],
    "插件": ["plugins", "src/plugins"],
    "主题": ["themes", "src/themes"],
    "日志": ["logs"],
}


def collect_items(src_dir, categories=None):
    src = Path(src_dir)
    items = []
    cats = categories if categories else list(CATEGORIES.keys())
    for cat_name in cats:
        for rel in CATEGORIES.get(cat_name, []):
            dp = src / rel
            if dp.is_dir() and not any(Path(rel).is_relative_to(existing) for existing in [i[2] for i in items]):
                items.append(("dir", dp, rel))
    return items


def do_backup(src_dir, dst_dir, categories=None, on_progress=None, on_log=None, on_status=None):
    def _log(msg):
        if on_log:
            on_log(msg)

    def _status(msg):
        if on_status:
            on_status(msg)

    def _progress(val):
        if on_progress:
            on_progress(val)

    try:
        src = Path(src_dir)
        dst = Path(dst_dir)
        if not src.is_dir():
            return False, "源目录不存在"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"cw2_backup_{timestamp}"
        backup_dir = dst / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        items = collect_items(src_dir, categories)
        total = len(items)
        if total == 0:
            return False, "未找到可备份的文件"

        missing = []
        cats = categories if categories else list(CATEGORIES.keys())
        for cat_name in cats:
            for rel in CATEGORIES.get(cat_name, []):
                if not (src / rel).is_dir():
                    missing.append(rel)
        if missing:
            _log(f"以下文件夹不存在，将跳过: {', '.join(missing)}")

        copied = []
        for i, (kind, path, name) in enumerate(items):
            _status(f"正在备份: {name}")
            _log(f"{name}")

            target = backup_dir / name
            try:
                if kind == "dir":
                    shutil.copytree(str(path), str(target))
                copied.append(name)
            except Exception as e:
                shutil.rmtree(str(backup_dir), ignore_errors=True)
                return False, f"{name} 备份失败: {e}"

            _progress(int((i + 1) / total * 100))

        meta = {
            "backup_time": datetime.now().isoformat(),
            "source_dir": str(src),
            "categories": categories or list(CATEGORIES.keys()),
            "items": copied,
        }
        with open(backup_dir / BACKUP_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        zip_path = dst / f"{backup_name}.zip"
        _status("正在压缩...")
        _log(f"{zip_path.name}")

        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(str(backup_dir)):
                for file in files:
                    fp = os.path.join(root, file)
                    zf.write(fp, os.path.relpath(fp, str(backup_dir)))

        shutil.rmtree(str(backup_dir))

        _status(f"备份完成: {zip_path.name}")
        _log(f"共备份 {len(copied)}/{total} 项")
        return True, None
    except Exception as e:
        return False, f"备份过程发生未知错误: {e}"


def list_backups(backup_dir):
    bd = Path(backup_dir)
    if not bd.is_dir():
        return []
    backups = []
    for f in sorted(bd.glob("cw2_backup_*.zip"), reverse=True):
        size = f.stat().st_size
        backups.append({"name": f.name, "path": str(f), "size": size})
    return backups


def format_size(size_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def delete_backup(zip_path):
    p = Path(zip_path)
    if p.is_file():
        p.unlink()
        return True
    return False


def do_restore(zip_path, target_dir, on_progress=None, on_log=None, on_status=None):
    def _log(msg):
        if on_log:
            on_log(msg)

    def _status(msg):
        if on_status:
            on_status(msg)

    def _progress(val):
        if on_progress:
            on_progress(val)

    try:
        if not os.path.isfile(zip_path):
            return False, "备份文件不存在"

        _status("正在解压...")
        _log(f"{os.path.basename(zip_path)}")

        temp_dir = Path(target_dir) / "_restore_temp"
        if temp_dir.exists():
            shutil.rmtree(str(temp_dir))
        temp_dir.mkdir(parents=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(str(temp_dir))

        meta_path = temp_dir / BACKUP_META_FILE
        meta = {}
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

        items = meta.get("items", [])
        total = len(items) if items else 1
        restored = 0
        target = Path(target_dir)

        for item_name in items:
            src_item = temp_dir / item_name
            dst_item = target / item_name
            _status(f"正在恢复: {item_name}")
            _log(f"{item_name}")

            try:
                if src_item.is_dir():
                    if dst_item.exists():
                        shutil.rmtree(str(dst_item))
                    shutil.copytree(str(src_item), str(dst_item),
                                    ignore=shutil.ignore_patterns("Barium.exe"))
                    restored += 1
            except Exception as e:
                shutil.rmtree(str(temp_dir), ignore_errors=True)
                return False, f"{item_name} 恢复失败: {e}"

            _progress(int((restored / total) * 100))

        shutil.rmtree(str(temp_dir))

        _status(f"恢复完成")
        _log("恢复操作已完成")
        return True, None
    except Exception as e:
        return False, f"恢复过程发生未知错误: {e}"
