"""build/hanazono.blend を開いて静止画を描く。

  blender -b build/hanazono.blend -P scripts/render.py -- --views top,broadcast --time day --res 1600x900 --samples 64 --out out/check
  --time は day / night / both。--views all5 で仕上げの 5 つ。
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from hz import cameras, config, sky  # noqa: E402

FINAL5 = ["broadcast", "behind_goal", "from_seat", "aerial", "exterior"]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", default="top")
    ap.add_argument("--time", default="day")
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--out", default="out/check")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--jpg", action="store_true")
    a = ap.parse_args(argv)

    scene = bpy.context.scene
    res = tuple(int(v) for v in a.res.split("x"))
    sky.setup_render(scene, samples=a.samples, res=res)
    if a.jpg:
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 92
    views = FINAL5 if a.views == "all5" else a.views.split(",")
    times = ["day", "night"] if a.time == "both" else [a.time]
    out = a.out if os.path.isabs(a.out) else os.path.join(config.ROOT, a.out)
    os.makedirs(out, exist_ok=True)
    ext = "jpg" if a.jpg else "png"
    for tm in times:
        (sky.setup_day if tm == "day" else sky.setup_night)(scene)
        for v in views:
            cam = cameras.make(scene, v)
            scene.camera = cam
            scene.render.filepath = os.path.join(out, "%s%s_%s.%s" % (a.prefix, v, tm, ext))
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print("[render] %s %.1f 秒" % (scene.render.filepath, time.time() - t))


main()
