"""スタジアムをゆっくり一周する動画を out/hanazono_orbit.mp4 に作る。

  blender -b build/hanazono.blend -P scripts/orbit.py -- [--seconds 30] [--fps 30] [--samples 48] [--time day] [--frames 0,450]
コマは out/orbit_frames/ に 1 枚ずつ書き、途中で止まっても続きから描ける。動画にしたあとコマは消す。
--frames を付けると、その番号のコマだけを描いて終わる(確認用。動画は作らない)。
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from hz import cameras, config, sky  # noqa: E402

CENTRE = (-14.0, 0.0)
TARGET_Z = 7.0
RADIUS = 235.0
HEIGHT = 92.0
START_DEG = 205.0      # 南の正面のやや東から始めて、反時計回りに一周


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--time", default="day")
    ap.add_argument("--frames", default="")
    ap.add_argument("--res", default="1920x1080")
    a = ap.parse_args(argv)
    scene = bpy.context.scene
    res = tuple(int(v) for v in a.res.split("x"))
    sky.setup_render(scene, samples=a.samples, res=res)
    (sky.setup_day if a.time == "day" else sky.setup_night)(scene)
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 96
    scene.cycles.seed = 7
    scene.cycles.use_animated_seed = False
    n = int(round(a.seconds * a.fps))
    fdir = os.path.join(config.ROOT, "out", "orbit_frames_" + a.time)
    os.makedirs(fdir, exist_ok=True)
    cam = cameras.make(scene, "orbit", (0, 0, 100), (0, 0, 0), 30)
    scene.camera = cam
    only = [int(v) for v in a.frames.split(",") if v != ""]
    t0 = time.time()
    done = 0
    for i in (only or range(n)):
        path = os.path.join(fdir, "f%04d.jpg" % i)
        if os.path.exists(path) and not only:
            continue
        ang = math.radians(START_DEG + 360.0 * i / n)
        # 高さと距離を少しだけ波打たせて、単調にしない
        r = RADIUS + 14.0 * math.sin(2 * ang)
        h = HEIGHT + 10.0 * math.cos(ang - math.radians(START_DEG))
        cam.location = (CENTRE[0] + r * math.cos(ang), CENTRE[1] + r * math.sin(ang), h)
        cameras.look_at(cam, (CENTRE[0], CENTRE[1], TARGET_Z))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done += 1
        if done % 20 == 0 or only:
            el = time.time() - t0
            print("[orbit] %d / %d コマ(1 コマ %.1f 秒)" % (i + 1, n, el / done), flush=True)
    if only:
        return
    out = os.path.join(config.ROOT, "out", "hanazono_orbit%s.mp4" % ("" if a.time == "day" else "_" + a.time))
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(fdir, "f%04d.jpg"),
                        "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out])
    if r.returncode == 0 and os.path.exists(out):
        shutil.rmtree(fdir)
        print("[orbit] 保存 %s(コマは消した)" % out)
    else:
        print("[orbit] 動画にできませんでした。コマは %s に残っています" % fdir)


main()
