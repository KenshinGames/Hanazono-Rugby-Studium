#!/bin/sh
# short_final.sh を、終わるまで流し直す(別のセッションに Blender を止められても続きから再開する)。
#   nohup caffeinate -i sh scripts/short_final_loop.sh > render/final_loop.log 2>&1 &
# 流し直す前に、止まった瞬間に書きかけだったかもしれない一番新しいコマを消す。
# リールの Blender(reel.py)が動いている間は、GPU のメモリが足りなくならないよう待つ。
cd "$(dirname "$0")/.."
for i in $(seq 1 20); do
  while pgrep -f "scripts/reel.py" >/dev/null; do sleep 20; done
  last=$(ls -t render/short/s*/f*.jpg render/short_thumb/*.jpg 2>/dev/null | head -1)
  [ -n "$last" ] && rm -f "$last" && echo "[loop] 書きかけかもしれないので消した: $last"
  echo "[loop] $i 回目 $(date '+%H:%M')"
  if sh scripts/short_final.sh >> render/final.log 2>&1; then
    echo "[loop] 終わり $(date '+%H:%M')"
    exit 0
  fi
  echo "[loop] 止まった $(date '+%H:%M')。30 秒後に流し直す"
  sleep 30
done
exit 1
