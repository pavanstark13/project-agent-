from typing import Dict, Any
import pathlib

def process_text(file_path: str) -> Dict[str, Any]:
    """Read plain text files and produce a simple signal based on length and word count.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    words = len(text.split())
    signal = [len(text), words]
    return {
        "timestamp": "2026-06-02T00:00:00Z",
        "source": "text",
        "data": {"content": text},
        "signal": signal,
        "confidence": 0.9,
    }
