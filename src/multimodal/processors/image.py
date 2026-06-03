import pytesseract
from PIL import Image
from typing import Dict, Any

_model = None
_processor = None

def _get_clip_model():
    global _model, _processor
    if _model is None:
        from transformers import CLIPProcessor, CLIPModel
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _model, _processor

def process_image(file_path: str) -> Dict[str, Any]:
    """Run OCR via pytesseract and extract visual features via CLIP.
    Returns a dict with extracted text, CLIP similarity vector (placeholder), and a simple signal.
    """
    import torch
    image = Image.open(file_path)
    ocr_text = pytesseract.image_to_string(image)
    model, processor = _get_clip_model()
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        image_features = model.get_image_features(**inputs)
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
