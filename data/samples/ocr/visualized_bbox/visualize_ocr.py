#!/usr/bin/env python3
"""Render OCR bounding boxes on source documents and save annotated images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import fitz
import io

from PIL import Image, ImageDraw, ImageFont


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
PDF_EXTS = {".pdf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw OCR bounding boxes on source documents")
    parser.add_argument(
        "--json",
        default="docs/ocr_opt_results_v2.json",
        help="Path to OCR result JSON file.",
    )
    parser.add_argument(
        "--source-dir",
        default="data/samples/ocr",
        help="Directory containing source images/PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/visualized_bbox",
        help="Where annotated files will be saved.",
    )
    return parser.parse_args()


def load_results(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("OCR result JSON must be a list of document results")
    return data


def get_label_font(size: int = 18) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/NotoSansJP-VF.ttf",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/YuGothR.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "arial.ttf",
        "DejaVuSans.ttf",
    ]

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue

    return ImageFont.load_default()


def render_page(image: Image.Image, blocks: list[dict[str, Any]], page_num: int) -> Image.Image:
    drawn = image.copy()
    draw = ImageDraw.Draw(drawn)
    font = get_label_font(18)

    for block in blocks:
        if int(block.get("page", 1)) != page_num:
            continue

        bbox = block.get("bbox") or []
        if len(bbox) != 4:
            continue

        x1, y1, x2, y2 = [float(v) for v in bbox]
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        draw.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=2)
        label = f"{block.get('text', '')[:24]} ({block.get('confidence', 0):.2f})".strip()
        if label:
            draw.text((x1, max(0, y1 - 18)), label, fill=(255, 0, 0), font=font)

    return drawn


import io
import fitz
from PIL import Image


def save_annotated_image(
    image: Image.Image,
    output_path: Path
) -> Path:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    image.save(output_path)

    return output_path


def visualize_document(
    result: dict[str, Any],
    source_dir: Path,
    output_dir: Path
) -> list[Path]:

    file_name = result.get("file") or ""

    if not file_name:
        return []

    source_path = (source_dir / file_name).resolve()

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source file not found: {source_path}"
        )

    saved_paths: list[Path] = []

    if source_path.suffix.lower() in PDF_EXTS:

        doc = fitz.open(str(source_path))

        max_pages = int(
            result.get(
                "pages",
                len(doc)
            )
        )

        max_pages = min(max_pages, len(doc))

        for page_num in range(max_pages):

            page = doc[page_num]

            # render page giống pipeline OCR
            pix = page.get_pixmap(
                matrix=fitz.Matrix(400 / 72, 400 / 72),
                alpha=False
            )

            page_img = Image.open(
                io.BytesIO(
                    pix.tobytes("png")
                )
            ).convert("RGB")

            annotated = render_page(
                page_img,
                result.get("blocks", []),
                page_num + 1
            )

            out_path = (
                output_dir
                /
                f"{result.get('document_id', source_path.stem)}_page_{page_num+1}.png"
            )

            save_annotated_image(
                annotated,
                out_path
            )

            saved_paths.append(out_path)

        doc.close()
    else:

        image = Image.open(
            source_path
        ).convert("RGB")

        annotated = render_page(
            image,
            result.get("blocks", []),
            1
        )

        out_path = (
            output_dir
            /
            f"{result.get('document_id', source_path.stem)}.png"
        )

        save_annotated_image(
            annotated,
            out_path
        )

        saved_paths.append(out_path)

    return saved_paths


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    json_path = (repo_root / args.json).resolve()
    source_dir = (repo_root / args.source_dir).resolve()
    output_dir = (repo_root / args.output_dir).resolve()

    results = load_results(json_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_outputs: list[Path] = []
    for result in results:
        try:
            outputs = visualize_document(result, source_dir, output_dir)
            all_outputs.extend(outputs)
            print(f"[OK] {result.get('file', 'unknown')} -> {len(outputs)} image(s)")
        except Exception as exc:
            print(f"[WARN] {result.get('file', 'unknown')} -> {exc}")

    print(f"\nTotal annotated files: {len(all_outputs)}")
    for path in all_outputs:
        print(f"  - {path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
