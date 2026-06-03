import cv2
import numpy as np
import subprocess
import json
import os
from typing import Dict, Any

# Whisper transcription helper (runs the whisper CLI)
def _transcribe_audio(video_path: str) -> Dict[str, Any]:
    # Extract audio to a temporary wav file
    audio_path = video_path + ".wav"
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Run whisper (assumes openai-whisper is installed and accessible)
    # Use short model for speed; you can replace with 'large' for better quality
    result = subprocess.run(["whisper", audio_path, "--model", "small", "--output_format", "json"], capture_output=True, text=True)
    # Clean up temporary audio
    os.remove(audio_path)
    if result.returncode != 0:
        raise RuntimeError(f"Whisper transcription failed: {result.stderr}")
    # Whisper returns a JSON string with segments
    transcription = json.loads(result.stdout)
    # Build a unified dict
    return {
        "transcript": " ".join(seg["text"] for seg in transcription["segments"]),
        "confidence": transcription.get("confidence", 0.0)
    }

def process_video(file_path: str) -> Dict[str, Any]:
    """Extract key frames and audio transcription from a video file.

    Returns a dictionary matching the unified ingestion schema:
        {
            "timestamp": ISO8601 string (file modification time),
            "source": "video",
            "data": {
                "frames": List[bytes] (JPEG encoded frames),
                "transcript": str,
                "confidence": float (0‑1)
            },
            "confidence": float (overall confidence)
        }
    """
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video file {file_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_interval = int(fps * 2)  # sample one frame every 2 seconds
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % frame_interval == 0:
            # Encode frame as JPEG bytes
            success, buffer = cv2.imencode('.jpg', frame)
            if success:
                frames.append(buffer.tobytes())
        idx += 1
    cap.release()
    # Audio transcription
    audio_info = _transcribe_audio(file_path)
    # Use file modification time as timestamp
    timestamp = os.path.getmtime(file_path)
    import datetime
    iso_ts = datetime.datetime.utcfromtimestamp(timestamp).isoformat() + "Z"
    overall_confidence = audio_info.get("confidence", 0.0)
    return {
        "timestamp": iso_ts,
        "source": "video",
        "data": {
            "frames": frames,
            "transcript": audio_info["transcript"],
            "confidence": audio_info["confidence"]
        },
        "confidence": overall_confidence
    }
