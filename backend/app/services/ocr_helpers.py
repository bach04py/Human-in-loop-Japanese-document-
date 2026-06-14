import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
import json

from PIL import Image

try:
    from paddleocr import PaddleOCR
except ImportError:  # pragma: no cover
    PaddleOCR = None  # type: ignore

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:  # pragma: no cover
    convert_from_path = None  # type: ignore
    PDF_SUPPORT = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
PDF_EXTS = {".pdf"}


def get_poppler_path() -> str | None:
    if shutil.which("pdftoppm"):
        return None

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            winget_packages_dir = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_packages_dir.exists():
                for p_dir in winget_packages_dir.glob("*Poppler*"):
                    for bd in list(p_dir.glob("**/Library/bin")) + list(p_dir.glob("**/bin")):
                        if (bd / "pdftoppm.exe").exists() or (bd / "pdfinfo.exe").exists():
                            return str(bd)
    return None


def init_ocr() -> "PaddleOCR":
    if PaddleOCR is None:
        raise RuntimeError("PaddleOCR chưa được cài. Chạy: pip install paddleocr paddlepaddle")

    return PaddleOCR(
        use_textline_orientation=True,
        lang="japan",
        enable_mkldnn=False,
    )


def process_and_ocr(ocr: "PaddleOCR", img: Image.Image, include_boxes: bool = True) -> list[dict[str, Any]]:
    orig_w, orig_h = img.size
    max_dim = 1000

    if orig_w > max_dim or orig_h > max_dim:
        img_temp = img.copy()
        img_temp.thumbnail((max_dim, max_dim))
        resized_w, resized_h = img_temp.size
        resized = True
    else:
        img_temp = img
        resized_w, resized_h = orig_w, orig_h
        resized = False

    tmp_path = Path(tempfile.gettempdir()) / f"_tmp_ocr_{uuid.uuid4().hex}.png"
    img_temp.save(str(tmp_path))

    try:
        res = ocr.ocr(
            str(tmp_path),
            use_doc_unwarping=False,
            use_doc_orientation_classify=False,
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    blocks: list[dict[str, Any]] = []
    if not res:
        return blocks

    item = res[0]
    rec_texts = item.get("rec_texts", [])
    rec_scores = item.get("rec_scores", [])
    dt_polys = item.get("dt_polys", [])

    scale_x = orig_w / resized_w if resized else 1.0
    scale_y = orig_h / resized_h if resized else 1.0

    for i, text in enumerate(rec_texts):
        confidence = float(rec_scores[i])
        poly = dt_polys[i]

        xs = [float(pt[0]) * scale_x for pt in poly]
        ys = [float(pt[1]) * scale_y for pt in poly]
        bbox = [min(xs), min(ys), max(xs), max(ys)] if include_boxes else []

        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        orientation = "vertical" if height > width * 1.5 else "horizontal"

        blocks.append(
            {
                "text": text,
                "confidence": round(confidence, 4),
                "bbox": [round(v, 1) for v in bbox] if bbox else [],
                "orientation": orientation,
            }
        )

    return blocks


def run_ocr_on_image(ocr: "PaddleOCR", image_path: Path, include_boxes: bool = True) -> dict[str, Any]:
    start = time.time()

    try:
        img = Image.open(str(image_path))
        blocks = process_and_ocr(ocr, img, include_boxes=include_boxes)
        for block in blocks:
            block["page"] = 1
    except Exception as exc:
        return {
            "document_id": image_path.stem,
            "file": image_path.name,
            "error": str(exc),
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "status": "error",
        }

    elapsed = round(time.time() - start, 2)
    full_text = "\n".join(block["text"] for block in blocks)
    avg_confidence = (
        round(sum(block["confidence"] for block in blocks) / len(blocks), 4)
        if blocks
        else 0.0
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


def run_ocr_on_pdf(ocr: "PaddleOCR", pdf_path: Path, max_pages: int = 3, include_boxes: bool = True) -> dict[str, Any]:
    if not PDF_SUPPORT:
        return {
            "document_id": pdf_path.stem,
            "file": pdf_path.name,
            "error": "pdf2image chưa được cài. Chạy: pip install pdf2image",
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "status": "error",
        }

    poppler_path = get_poppler_path()
    try:
        images = convert_from_path(str(pdf_path), dpi=200, poppler_path=poppler_path)
    except Exception as exc:
        return {
            "document_id": pdf_path.stem,
            "file": pdf_path.name,
            "error": f"Lỗi convert PDF: {exc}",
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "status": "error",
        }

    if len(images) > max_pages:
        images = images[:max_pages]

    all_blocks: list[dict[str, Any]] = []
    start = time.time()

    for page_num, img in enumerate(images, start=1):
        try:
            page_blocks = process_and_ocr(ocr, img, include_boxes=include_boxes)
            for block in page_blocks:
                block["page"] = page_num
            all_blocks.extend(page_blocks)
        except Exception:
            continue

    elapsed = round(time.time() - start, 2)
    full_text = "\n".join(block["text"] for block in all_blocks)
    avg_confidence = (
        round(sum(block["confidence"] for block in all_blocks) / len(all_blocks), 4)
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
        "pages": len(images),
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
