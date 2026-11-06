"""מפת חשיבה בפורמט XMind: ממתאר markdown (או מקובץ ה־HTML של mindmap.py) לקובץ .xmind.

שימוש:
  python3 -I xmind.py <outline.md | map.html> <out.xmind> "<כותרת הגיליון>"

המתאר: כותרת # אחת לשורש, ## / ### / #### לענפים, ו־"-" (עם הזחה) לתתי־ענפים.
הקובץ כולל content.json (XMind 2020 ואילך) וגם content.xml (XMind 8).
הפריסה: מפה לוגית לשמאל, כך שהשורש מימין והענפים נקראים מימין לשמאל.
"""
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

STRUCTURE = "org.xmind.ui.logic.left"


def read_outline(path):
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".html"):
        # המתאר נמצא בתוך ה־template של markmap, אחרי כותרת ה־YAML
        body = text.split('<script type="text/template">', 1)[1].split("</script>", 1)[0]
        text = body.split("\n---\n", 2)[-1]
    return text


def clean(title):
    title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)
    title = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", title)
    return title.strip()


def new_topic(title):
    return {"id": uuid.uuid4().hex, "title": clean(title), "children": []}


def parse(text):
    root = None
    heads = []  # [(level, topic)]
    bullets = []  # [(indent, topic)]
    for line in text.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, topic = len(m.group(1)), new_topic(m.group(2))
            bullets = []
            if level == 1:
                root, heads = topic, [(1, topic)]
                continue
            while heads and heads[-1][0] >= level:
                heads.pop()
            heads[-1][1]["children"].append(topic)
            heads.append((level, topic))
            continue
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            indent = len(m.group(1).expandtabs(2))
            topic = new_topic(m.group(2))
            while bullets and bullets[-1][0] >= indent:
                bullets.pop()
            parent = bullets[-1][1] if bullets else heads[-1][1]
            parent["children"].append(topic)
            bullets.append((indent, topic))
    if root is None:
        raise SystemExit("אין במתאר כותרת # לשורש")
    return root


def to_json(topic, is_root=False):
    out = {"id": topic["id"], "class": "topic", "title": topic["title"]}
    if is_root:
        out["structureClass"] = STRUCTURE
    if topic["children"]:
        out["children"] = {"attached": [to_json(c) for c in topic["children"]]}
    return out


def to_xml(topic, is_root=False):
    attrs = f' id="{topic["id"]}"' + (f' structure-class="{STRUCTURE}"' if is_root else "")
    kids = ""
    if topic["children"]:
        kids = '<children><topics type="attached">' + "".join(to_xml(c) for c in topic["children"]) + "</topics></children>"
    return f"<topic{attrs}><title>{escape(topic['title'])}</title>{kids}</topic>"


def count(topic):
    return 1 + sum(count(c) for c in topic["children"])


def build(src, out, sheet_title):
    root = parse(read_outline(src))
    sheet_id = uuid.uuid4().hex
    content_json = [{
        "id": sheet_id,
        "class": "sheet",
        "title": sheet_title,
        "rootTopic": to_json(root, is_root=True),
    }]
    content_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:fo="http://www.w3.org/1999/XSL/Format" '
        'xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0">'
        f'<sheet id="{sheet_id}">{to_xml(root, is_root=True)}<title>{escape(sheet_title)}</title></sheet>'
        "</xmap-content>"
    )
    manifest_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0">'
        '<file-entry full-path="content.xml" media-type="text/xml"/>'
        '<file-entry full-path="META-INF/" media-type=""/>'
        '<file-entry full-path="META-INF/manifest.xml" media-type="text/xml"/>'
        "</manifest>"
    )
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("content.json", json.dumps(content_json, ensure_ascii=False))
        z.writestr("metadata.json", json.dumps({"creator": {"name": "study-pack", "version": "1.0"}}))
        z.writestr("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}}))
        z.writestr("content.xml", content_xml)
        z.writestr("META-INF/manifest.xml", manifest_xml)
    print(f"xmind -> {out} ({count(root)} topics)")


if __name__ == "__main__":
    build(*sys.argv[1:4])
