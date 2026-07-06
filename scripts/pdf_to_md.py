#!/usr/bin/env python3
"""
PDF -> Markdown conversion script for repository use.
Saves images into a companion folder and writes a Markdown file.
Usage (from repo root):
  python3 scripts/pdf_to_md.py "88Key 全球首个娱乐RWA资本网络 _项目白皮书_ .pdf" "converted/88Key-白皮书.md"

This script uses PyMuPDF (pymupdf). The accompanying GitHub Actions workflow installs the dependency.
"""

import fitz  # PyMuPDF
import sys
import os
import re

def save_page_images(doc, page_index, out_img_dir):
    saved = []
    images = doc.get_page_images(page_index)
    for img in images:
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            # Convert CMYK/alpha images to RGB
            if pix.n >= 5:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img_name = f"page{page_index+1}_img{xref}.png"
            img_path = os.path.join(out_img_dir, img_name)
            pix.save(img_path)
            pix = None
            saved.append(img_name)
        except Exception as e:
            print(f"warning: save image xref={xref} failed: {e}", file=sys.stderr)
    return saved


def span_to_md_text(span):
    t = span.get("text", "")
    t = t.replace("\u00A0", " ")
    t = t.rstrip()
    return t


def convert(pdf_path, md_path):
    doc = fitz.open(pdf_path)
    out_dir = os.path.splitext(md_path)[0] + "_files"
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    md_lines = []
    for pno, page in enumerate(doc):
        saved_imgs = save_page_images(doc, pno, img_dir)

        page_dict = page.get_text("dict")
        blocks = page_dict.get("blocks", [])
        if blocks:
            if pno > 0:
                md_lines.append("---")

            for b in blocks:
                if b.get("type") != 0:
                    continue
                for line in b.get("lines", []):
                    line_texts = []
                    max_size = 0
                    for span in line.get("spans", []):
                        max_size = max(max_size, span.get("size", 0))

                    prefix = ""
                    if max_size >= 20:
                        prefix = "# "
                    elif max_size >= 16:
                        prefix = "## "
                    elif max_size >= 13:
                        prefix = "### "

                    for span in line.get("spans", []):
                        text = span_to_md_text(span)
                        if text:
                            line_texts.append(text)
                    if not line_texts:
                        continue
                    joined = " ".join(line_texts).strip()
                    joined = re.sub(r"\s+", " ", joined)
                    if prefix:
                        md_lines.append(f"{prefix}{joined}")
                    else:
                        md_lines.append(joined)

        if saved_imgs:
            for img in saved_imgs:
                rel = os.path.join(os.path.basename(out_dir), "images", img)
                md_lines.append(f"![{img}]({rel})")

    # Ensure output directory exists
    out_folder = os.path.dirname(md_path)
    if out_folder:
        os.makedirs(out_folder, exist_ok=True)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(md_lines))

    print(f"Converted '{pdf_path}' -> '{md_path}'")
    print(f"Images (if any) saved to '{img_dir}'")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/pdf_to_md.py input.pdf output.md")
        sys.exit(1)
    pdf_path = sys.argv[1]
    md_path = sys.argv[2]
    convert(pdf_path, md_path)
