import os
from datetime import datetime
from typing import Dict, List


def get_log_files(log_dir: str) -> List[Dict]:
    files = []
    if not os.path.exists(log_dir):
        return files

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if not os.path.isfile(filepath):
            continue

        stat = os.stat(filepath)
        files.append(
            {
                "name": filename,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
        )

    return sorted(files, key=lambda item: item["mtime"], reverse=True)


def read_log_file_chunk(
    log_dir: str,
    filename: str,
    offset: int = 0,
    chunk_size: int = 65536,
) -> bytes:
    root = os.path.abspath(log_dir)
    filepath = os.path.abspath(os.path.join(root, filename))

    if os.path.commonpath([root, filepath]) != root:
        raise ValueError("Invalid file path")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Log file not found: {filename}")

    with open(filepath, "rb") as f:
        f.seek(offset)
        return f.read(chunk_size)
