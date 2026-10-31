"""כלי PDF לחבילת הלמידה.

שימוש:
  python3 -I pdf_tools.py render <in.pdf> <out_dir>        # תמונת PNG לכל עמוד + טקסט לכל עמוד
  python3 -I pdf_tools.py redact <in.pdf> <out.pdf>        # עותק בלי סימן המים האישי (ת"ז, מייל, שם)

דורש PyMuPDF (fitz). אין pdftoppm במחשב.
"""
import re
import sys
from pathlib import Path

import fitz

# סימן המים של האוניברסיטה הפתוחה: "File #... belongs to <name> - do not distribute",
# מספר זהות (9 ספרות), מייל מוסווה ("...atgmail.com"), השם בתחתית העמוד ורצף אותיות מרווח.
WATERMARK_PATTERNS = [
    re.compile(r"File #\d+"),
    re.compile(r"belongs to", re.I),
    re.compile(r"do not distribute", re.I),
    re.compile(r"\b\d{9}\b"),
    re.compile(r"\S+at(gmail|walla|yahoo|hotmail|outlook)\.\S+", re.I),
    re.compile(r"\S+@\S+"),
    re.compile(r"^\s*(Anat|Fradin)\s*$"),
    re.compile(r"^\s*([A-Z] ){4,}[A-Z]\s*$"),
]


def render(pdf, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    for i, page in enumerate(doc, start=1):
        page.get_pixmap(dpi=110).save(out / f"p{i}.png")
        (out / f"p{i}.txt").write_text(page.get_text(), encoding="utf-8")
    print(f"{doc.page_count} pages -> {out}")


def redact(pdf, out_pdf):
    doc = fitz.open(pdf)
    hits = 0
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if any(p.search(span["text"]) for p in WATERMARK_PATTERNS):
                        page.add_redact_annot(fitz.Rect(span["bbox"]), fill=(1, 1, 1))
                        hits += 1
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    doc.save(out_pdf, garbage=4, deflate=True)

    left = []
    for page in fitz.open(out_pdf):
        text = page.get_text()
        left += [p.pattern for p in WATERMARK_PATTERNS[:6] if p.search(text)]
    print(f"redacted {hits} spans -> {out_pdf}")
    if left:
        sys.exit(f"WARNING: watermark still found: {sorted(set(left))}")


if __name__ == "__main__":
    cmd, src, dst = sys.argv[1:4]
    {"render": render, "redact": redact}[cmd](src, dst)
