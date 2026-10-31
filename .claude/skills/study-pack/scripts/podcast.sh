#!/bin/zsh
# מעלה מקורות למחברת NotebookLM, מייצר פודקאסט בעברית ומוריד אותו.
# רץ 10–30 דקות: להריץ ברקע.
#
# שימוש:
#   podcast.sh <out.m4a> <default|long> "<הנחיות לפודקאסט>" <מקור> [<מקור> ...]
#
# מקור = נתיב לקובץ (ה־PDF אחרי redact, הסיכום md) שיועלה למחברת,
#        או id:<source_id> של מקור שכבר נמצא במחברת (למשל קובץ שענת העלתה בעצמה).

set -euo pipefail

NB="5c610cfe-ba89-4728-a5a0-34d8176a7179"   # מחברת "מבוא לפסיכולוגיה"
OUT="$1"; LEN="$2"; INSTR="$3"; shift 3

json_field() {  # קורא את ה־JSON מהפלט של notebooklm (מדלג על שורות אזהרה לפניו)
  python3 -I -c 'import json,sys
s = sys.stdin.read(); d = json.loads(s[s.index("{"):])
for k in sys.argv[1].split("."): d = d[k]
print(d)' "$1"
}

retry() {  # שגיאות זמניות של גוגל (502, הגבלת קצב): עד 4 ניסיונות
  local n
  for n in 1 2 3 4; do
    "$@" && return 0
    echo "attempt $n failed, retrying in $((n * 20))s..." >&2
    sleep $((n * 20))
  done
  return 1
}

add_source() {
  notebooklm source add "$1" --notebook "$NB" --json | json_field source.id
}

SRC_ARGS=()
for f in "$@"; do
  if [[ "$f" == id:* ]]; then
    SRC_ARGS+=(-s "${f#id:}")
    continue
  fi
  echo "uploading: $f"
  sid=$(retry add_source "$f")
  notebooklm source wait "$sid" -n "$NB" --timeout 600
  SRC_ARGS+=(-s "$sid")
done

gen_audio() {
  notebooklm generate audio "$INSTR" "${SRC_ARGS[@]}" --notebook "$NB" \
    --format deep-dive --length "$LEN" --language he --json | json_field task_id
}
task=$(retry gen_audio)
echo "generating audio: $task"

notebooklm artifact wait "$task" -n "$NB" --timeout 2700
notebooklm download audio "$OUT" -a "$task" -n "$NB"
afinfo "$OUT" | grep -E "estimated duration" || true

# הפודקאסטים לא נשמרים בגיט: עותק לגוגל דרייב
GDRIVE="$HOME/Library/CloudStorage/GoogleDrive-anat.fradin@gmail.com/My Drive/Open University/מבוא-לפסיכולוגיה/פודקאסטים"
if [[ -d "$GDRIVE" ]]; then
  cp -p "$OUT" "$GDRIVE/" && echo "copied to Google Drive"
fi
echo "DONE: $OUT"
