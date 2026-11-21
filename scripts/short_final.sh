#!/bin/sh
# ショート「目覚め」の本番を通して流す。止まったらもう一度流せば、描いてあるコマは飛ばして続きから描く。
#   caffeinate -i sh scripts/short_final.sh
# 順番: 本編 960 コマ → 本編の動画 → サムネイル 3 案 → 前後の余白 → 本編とショットごとの動画をまとめ直す
# (時間が足りなくなっても、本編とサムネイルが先にできるように)
set -e
cd "$(dirname "$0")/.."
B="blender -b build/hanazono.blend -P scripts/short.py --"
S=${SAMPLES:-32}
mkdir -p render
$B --part core --samples $S > render/final_core.log 2>&1
python3 scripts/short_assemble.py
if [ ! -f render/short_thumb/t3_s09.jpg ]; then
  $B --thumbs > render/final_thumbs.log 2>&1
fi
python3 scripts/short_assemble.py --thumbs
$B --part pad --samples $S > render/final_pad.log 2>&1
python3 scripts/short_assemble.py
echo "[short] 本番 ぜんぶ終わり"
