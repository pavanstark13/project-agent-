import os
import mimetypes
from typing import Any, Dict

from .processors.video import process_video
from .processors.image import process_image
from .processors.text import process_text
from .processors.code import process_code

def ingest(file_path: str) -> Dict[str, Any]:
    """Detect file type and delegate to the appropriate processor.

    Returns a dictionary with a unified schema:
        {
            "timestamp": "ISO8601",
            "source": "video|image|text|code",
            "data": <processor specific payload>,
            "confidence": float (0-1)
        }
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")

    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        if mime.startswith("video"):
            return process_video(file_path)
        if mime.startswith("image"):
            return process_image(file_path)
    # fallback based on extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".txt", ".md", ".json"}:
        return process_text(file_path)
    if ext in {".py", ".js", ".cpp", ".java", ".c"}:
        return process_code(file_path)
    raise ValueError(f"Unsupported file type for {file_path}")
