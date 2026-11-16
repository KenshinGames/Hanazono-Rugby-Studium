#!/bin/sh
# 使い方: ./run.sh build | check 角度,角度 [day|night|both] | stills | video | compare | all
set -e
cd "$(dirname "$0")"
BLENDER="${BLENDER:-blender}"
Q() { grep -E "^\[|Error|Traceback|error:|  File " || true; }

case "$1" in
  build)
    "$BLENDER" -b --factory-startup -P scripts/build.py 2>&1 | Q ;;
  check)
    "$BLENDER" -b build/hanazono.blend -P scripts/render.py -- --views "$2" --time "${3:-day}" \
      --res "${RES:-1600x900}" --samples "${SAMPLES:-48}" --out "${OUT:-out/check}" --prefix "${PREFIX:-}" --jpg 2>&1 | Q ;;
  stills)
    "$BLENDER" -b build/hanazono.blend -P scripts/render.py -- --views all5 --time both \
      --res 3840x2160 --samples "${SAMPLES:-256}" --out out/final 2>&1 | Q ;;
  video)
    "$BLENDER" -b build/hanazono.blend -P scripts/orbit.py -- ${ORBIT_ARGS:-} 2>&1 | Q ;;
  compare)
    "$BLENDER" -b build/hanazono.blend -P scripts/compare.py -- 2>&1 | Q ;;
  all)
    "$0" build && "$0" stills && "$0" video && "$0" compare ;;
  *)
    echo "使い方: ./run.sh build | check 角度,角度 [day|night|both] | stills | video | compare | all" ; exit 1 ;;
esac
