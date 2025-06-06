import os
from pathlib import Path
from datetime import datetime
import shutil

def get_output_folder(session_id: str, base_dir: str = "outputs") -> Path:
    """
    Construct the full path to the output folder based on current date and session ID.
    Format: outputs/YYYY/MM/DD/<session_id>/
    """
    now = datetime.now()
    folder = Path(base_dir) / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}" / session_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def cleanup_output_folder(folder: Path):
    """Clean up the output folder if it exists"""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
