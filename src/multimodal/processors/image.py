import pytesseract
from PIL import Image
from typing import Dict, Any
import os
from transformers import CLIPProcessor, CLIPModel
import torch

def _load_clip_model():
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return model, processor

_model, _processor = _load_clip_model()

def process_image(file_path: str) -> Dict[str, Any]:
    """Run OCR via pytesseract and extract visual features via CLIP.
    Returns a dict with extracted text, CLIP similarity vector (placeholder), and a simple signal.
    """
    # OCR
    image = Image.open(file_path)
    ocr_text = pytesseract.image_to_string(image)
    # CLIP features (image-text similarity placeholder using empty text)
    inputs = _processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_features = _model.get_image_features(**inputs)
    # Simple signal: length of OCR text and norm of feature vector
    signal = [len(ocr_text), float(image_features.norm())]
    return {
        "timestamp": "2026-06-02T00:00:00Z",
        "source": "image",
        "data": {
            "ocr_text": ocr_text,
            "clip_feature_norm": image_features.norm().item(),
        },
        "signal": signal,
        "confidence": 0.85,
    }
