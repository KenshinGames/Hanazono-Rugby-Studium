"""インスタのリール用の縦長の動画(1080×1920、40 秒、24 コマ/秒)のコマを描く。台本は docs/reel/台本.md。

  blender -b build/hanazono.blend -P scripts/reel.py -- [--shots 1,2] [--test] [--samples 48] [--res 1080x1920]

カットごとに out/reel/sNN_<昼夜>/f%04d.jpg に 1 枚ずつ書く。途中で止まっても続きから描ける。
--test を付けると、各カットの最初・真ん中・最後の 3 コマだけを小さく描いて out/reel_test/ に置く(構図の確認用)。
動画にまとめるのは scripts/reel_assemble.py(Blender は要らない)。
"""
import argparse
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from hz import config, sky  # noqa: E402

FPS = 24
# exterior.py の線路の向き(電車を動かすのに使う)
RAIL_DIR = (-0.247, -0.969)


def lerp(a, b, s):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * s for x, y in zip(a, b))
    return a + (b - a) * s


def ease(s):            # ゆっくり始まりゆっくり止まる
    return s * s * (3 - 2 * s)


def ease_out(s):        # 勢いよく始まり、ゆっくり止まる
    return 1 - (1 - s) ** 2


def soft(s):            # ほぼ一定の速さで、端だけ少し丸める
    return 0.6 * s + 0.4 * ease(s)


def add(p, d):
    return tuple(a + b for a, b in zip(p, d))


# ---------------------------------------------------------------- カット
# path(s) は s=0〜1 で (カメラの位置, 見る点, 上の向きの目安) を返す。上の向きを省くと +Z。

def s01(s):   # 昼のスライダー: 七色の外壁を斜めから、ぐっと近くで(つかみ)
    loc = lerp((-138.0, 31.0, 1.3), (-138.0, 21.0, 1.3), s)
    return loc, add(loc, (16.0, -19.0, 7.5))


def s02(s):   # 昼のドローン: 真上から回りながら降りる
    z = lerp(390.0, 200.0, ease_out(s))
    phi = math.radians(lerp(-62.0, 0.0, ease(s)))
    loc = (-14.0, 0.0, z)
    return loc, (-14.0, 0.0, 0.0), (math.cos(phi), math.sin(phi), 0.0)


def s03(s):   # 昼のドローン: 北の町の上を進み、電光掲示板を越えるとグラウンドが開ける
    k = soft(s)
    loc = lerp((240.0, 6.0, 46.0), (78.0, 0.0, 31.0), k)
    return loc, lerp((40.0, 0.0, 12.0), (-45.0, 0.0, -2.0), k)


def s04(s):   # 昼のスライダー: ゴール裏から H のポストの前を横に流す
    loc = lerp((-63.0, 10.0, 1.6), (-63.0, -10.0, 1.6), s)
    return loc, (-20.0, loc[1] * 0.25, 9.0)


def s05(s):   # 昼のクレーン: メインスタンド前列の高さから上がり、HANAZONO の文字が見えてくる
    k = ease(s)
    loc = lerp((-6.0, 46.4, 5.3), (-6.0, 49.5, 17.5), k)   # x=-6 は客席の出入口(u=-15, 5)の間
    return loc, (-6.0, -56.0, lerp(-9.0, -17.0, k))


def s06(s):   # 昼のドリー: 屋根の下を進み、白い鉄骨を見上げる
    loc = lerp((26.0, 56.0, 11.5), (4.0, 56.0, 11.5), ease(s))
    return loc, add(loc, (-44.0, 10.5, 10.5))


def s07(s):   # 昼から夜へ: 南西の空からスタジアム全体。ゆっくり寄る
    loc = lerp((-215.0, 46.0, 118.0), (-198.0, 42.0, 107.0), ease(s))
    return loc, (5.0, 0.0, 0.0)


def s08(s):   # 夜のティルトアップ: 照明塔を見上げ、上で照明が点く
    loc = (-62.0, 36.0, 1.6)
    return loc, lerp((-74.0, 63.0, 7.0), (-79.0, 73.0, 35.0), ease(s))


def s09(s):   # 夜のドローン: 暗い町に光るスタジアムを 5 分の 1 周
    a = math.radians(lerp(95.0, 165.0, soft(s)))
    r = 225.0
    loc = (-14.0 + r * math.cos(a), r * math.sin(a), lerp(100.0, 86.0, s))
    return loc, (-14.0, 0.0, 7.0)


def s10(s):   # 夜のスライダー: 正面広場から七色の外壁を落ち着いて
    loc = lerp((-151.0, 31.0, 1.7), (-151.0, 8.0, 1.7), ease(s))
    return loc, add(loc, (29.0, -10.0, 9.5))


def s11(s):   # 夜のドローン: 外壁の前を上へ抜け、光るグラウンドを見下ろす
    k = ease(s)
    loc = lerp((-131.0, -6.0, 2.0), (-131.0, 2.0, 33.0), k)
    return loc, lerp((-122.0, 6.0, 16.0), (-40.0, 4.0, -6.0), k)


def s12(s):   # 夜のドローン: 上がりながら下がり、町の灯りの中の一点に。電車が横切る
    k = ease(s)
    loc = lerp((-215.0, -10.0, 70.0), (-600.0, -60.0, 280.0), k)
    return loc, lerp((-60.0, 0.0, 0.0), (-20.0, 0.0, 0.0), k)


# id: (昼夜, 秒, レンズ, path, 背景のぼけ(ピントの距離, F 値) か None)
SHOTS = {
    1: ("day", 1.5, 16, s01, None),
    2: ("day", 3.5, 24, s02, None),
    3: ("day", 4.0, 22, s03, None),
    4: ("day", 3.0, 18, s04, (13.5, 2.0)),
    5: ("day", 3.0, 18, s05, None),
    6: ("day", 3.0, 16, s06, None),
    7: ("both", 3.0, 28, s07, None),   # 昼と夜を両方描いて、まとめるときに重ねる
    8: ("lights", 2.0, 24, s08, None),  # 夜。途中まで照明を消しておく
    9: ("night", 5.0, 24, s09, None),
    10: ("night", 4.0, 20, s10, None),
    11: ("night", 3.0, 18, s11, None),
    12: ("night", 5.0, 24, s12, None),
}
# 照明が点く時刻(カット 8 の中の秒)。点いて、一瞬消えて、また点く
LIGHTS_ON = [(0.0, False), (0.95, True), (1.04, False), (1.12, True)]
# カット 12 の電車の進み(線路に沿った m)。最初と最後
TRAIN_RUN = (560.0, 690.0)


def frames_of(sid):
    return int(round(SHOTS[sid][1] * FPS))


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


def set_floodlights(on):
    c = bpy.data.collections.get("night_lights")
    if c:
        c.hide_render = not on
    m = bpy.data.materials.get("lamp_lens")
    if m:
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Strength"].default_value = m["emit_night"] if on else 0.0


def key_camera(scene, cam, sid):
    """カメラ(と電車)に 1 コマごとのキーを打つ。前後 1 コマずつ余分に打って、動きのぶれを正しくする。"""
    _, _, lens, path, dof = SHOTS[sid]
    n = frames_of(sid)
    cam.animation_data_clear()
    cam.rotation_mode = "QUATERNION"
    cam.data.lens = lens
    cam.data.dof.use_dof = dof is not None
    if dof:
        cam.data.dof.focus_distance, cam.data.dof.aperture_fstop = dof
    prev = None
    for f in range(-1, n + 1):
        s = f / (n - 1)
        r = path(s) if 0 <= f < n else _extrap(path, s)
        loc, tgt = r[0], r[1]
        up = r[2] if len(r) > 2 else (0.0, 0.0, 1.0)
        q = cam_matrix(loc, tgt, up)
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
        for f in (-1, n):
            d = lerp(TRAIN_RUN[0], TRAIN_RUN[1], f / (n - 1)) if sid == 12 else 0.0
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
    out = [add(a[0], tuple((x - y) * k for x, y in zip(a[0], b[0]))),
           add(a[1], tuple((x - y) * k for x, y in zip(a[1], b[1])))]
    if len(a) > 2:
        out.append(a[2])
    return out


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
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="1080x1920")
    a = ap.parse_args(argv)
    scene = bpy.context.scene
    res = tuple(int(v) for v in a.res.split("x"))
    if a.test:
        res = (res[0] // 2, res[1] // 2)
    sky.setup_render(scene, samples=a.samples if not a.test else min(a.samples, 24), res=res)
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 95
    scene.render.fps = FPS
    scene.render.use_motion_blur = True
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
    root = os.path.join(config.ROOT, "out", "reel_test" if a.test else "reel")
    t0 = time.time()
    done = 0
    for sid in ids:
        mode = SHOTS[sid][0]
        n = frames_of(sid)
        key_camera(scene, cam, sid)
        passes = ["day", "night"] if mode == "both" else ["night" if mode == "lights" else mode]
        for tm in passes:
            (sky.setup_day if tm == "day" else sky.setup_night)(scene)
            set_floodlights(tm == "night")
            fdir = root if a.test else os.path.join(root, "s%02d_%s" % (sid, tm))
            os.makedirs(fdir, exist_ok=True)
            todo = [0, n // 2, n - 1] if a.test else range(n)
            for f in todo:
                path = (os.path.join(fdir, "s%02d_%s_f%04d.jpg" % (sid, tm, f)) if a.test
                        else os.path.join(fdir, "f%04d.jpg" % f))
                if os.path.exists(path) and not a.test:
                    continue
                if mode == "lights":
                    set_floodlights(lights_on_at(f / FPS))
                scene.frame_set(f)
                scene.render.filepath = path
                bpy.ops.render.render(write_still=True)
                done += 1
                if done % 10 == 0 or a.test:
                    el = time.time() - t0
                    print("[reel] カット %d %s %d / %d コマ(1 コマ %.1f 秒)" % (sid, tm, f + 1, n, el / done), flush=True)
    print("[reel] 終わり %d コマ %.0f 秒" % (done, time.time() - t0))


main()
