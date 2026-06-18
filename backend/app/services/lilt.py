import logging
from typing import List, Any
import torch
from transformers import LiltForTokenClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class LiltService:
    def __init__(self):
        # Force the device to CPU for stability during testing
        self.device = "cpu"

        # Use a raw string (r"...") so Windows backslashes are read correctly
        model_name = r"C:\Users\fish\PycharmProjects\Japanese-document\backend\app\services\LiLT\local_lilt_model"

        try:
            # Force the library to only look at the local folder
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            self.model = LiltForTokenClassification.from_pretrained(model_name, local_files_only=True).to(self.device)
            self.model.eval()
            logger.info(f"LiLT Service initialized locally on {self.device}.")
        except Exception as e:
            logger.error(f"Failed to load local LiLT model: {e}")

    def _normalize_box(self, box, width=1000, height=1000):
        # PaddleOCR usually gives [x0, y0, x1, y1] in pixels
        # LiLT expects normalized coordinates 0-1000
        return [
            int(box[0] / width * 1000),
            int(box[1] / height * 1000),
            int(box[2] / width * 1000),
            int(box[3] / height * 1000)
        ]

    async def analyze(self, ocr_text: str, blocks: List[Any]) -> str:
        if not blocks:
            return "No structural layout detected."

        # Prepare tokens and normalized boxes
        texts = [b.text for b in blocks]

        # Change 'b.box' to 'b.bbox' to match your OcrBlock schema
        boxes = [self._normalize_box(b.bbox) for b in blocks]

        inputs = self.tokenizer(texts, boxes=boxes, return_tensors="pt", padding=True).to(self.device)


        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = outputs.logits.argmax(dim=-1)

        # Generate structural markers for the LLM
        markers = []
        for i, pred in enumerate(predictions[0]):
            label = self.model.config.id2label[pred.item()]
            # Simple marker format
            markers.append(f"[{label.upper()}: {texts[i]}]")

        return " ".join(markers)