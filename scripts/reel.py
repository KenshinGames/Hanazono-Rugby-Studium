"""インスタのリール用の縦長の動画(1080×1920、40 秒、24 コマ/秒)のコマを描く。台本は docs/reel/台本.md(第 3 版)。

  blender -b build/hanazono.blend -P scripts/reel.py -- [--shots 1,2] [--test | --preview] [--samples 48] [--res 1080x1920]

カットごとに out/reel_v3/sNN/f%04d.jpg に 1 枚ずつ書く。途中で止まっても続きから描ける。
--test を付けると、各カットの最初・真ん中・最後の 3 コマだけを小さく描いて out/reel_v3_test/ に置く(構図の確認用)。
--preview を付けると、全部のコマを縦横半分・少ないサンプルで out/reel_v3_preview/ に描く(動きの確認用)。
動画にまとめるのは scripts/reel_assemble.py(Blender は要らない)。

動きはどのカットも一定の速さ(止まった所から動き出さない)。最後のカットだけ、終わりに向けてゆっくり止まる。
時刻は昼下がり → 夕方 → 夕焼け → 日暮れ(照明が点く)→ 夜と、カットごとに進む(scripts/hz/tod.py)。
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from hz import config, sky, tod  # noqa: E402

FPS = 24
PAD = 12                 # カットごとのファイルにするとき、前後に足すコマ(0.5 秒)。インスタで曲に合わせて切れるように
# exterior.py の線路の向き(電車を動かすのに使う)
RAIL_DIR = (-0.247, -0.969)


def lerp(a, b, s):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * s for x, y in zip(a, b))
    return a + (b - a) * s


def add(p, d):
    return tuple(a + b for a, b in zip(p, d))


def stop(s):
    """6 割までは一定の速さ、そこから終わりに向けて速さを 0 まで落とす(最後のカット用)。"""
    if s < 0.6:
        return 1.25 * s
    u = s - 0.6
    return 0.75 + 1.25 * (u - u * u / 0.8)


# ---------------------------------------------------------------- カット
# path(s) は s=0〜1 で (カメラの位置, 見る点) を返す。s に比例して動く(一定の速さ)。

def s01(s):   # 昼下がり: 外壁の前を横へ(つかみ)
    loc = lerp((-151.0, 22.5, 1.7), (-151.0, 18.3, 2.1), s)
    return loc, add(loc, (29.0, -10.0, 9.5))


def s02(s):   # 昼下がり: 南西の空から斜めに見下ろし、右へ回り込む。スタジアム全体と HANAZONO の客席
    a = math.radians(lerp(140.0, 155.0, s))
    r = 175.0
    loc = (-20.0 + r * math.cos(a), r * math.sin(a), 78.0)   # 低めにして、遠くの町の切れ目を見せない
    return loc, (-20.0, -5.0, 0.0)


def s03(s):   # 昼下がり: ゴールポストの手前を低く横へ。奥に電光掲示板
    loc = lerp((35.2, -15.1, 1.4), (37.0, -17.0, 1.4), s)
    return loc, add(loc, (24.0, 17.5, 7.6))


def s04(s):   # 夕方前: バックスタンドの上のほうの席の背もたれの陰から上がり、正面にメインスタンドと屋根が現れる
    loc = lerp((8.0, -62.4, 12.4), (8.0, -62.4, 16.4), s)
    return loc, add(loc, (-6.0, 120.0, -2.0))


def s05(s):   # 夕方前: メインスタンドの上のほうの客席から後ろへ下がり、屋根の鉄骨が上から入って前ボケになる。HANAZONO と生駒山
    loc = lerp((-1.5, 64.5, 17.7), (-1.5, 67.5, 18.8), s)
    return loc, add(loc, (4.0, -358.0, 21.0))


def s06(s):   # 夕焼け: バックスタンドの上から西へ。上がると、メインスタンドの屋根の上に夕日が出る
    loc = lerp((-14.0, -60.0, 24.0), (-17.0, -60.0, 32.0), s)
    return loc, add(loc, (-4.0, 97.6, -4.0))


def s07(s):   # 日暮れ: 照明塔を引きで見上げていくと、すぐに照明が点く(山場)
    loc = lerp((-52.0, 18.0, 1.6), (-53.0, 20.0, 1.6), s)
    return loc, lerp((-73.0, 63.0, 16.0), (-79.0, 73.0, 33.0), s)


def s08(s):   # 夜: 西の空から回り込む。光るスタジアムの奥に、赤い灯の生駒山
    a = math.radians(lerp(95.0, 108.0, s))
    r = 225.0
    loc = (-14.0 + r * math.cos(a), r * math.sin(a), lerp(98.0, 94.0, s))
    return loc, (-14.0, 0.0, 7.0)


def s09(s):   # 夜: 上がりながら下がり、町の灯りの中の一点に。ゆっくり止まる。電車が横切る
    k = stop(s)
    loc = lerp((-260.0, -15.0, 90.0), (-420.0, -35.0, 165.0), k)
    return loc, lerp((-60.0, 0.0, 0.0), (-30.0, 0.0, 0.0), k)


# id: (時刻, 時刻の上書き, 秒, レンズ, path, 背景のぼけ(ピントの距離, F 値) か None)
# 長さは曲(Formula 1 Theme、100 BPM、1 拍 0.6 秒、1 小節 2.4 秒)に合わせる。曲の頭はドラムの入り(16 分の連打)で、
# 小節の頭は 0.525 秒、そこから 1.2 秒(2 拍)ごとに強い拍がある。切り替えはその強い拍の上(4.125 秒から 3.6 秒おき)。
# カット 7 は 22.125 秒の小節の頭から。1 拍は 14.4 コマで割り切れないので、通しのコマ数で丸めた値にしてある
SHOTS = {
    1: ("late", {"el": 42.0}, 99 / FPS, 20, s01, None),
    2: ("late", {"el": 40.0, "haze_scale": 900.0}, 86 / FPS, 20, s02, None),   # 遠くの町を霞ませて、町の切れ目を隠す
    3: ("late", {"el": 37.0}, 87 / FPS, 20, s03, (22.0, 2.8)),
    4: ("late", {"el": 35.0}, 86 / FPS, 24, s04, (110.0, 2.0)),   # 手前の背もたれをぼかす
    5: ("golden", {"el": 33.0}, 87 / FPS, 16, s05, (128.0, 0.35)),   # 手前の屋根の鉄骨を大きくぼかす(F 値は実在しない明るさ)
    6: ("sunset", {}, 86 / FPS, 24, s06, None),
    7: ("blue", {}, 86 / FPS, 24, s07, None),     # 1.2 秒(小節の 3 拍目)で投光器が点く
    8: ("night", {}, 116 / FPS, 24, s08, None),
    9: ("night", {}, 144 / FPS, 24, s09, None),
}
LIGHTS_SHOT = 7
# 照明が点く時刻(カット 7 の中の秒)。点いて、一瞬消えて、また点く
LIGHTS_ON = [(0.0, False), (1.2, True), (1.275, False), (1.35, True)]   # 小節の 3 拍目で点き、16 分音符で瞬く
TRAIN_SHOT = 9
# 電車の進み(線路に沿った m)。最初と最後
TRAIN_RUN = (560.0, 640.0)


def frames_of(sid):
    return int(round(SHOTS[sid][2] * FPS))


def cam_matrix(loc, target, up=(0.0, 0.0, 1.0)):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector(up))
    if r.length < 1e-6:
        r = f.cross(Vector((0.0, 1.0, 0.0)))
    r.normalize()
    u = r.cross(f)
    m = Matrix((r, u, -f)).transposed()
    return m.to_quaternion()


def lights_on_at(sec):
    on = False
    for t, v in LIGHTS_ON:
        if sec >= t:
            on = v
    return on


def key_camera(scene, cam, sid, pad=0):
    """カメラ(と電車)に 1 コマごとのキーを打つ。前後 pad + 1 コマずつ余分に打つ(余白と動きのぶれ用)。"""
    _, _, _, lens, path, dof = SHOTS[sid]
    n = frames_of(sid)
    cam.animation_data_clear()
    cam.rotation_mode = "QUATERNION"
    cam.data.lens = lens
    cam.data.dof.use_dof = dof is not None
    if dof:
        cam.data.dof.focus_distance, cam.data.dof.aperture_fstop = dof
    prev = None
    for f in range(-1 - pad, n + 1 + pad):
        s = f / (n - 1)
        loc, tgt = path(s) if 0 <= f < n else _extrap(path, s)
        q = cam_matrix(loc, tgt)
        if prev is not None and q.dot(prev) < 0:
            q.negate()
        prev = q
        cam.location = loc
        cam.rotation_quaternion = q
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
    train = bpy.data.objects.get("train")
    if train:
        train.animation_data_clear()
        for f in (-1 - pad, n + pad):
            d = lerp(TRAIN_RUN[0], TRAIN_RUN[1], f / (n - 1)) if sid == TRAIN_SHOT else 0.0
            train.location = (RAIL_DIR[0] * d, RAIL_DIR[1] * d, 0.0)
            train.keyframe_insert("location", frame=f)
        if train.animation_data and train.animation_data.action:
            _linear(train.animation_data.action)
    if cam.animation_data and cam.animation_data.action:
        _linear(cam.animation_data.action)


def _extrap(path, s):
    """s が 0〜1 の外(動きのぶれ用の前後 1 コマ)は、端の速さのまま延ばす。"""
    e = 0.02
    if s < 0:
        a, b = path(0.0), path(e)
    else:
        a, b = path(1.0), path(1.0 - e)
    k = abs(s if s < 0 else s - 1.0) / e
    return (add(a[0], tuple((x - y) * k for x, y in zip(a[0], b[0]))),
            add(a[1], tuple((x - y) * k for x, y in zip(a[1], b[1]))))


def _linear(action):
    try:
        curves = action.fcurves
    except AttributeError:   # Blender 5 のレイヤー式のアクション
        curves = [fc for layer in action.layers for strip in layer.strips
                  for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="all")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1080x1920")
    ap.add_argument("--cuts", action="store_true", help="カットごとのファイル用に、前後 0.5 秒ずつ足して out/reel_cuts/ に描く")
    a = ap.parse_args(argv)
    scene = bpy.context.scene
    res = tuple(int(v) for v in a.res.split("x"))
    samples = a.samples
    if a.test or a.preview:
        res = (res[0] // 2, res[1] // 2)
        samples = min(samples, 24 if a.test else 12)
    sky.setup_render(scene, samples=samples, res=res)
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 95
    scene.render.fps = FPS
    scene.render.use_motion_blur = not a.preview
    scene.render.motion_blur_shutter = 0.5      # 180 度のシャッター
    scene.cycles.seed = 7
    scene.cycles.use_animated_seed = False

    cam_data = bpy.data.cameras.new("reel")
    cam_data.sensor_width = 36.0
    cam_data.sensor_fit = "AUTO"
    cam_data.clip_start = 0.1
    cam_data.clip_end = 30000.0
    cam = bpy.data.objects.new("cam_reel", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    ids = sorted(SHOTS) if a.shots == "all" else [int(v) for v in a.shots.split(",")]
    root = os.path.join(config.ROOT, "out", "reel_v3_test" if a.test else "reel_v3_preview" if a.preview
                        else "reel_cuts" if a.cuts else "reel_v3")
    pad = PAD if a.cuts else 0
    t0 = time.time()
    done = 0
    for sid in ids:
        when, over = SHOTS[sid][0], SHOTS[sid][1]
        n = frames_of(sid)
        key_camera(scene, cam, sid, pad)
        tod.setup(scene, when, **over)
        fdir = root if a.test else os.path.join(root, "s%02d" % sid)
        os.makedirs(fdir, exist_ok=True)
        todo = [0, n // 2, n - 1] if a.test else range(-pad, n + pad)
        for f in todo:
            path = (os.path.join(fdir, "s%02d_f%04d.jpg" % (sid, f)) if a.test
                    else os.path.join(fdir, "f%04d.jpg" % (f + pad)))
            if os.path.exists(path) and not a.test:
                continue
            if sid == LIGHTS_SHOT:
                tod.set_floodlights(lights_on_at(f / FPS))
            scene.frame_set(f)
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            done += 1
            if done % 10 == 0 or a.test:
                el = time.time() - t0
                print("[reel] カット %d %d / %d コマ(1 コマ %.1f 秒)" % (sid, f + pad + 1, n + 2 * pad, el / done), flush=True)
    print("[reel] 終わり %d コマ %.0f 秒" % (done, time.time() - t0))


main()
