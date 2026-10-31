"""מפת חשיבה: ממתאר markdown לקובץ HTML אינטראקטיבי + תמונת PNG.

שימוש (עם הפייתון של notebooklm, שיש בו playwright):
  ~/.local/pipx/venvs/notebooklm-py/bin/python -I mindmap.py <outline.md> <out_base> "<כותרת>"

יוצר <out_base>.html (markmap: אפשר לקפל ענפים ולעשות זום, צריך אינטרנט)
ו־<out_base>.png (תמונה סטטית, נפתחת בכל מקום, גם באייפון).

המתאר: כותרת # אחת לשורש, ## לענפים ראשיים, ### או "-" לתתי־ענפים.
"""
import html
import sys
import time
from pathlib import Path

MARKMAP = "https://cdn.jsdelivr.net/npm/markmap-autoloader@0.18.12"

TEMPLATE = """<!doctype html>
<html lang="he">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  html, body {{ margin: 0; height: 100%; background: #ffffff; }}
  body {{ font-family: -apple-system, "Arial Hebrew", Arial, sans-serif; }}
  .markmap {{ width: 100vw; height: 100vh; }}
  .markmap > svg {{ width: 100%; height: 100%; }}
  .markmap-foreign {{ font-size: 15px; line-height: 1.35; }}
  .markmap-foreign div {{ direction: rtl; text-align: right; }}  /* עברית: כיוון טקסט מימין לשמאל */
</style>
<script>window.markmap = {{ autoLoader: {{ toolbar: true }} }};</script>
<script src="{markmap}"></script>
</head>
<body>
<div class="markmap"><script type="text/template">
---
markmap:
  colorFreezeLevel: 2
  maxWidth: 300
  spacingVertical: 8
  spacingHorizontal: 90
  initialExpandLevel: -1
---
{outline}
</script></div>
</body>
</html>
"""


def build(outline_path, out_base, title):
    outline = Path(outline_path).read_text(encoding="utf-8").strip()
    out_html = Path(f"{out_base}.html")
    out_png = Path(f"{out_base}.png")
    out_html.write_text(
        TEMPLATE.format(title=html.escape(title), markmap=MARKMAP, outline=outline),
        encoding="utf-8",
    )
    print(f"html -> {out_html}")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 2000, "height": 1250}, device_scale_factor=1.5)
        page.goto(out_html.resolve().as_uri())
        page.wait_for_selector(".markmap svg g.markmap-node", timeout=30000)
        time.sleep(2.5)  # אנימציית ההתאמה למסך
        page.screenshot(path=str(out_png), full_page=True)
        browser.close()
    print(f"png  -> {out_png}")


if __name__ == "__main__":
    build(*sys.argv[1:4])
