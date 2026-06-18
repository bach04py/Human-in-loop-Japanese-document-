import argparse
import io
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from PIL import Image

import cv2
import numpy as np
import fitz

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("[ERROR] PaddleOCR is not installed. Please run the installation cell above.")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
PDF_EXTS = {".pdf"}


def render_pdf_page(page, dpi=300):
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(
        matrix=mat,
        alpha=False
    )

    img = Image.open(io.BytesIO(pix.tobytes("png")))

    return img


def init_ocr() -> PaddleOCR:
    """Init PaddleOCR with Japanese model (v3.x API)."""
    print("[INFO] Loading PaddleOCR Japanese model...")
    ocr = PaddleOCR(
        use_textline_orientation=True,  # detect horizontal / vertical text
        lang="japan",                   # Japanese model
        enable_mkldnn=False,             # Avoid oneDNN NotImplementedError on CPU
        det_db_thresh=0.3,              
        det_db_box_thresh=0.5,
        rec_batch_num=6             
    )
    print("[INFO] Model loaded.\n")
    return ocr

def preprocess_image(img: Image.Image) -> Image.Image:
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # denoise
    gray = cv2.fastNlMeansDenoising(gray)

    # CLAHE tăng contrast
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8,8)
    )
    enhanced = clahe.apply(gray)

    return Image.fromarray(enhanced)

def process_and_ocr(ocr: PaddleOCR, img: Image.Image, include_boxes: bool = True) -> list[dict]:
    """Resizes the PIL Image if it exceeds max size, runs OCR, and scales coordinates back."""
    img = preprocess_image(img)
    orig_w, orig_h = img.size
    max_dim = 2000

    resized = False
    if orig_w > max_dim or orig_h > max_dim:
        img_temp = img.copy()
        img_temp.thumbnail((max_dim, max_dim))
        resized_w, resized_h = img_temp.size
        resized = True
    else:
        img_temp = img
        resized_w, resized_h = orig_w, orig_h

    
    # Save to a temporary file in the current directory
    # In Colab, the current working directory is /content/
    tmp_filename = f"_tmp_ocr_{uuid.uuid4().hex}.png"
    tmp_path = Path(os.getcwd()) / tmp_filename # Use os.getcwd() for Colab compatibility
    img_temp.save(str(tmp_path))

    try:
        res = ocr.ocr(
            str(tmp_path),
            use_doc_unwarping=False,
            use_doc_orientation_classify=False
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    blocks = []
    if res and len(res) > 0:
        item = res[0]
        rec_texts = item.get("rec_texts", [])
        rec_scores = item.get("rec_scores", [])
        dt_polys = item.get("dt_polys", [])

        scale_x = orig_w / resized_w if resized else 1.0
        scale_y = orig_h / resized_h if resized else 1.0

        for i in range(len(rec_texts)):
            text = rec_texts[i]
            confidence = float(rec_scores[i])
            poly = dt_polys[i]

            # Bounding box coordinates in original coordinates
            xs = [float(pt[0]) * scale_x for pt in poly]
            ys = [float(pt[1]) * scale_y for pt in poly]
            bbox = [min(xs), min(ys), max(xs), max(ys)] if include_boxes else []

            # Determine orientation
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            orientation = "vertical" if height > width * 1.5 else "horizontal"

            blocks.append({
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": [round(v, 1) for v in bbox] if bbox else [],
                "orientation": orientation,
            })

    return blocks


def run_ocr_on_image(ocr: PaddleOCR, image_path: Path) -> dict:
    """Run OCR on an image file, returning a dict in OcrResult format."""
    start = time.time()
    try:
        img = Image.open(str(image_path))
        blocks = process_and_ocr(ocr, img, include_boxes=True)
        for b in blocks:
            b["page"] = 1
    except Exception as e:
        print(f"[ERROR] Error processing image {image_path.name}: {e}")
        return {
            "document_id": image_path.stem,
            "file": image_path.name,
            "error": str(e),
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "status": "error",
        }

    elapsed = round(time.time() - start, 2)
    full_text = "\n".join(b["text"] for b in blocks)
    avg_confidence = (
        round(sum(b["confidence"] for b in blocks) / len(blocks), 4)
        if blocks else 0.0
    )

    return {
        "document_id": image_path.stem,
        "file": image_path.name,
        "text": full_text,
        "blocks": blocks,
        "confidence": avg_confidence,
        "status": "ocr_completed",
        "elapsed_seconds": elapsed,
    }


def run_ocr_on_pdf(ocr: PaddleOCR, pdf_path: Path, max_pages: int = 3) -> dict:
    start = time.time()
    all_blocks = []
    try:
        pdf_doc = fitz.open(str(pdf_path))
    except Exception as e:
        return {
            "document_id": pdf_path.stem,
            "file": pdf_path.name,
            "error": f"Cannot open PDF: {e}",
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "status": "error",
        }

    num_pages = min(len(pdf_doc), max_pages)
    print(f"[INFO] Processing {num_pages} pages...")
    for page_num in range(num_pages):
        try:
            page = pdf_doc[page_num]
            # Render PDF page -> image
            img = render_pdf_page(page, dpi=400)

            # OCR
            page_blocks = process_and_ocr(ocr, img, include_boxes=True)

            # Add page info
            for block in page_blocks:
                block["page"] = page_num + 1
                block["type"] = "ocr_scan"

            all_blocks.extend(page_blocks)

        except Exception as e:
            print(f"[ERROR] Page {page_num+1}: {e}")

    pdf_doc.close()

    elapsed = round(time.time() - start, 2)

    full_text = "\n".join(
        block["text"]
        for block in all_blocks)

    avg_confidence = (
        round(
            sum(block["confidence"] for block in all_blocks)
            / len(all_blocks),
            4
        )
        if all_blocks
        else 0.0
    )

    return {
        "document_id": pdf_path.stem,
        "file": pdf_path.name,
        "text": full_text,
        "blocks": all_blocks,
        "confidence": avg_confidence,
        "status": "ocr_completed",
        "elapsed_seconds": elapsed,
        "pages": num_pages,
    }

# def print_result(res: dict) -> None:
#     """In kết quả OCR ra màn hình dễ đọc."""
#     print("=" * 60)
#     print(f"[File]       : {res['file']}")
#     if "error" in res:
#         print(f"[Error]      : {res['error']}")
#         return
#     print(f"[Doc ID]     : {res['document_id']}")
#     print(f"[Confidence] : {res['confidence']}")
#     print(f"[Time]       : {res.get('elapsed_seconds', '?')}s")
#     if "pages" in res:
#         print(f"[Pages]      : {res['pages']}")
#     print(f"[Blocks]     : {len(res['blocks'])}")
#     print("\n--- EXTRACTED TEXT ---")
#     print(res["text"] or "(No text detected)")
#     print("\n--- BLOCKS (first 5) ---")
#     for b in res["blocks"][:5]:
#         print(f"  [{b['orientation']}] {b['text']!r:40s} conf={b['confidence']}")
#     if len(res["blocks"]) > 5:
#         print(f"  ... and {len(res['blocks']) - 5} more blocks")
#     print()


# def save_results(results: list[dict], out_path: Path) -> None:
#     """Lưu toàn bộ kết quả ra file JSON."""
#     out_path.parent.mkdir(parents=True, exist_ok=True)
#     out_path.write_text(
#         json.dumps(results, ensure_ascii=False, indent=2),
#         encoding="utf-8",
#     )
#     print(f"\n[OK] Results saved to: {out_path}")



# def main() -> None:
#     import argparse
#     parser = argparse.ArgumentParser(description="OCR Baseline Test — Week 1")
#     parser.add_argument(
#         "--file",
#         type=str,
#         default=None,
#         help="Chạy OCR trên 1 file cụ thể. Mặc định: chạy tất cả file trong data/samples/ocr/",
#     )
#     parser.add_argument(
#         "--save",
#         action="store_true",
#         help="Lưu kết quả ra docs/ocr_baseline_results.json",
#     )
#     args = parser.parse_args()

#     ocr = init_ocr()
#     results = []

#     if args.file:
#         target = Path(args.file)
#         if not target.exists():
#             print(f"[ERROR] File không tồn tại: {target}")
#             sys.exit(1)
#         files = [target]
#     else:
#         files = sorted(
#             f for f in SAMPLE_DIR.iterdir()
#             if f.suffix.lower() in IMAGE_EXTS | PDF_EXTS
#         )
#         if not files:
#             print(f"[WARN] No image/PDF files found in: {SAMPLE_DIR}")
#             sys.exit(0)

#     print(f"[INFO] Found {len(files)} files to test:\n")
#     for f in files:
#         print(f"  - {f.name}")
#     print()

#     for file_path in files:
#         print(f"[OCR] Processing: {file_path.name}")
#         if file_path.suffix.lower() in PDF_EXTS:
#             res = run_ocr_on_pdf(ocr, file_path)
#         else:
#             res = run_ocr_on_image(ocr, file_path)
#         print_result(res)
#         results.append(res)

#     if args.save:
#         out = Path(__file__).parent.parent / "docs" / "ocr_baseline_results.json"
#         save_results(results, out)


# if __name__ == "__main__":
#     SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples" / "ocr"
#     main()
