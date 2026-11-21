"""YouTube ショート「目覚め」(縦 1080×1920、24 コマ/秒、40 秒)のコマを描く。ショットの表は docs/short/shotlist.md。

  blender -b build/hanazono.blend -P scripts/short.py -- --board              # 絵コンテ: 各ショットの代表の 1 コマ
  blender -b build/hanazono.blend -P scripts/short.py -- --check              # 全コマでカメラが物の中に入っていないか調べる(描かない)
  blender -b build/hanazono.blend -P scripts/short.py -- --preview            # 動きの確認: 40 秒を小さく・少ないサンプルで
  blender -b build/hanazono.blend -P scripts/short.py -- --probe              # 本番の設定でショットごとに 1 コマ(時間の見積もり)
  blender -b build/hanazono.blend -P scripts/short.py --                      # 本番(render/short/sNN/f%04d.jpg。続きから描ける)
  オプション: --shots 1,2  --samples N  --pad(前後 0.5 秒の余白も描く。本番は既定で描く)

ショットの中の時間 s(0〜1)に、カメラの位置・見る点・レンズ・ピント・時刻・照明を決める。
カメラは制御点を通る曲線(Catmull-Rom)の上を、一定の速さで動く(緩急なし)。前後の余白は同じ速さのまま延ばして描き、
動き出しや止まりは映さない。ショット 10 → 11 → 1 は 1 本の動きで、最後のコマが最初のコマにつながる。
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from hz import config, sky, tod  # noqa: E402

FPS = 24
PAD = 12                 # 前後の余白(コマ)。0.5 秒
BEAT = 0.5               # 切り替えの刻み(テンポ 120 の 1 拍)


# ---------------------------------------------------------------- 緩急

def smooth(s):
    return s * s * (3 - 2 * s)


def lerp(a, b, s):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * s for x, y in zip(a, b))
    return a + (b - a) * s


def ramp(s, a, b):
    """s が a から b へ進むあいだに 0 から 1 へ(なめらかに)。"""
    if s <= a:
        return 0.0
    if s >= b:
        return 1.0
    return smooth((s - a) / (b - a))


# ---------------------------------------------------------------- 曲線

def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


class Path:
    """制御点を通る曲線。at(k) の k は道のりの割合(0〜1)。見る点の曲線は同じ区間の割合で進む。"""

    def __init__(self, locs, tgts, pre=None, post=None, tpre=None, tpost=None):
        """pre / post は最初の点の前・最後の点の後ろにあるとみなす点(隣のショットの点)。つなぎ目の向きがそろう。"""
        self.locs, self.tgts = locs, tgts
        self.ends = {id(locs): (pre, post), id(tgts): (tpre, tpost)}
        n = 400
        self.us = [i / n for i in range(n + 1)]
        pts = [self._ev(locs, u) for u in self.us]
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))

    def _ev(self, pts, u):
        if len(pts) == 1:
            return pts[0]
        m = len(pts) - 1
        x = min(max(u, 0.0), 1.0) * m
        i = min(int(x), m - 1)
        t = x - i
        p = [pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, m)]]
        pre, post = self.ends.get(id(pts), (None, None))
        if i == 0:
            p[0] = pre or tuple(2 * a - b for a, b in zip(pts[0], pts[1]))
        if i + 2 > m:
            p[3] = post or tuple(2 * a - b for a, b in zip(pts[m], pts[m - 1]))
        return _cr(p[0], p[1], p[2], p[3], t)

    def length(self):
        return self.cum[-1]

    def at(self, k):
        L = self.cum[-1]
        if L < 1e-9:
            u = k
        else:
            d = min(max(k, 0.0), 1.0) * L
            j = 1
            while j < len(self.cum) - 1 and self.cum[j] < d:
                j += 1
            a, b = self.cum[j - 1], self.cum[j]
            u = self.us[j - 1] + (self.us[j] - self.us[j - 1]) * ((d - a) / (b - a) if b > a else 0)
        return self._ev(self.locs, u), self._ev(self.tgts, u)


def add(p, d):
    return tuple(a + b for a, b in zip(p, d))


def look_dir(yaw_deg, pitch_deg):
    """シーンの向き(+X から反時計回りの角、上向きの角)の単位ベクトル。"""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    return (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))


def sun_dir_scene(az, el):
    return tuple(sky.sun_vector(az, el))


def sun_az(el, am):
    a = tod.afternoon_azimuth(el)
    return 360.0 - a if am else a


# ---------------------------------------------------------------- ショット
# 各ショットは dict:
#   t0, dur      開始の秒と長さ(0.5 秒刻み)
#   path         Path
#   lens         焦点距離(数か、s の関数)
#   dof          None か (ピントの距離(数か関数), F 値)
#   time         tod の名前、または s の関数で dict を返す
#   up           上の向きの目安の関数(省くと +Z)
#   lights       s → {"nw","ne","sw","se","roof","screen"} の点き具合(省くと時刻なり)
#   beams        光の筋(太陽の方向から)の強さ。0 なし
#   rep          絵コンテに使う s

SUN_RISE_EL = (3.0, 8.5)      # ショット 3 の間に太陽が昇る高さ


def t_dawn(s):
    t = tod.mix("dawn", dict(tod.TIMES["dawn"], el=-1.2, exposure=0.45, bg=0.45), s)
    return t


def t_sunrise(s):
    el = lerp(*SUN_RISE_EL, s)
    return dict(tod.TIMES["sunrise"], el=el)


def t_morning(s):
    return dict(tod.TIMES["morning"], el=12.0)


def t_late_morning(s):
    return dict(tod.TIMES["morning"], el=lerp(26.0, 30.0, s))


def t_day_to_evening(s):
    k = smooth(s)
    t = tod.mix(dict(tod.TIMES["late"], el=48.0), dict(tod.TIMES["golden"], el=9.0), k)
    t["am"] = False
    return t


def t_sunset_to_blue(s):
    k = smooth(s)
    return tod.mix("sunset", "blue", k)


def t_blue(s):
    return dict(tod.TIMES["blue"], el=-4.5, exposure=0.55)


def t_night(s):
    return None


ALL_ON = {"nw": 1, "ne": 1, "sw": 1, "se": 1, "roof": 1, "screen": 1}
ALL_OFF = {"nw": 0, "ne": 0, "sw": 0, "se": 0, "roof": 0, "screen": 0}

# ショット 9 の点灯の順番(ショットの中の秒)。拍(0.5 秒)ごと
LIGHT_ORDER = [("nw", 0.5), ("ne", 1.0), ("sw", 1.5), ("se", 2.0), ("roof", 2.5), ("screen", 3.0)]


def lights_s9(s, dur=4.0):
    sec = s * dur
    out = dict(ALL_OFF)
    for k, t in LIGHT_ORDER:
        # 点いて、一瞬(2 コマ)消えて、また点く
        if sec >= t:
            out[k] = 0 if t + 2 / FPS <= sec < t + 4 / FPS else 1
    return out


# つなぎ目の点。ショット 10 → 11 → 1 は 1 本の動きとしてつながる(11 の最後と 1 の最初は同じ構え、同じ向きと速さ)
P10 = [(-60.0, 120.0, 62.0), (-40.0, 62.0, 36.0), (-28.0, 44.0, 22.0), (-12.0, 18.0, 4.0), (10.0, 4.0, 1.1),
       (36.0, 0.8, 1.4), (50.0, 0.0, 5.5), (58.0, -1.0, 12.0), (64.0, -4.0, 22.0)]
T10 = [(0.0, 20.0, 0.0), (10.0, 0.0, 0.0), (30.0, 0.0, 0.0), (50.0, 0.0, 2.0), (60.0, 0.0, 4.0),
       (72.0, 0.0, 8.0), (90.0, -2.0, 18.0), (96.0, -8.0, 24.0), (96.0, -14.0, 26.0)]
P11 = [P10[-1], (78.0, 20.0, 42.0), (70.0, 62.0, 56.0), (40.0, 95.0, 62.0)]
T11 = [T10[-1], (40.0, -20.0, 10.0), (-10.0, 0.0, 0.0), (-14.0, 10.0, 6.0)]
P1 = [P11[-1], (-10.0, 118.0, 56.0), (-34.0, 72.0, 47.0), (-41.0, 46.0, 33.0), (-48.0, 22.0, 18.0)]
T1 = [T11[-1], (-25.0, 20.0, 4.0), (-50.0, -20.0, 10.0), (-70.0, -50.0, 25.0), (-80.0, -67.0, 34.0)]
LOOP_LENS = 20

# 各ショットは dict(t0, dur, path, lens, dof, time, up, lights, beams, grass, rep)。
# カメラは道のりに対して一定の速さで動く(緩急なし)。前後の余白は同じ速さのまま延ばす。
SHOTS = {
    # 1 夜: 外へ回っていた旋回のまま内へ回り込み、屋根の縁をかすめて照明の光の中へ(見せ場の先出し)
    1: dict(t0=0.0, dur=2.5, prev=11, lens=LOOP_LENS, time=t_night, lights=lambda s: ALL_ON,
            path=Path(P1, T1, pre=P11[-2], tpre=T11[-2]), rep=0.75),
    # 2 夜明け前: グラウンドの上 12 m から望遠で、まだ消えている北東の照明塔の頭を見る。後ろに霞の生駒山と明るくなる空。
    #   塔へ斜めに寄る(塔と山の位置がずれて、動いているのがわかる)。ショット 9 で点く塔の前触れ
    2: dict(t0=2.5, dur=4.5, lens=85, time=t_dawn, lights=lambda s: ALL_OFF,
            path=Path([(34.0, 34.0, 12.0), (39.0, 25.0, 12.4)], [(91.5, -60.0, 35.0), (91.5, -60.0, 35.0)]),
            rep=0.7),
    # 3 日の出: メインスタンドの上の段から東へ寄る。生駒山の稜線から朝日が昇り、光の筋がグラウンドへ
    3: dict(t0=7.0, dur=4.0, lens=28, time=t_sunrise, lights=lambda s: ALL_OFF,
            path=Path([(0.5, 68.2, 17.6), (-0.1, 66.8, 17.3)],
                      [(-45.5, -21.0, 6.0), (-46.1, -22.4, 5.7)]),
            beams=1.0, rep=0.75),
    # 4 朝: 芝の上 30 cm を滑り、トライラインを越えて、ゴールポストの真下から見上げる
    4: dict(t0=11.0, dur=4.0, lens=16, time=t_morning, lights=lambda s: ALL_OFF,
            path=Path([(26.0, 0.9, 0.30), (40.0, 0.6, 0.30), (49.0, 0.3, 0.34), (55.0, 0.1, 0.45)],
                      [(46.0, 0.6, 0.6), (60.0, 0.4, 1.5), (53.0, 0.2, 14.0), (49.0, 0.0, 16.0)]),
            dof=(lambda s: lerp(2.0, 12.0, ramp(s, 0.35, 0.85)), 2.8), grass=True, rep=0.55),
    # 5 朝: バックスタンドの空の座席を横に流し、ピントを手前の座席から奥の屋根へ
    5: dict(t0=15.0, dur=4.0, lens=50, time=t_morning, lights=lambda s: ALL_OFF,
            path=Path([(-12.0, -56.6, 9.3), (-6.0, -56.6, 9.3)], [(0.0, 60.0, 22.0), (6.0, 60.0, 22.0)]),
            dof=(lambda s: lerp(2.2, 118.0, ramp(s, 0.35, 0.75)), 1.8), rep=0.85),
    # 6 朝: 屋根の下から骨組みを見上げ、ゆっくり回る
    6: dict(t0=19.0, dur=4.0, lens=14, time=t_late_morning, lights=lambda s: ALL_OFF,
            path=Path([(4.0, 57.5, 12.6), (0.0, 58.5, 12.6)], [(4.6, 61.0, 40.0), (0.6, 62.0, 40.0)]),
            up=lambda s: look_dir(lerp(-120.0, -60.0, s), 0.0), no_seat_bounce=True, rep=0.5),
    # 7 昼 → 夕方: 真上から降りながら回る。影がグラウンドを横切る
    7: dict(t0=23.0, dur=4.0, lens=50, time=t_day_to_evening, lights=lambda s: ALL_OFF,
            path=Path([(-14.0, 2.0, 430.0), (-14.0, 0.0, 395.0)], [(-14.0, 2.0, 0.0), (-14.0, 0.0, 0.0)]),
            up=lambda s: look_dir(lerp(-8.0, 6.0, s), 0.0), rep=0.6),
    # 8 夕暮れの逆光: バックスタンドの上から西へ寄る。空が赤から群青へ、メインスタンドがシルエットに
    8: dict(t0=27.0, dur=3.0, lens=24, time=t_sunset_to_blue, lights=lambda s: ALL_OFF,
            path=Path([(-6.0, -64.0, 19.5), (-7.0, -61.0, 18.9)], [(-12.0, 60.0, 24.0), (-13.0, 60.0, 22.0)]),
            rep=0.35),
    # 9 日暮れ: グラウンドから北へ寄る。照明塔が拍に合わせて 1 基ずつ点き、最後に映像装置
    9: dict(t0=30.0, dur=4.0, lens=18, time=t_blue, lights=lights_s9,
            path=Path([(-36.0, -6.0, 1.7), (-28.0, -5.0, 2.1)], [(60.0, -4.0, 26.0), (66.0, -3.0, 27.0)]),
            rep=0.9),
    # 10 夜: 屋根の上から急降下し、芝すれすれを抜け、ゴールポストの間をくぐって上昇
    10: dict(t0=34.0, dur=4.0, next=11, lens=16, time=t_night, lights=lambda s: ALL_ON,
             path=Path(P10, T10, post=P11[1], tpost=T11[1]), rep=0.84),
    # 11 夜: 上昇しながら外へ旋回して全景へ引き、ショット 1 の最初の構えにつなぐ
    11: dict(t0=38.0, dur=2.0, prev=10, next=1, lens=LOOP_LENS, time=t_night, lights=lambda s: ALL_ON,
             path=Path(P11, T11, pre=P10[-2], post=P1[1], tpre=T10[-2], tpost=T1[1]), rep=0.6),
}


# サムネイルの 3 案: (番号, ショット, ショットの中のコマ)
THUMBS = [(1, 1, 44), (2, 3, 71), (3, 9, 86)]


def frames_of(sid):
    return int(round(SHOTS[sid]["dur"] * FPS))


def val(v, s):
    return v(s) if callable(v) else v


def pose(sid, f):
    """ショット sid のコマ f の (位置, 見る点, 上, レンズ, s)。
    コマはその時間の真ん中で描く(s = (f + 0.5) / n)。こうすると、同じ点でつながる 2 つのショットの境目で同じ構えが 2 コマ続かない。
    道のりに対して一定の速さ。余白(f < 0 や f >= n)は、つながっている隣のショット(prev / next)があればその動きを、
    なければ端の速さと向きのまま延ばす(動き出しや止まりは作らない)。"""
    sh = SHOTS[sid]
    n = frames_of(sid)
    if f < 0 and sh.get("prev"):
        return pose(sh["prev"], frames_of(sh["prev"]) + f)
    if f >= n and sh.get("next"):
        return pose(sh["next"], f - n)
    s = (f + 0.5) / n
    sc = min(max(s, 0.0), 1.0)
    path = sh["path"]
    if 0.0 <= s <= 1.0:
        loc, tgt = path.at(s)
    else:
        e = 0.01
        a0, b0 = (path.at(0.0), path.at(e)) if s < 0 else (path.at(1.0), path.at(1.0 - e))
        k = (s if s < 0 else s - 1.0) / e * (1 if s < 0 else -1)
        loc = tuple(p + (p - q) * -k for p, q in zip(a0[0], b0[0]))
        tgt = tuple(p + (p - q) * -k for p, q in zip(a0[1], b0[1]))
    up = sh["up"](s) if "up" in sh else (0.0, 0.0, 1.0)
    return loc, tgt, up, val(sh["lens"], sc), sc


def cam_quat(loc, target, up):
    f = (Vector(target) - Vector(loc)).normalized()
    r = f.cross(Vector(up))
    if r.length < 1e-6:
        r = f.cross(Vector((0.0, 1.0, 0.0)))
    r.normalize()
    u = r.cross(f)
    return Matrix((r, u, -f)).transposed().to_quaternion()


# ---------------------------------------------------------------- 照明と画面

def bsdf(nt):
    """材質のプリンシプル BSDF。ノードの名前は Blender の表示言語で変わる(日本語だと「プリンシプルBSDF」)ので、種類で探す。"""
    return next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)


LENS_KEYS = {"nw":"tower_nw", "ne": "tower_ne", "sw": "tower_sw", "se": "tower_se", "roof": "roof_lamps"}


def prepare_lights():
    """塔ごと・屋根の投光器のレンズの材質を分けて、1 基ずつ点けられるようにする。"""
    base = bpy.data.materials.get("lamp_lens")
    for key, obn in LENS_KEYS.items():
        ob = bpy.data.objects.get(obn)
        if ob is None or base is None:
            continue
        m = bpy.data.materials.get("lamp_lens_" + key) or base.copy()
        m.name = "lamp_lens_" + key
        for slot in ob.material_slots:
            if slot.material in (base, m):
                slot.material = m
    for m in bpy.data.materials:
        if m.name.startswith("scr_") and m.use_nodes and "emit_day" in m:
            b = bsdf(m.node_tree)
            if "base0" not in m:
                m["base0"] = tuple(b.inputs["Base Color"].default_value)


def apply_lights(state):
    """state: {"nw","ne","sw","se","roof","screen"} → 0/1。None なら触らない(時刻なり)。"""
    if state is None:
        return
    nl = bpy.data.collections.get("night_lights")
    if nl:
        nl.hide_render = False
        for ob in nl.objects:
            if ob.name.startswith("tower_light_"):
                ob.hide_render = not state.get(ob.name[-2:], 0)
            elif ob.name.startswith("roof_light_"):
                ob.hide_render = not state.get("roof", 0)
    for key in LENS_KEYS:
        m = bpy.data.materials.get("lamp_lens_" + key)
        if m:
            bsdf(m.node_tree).inputs["Emission Strength"].default_value = m["emit_night"] if state.get(key) else 0.0
    on = state.get("screen", 0)
    for m in bpy.data.materials:
        if m.name.startswith("scr_") and "base0" in m:
            b = bsdf(m.node_tree)
            b.inputs["Emission Strength"].default_value = m["emit_night"] if on else 0.0
            b.inputs["Base Color"].default_value = m["base0"] if on else (0.006, 0.006, 0.007, 1.0)


# ---------------------------------------------------------------- 光の筋とにじみ(コンポジター)

def compositor(scene, glow, beams=0.0, sun_xy=(0.5, 0.5)):
    nt = bpy.data.node_groups.get("short_comp")
    if nt is None:
        nt = bpy.data.node_groups.new("short_comp", "CompositorNodeTree")
        nt.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = nt.nodes.new("CompositorNodeRLayers")
        g1 = nt.nodes.new("CompositorNodeGlare"); g1.name = "glow"
        g2 = nt.nodes.new("CompositorNodeGlare"); g2.name = "beams"
        out = nt.nodes.new("NodeGroupOutput")
        g1.inputs["Type"].default_value = "Fog Glow"
        g1.inputs["Quality"].default_value = "High"
        g1.inputs["Threshold"].default_value = 6.0
        g1.inputs["Size"].default_value = 1.0
        g2.inputs["Type"].default_value = "Sun Beams"
        g2.inputs["Quality"].default_value = "High"
        g2.inputs["Threshold"].default_value = 1.2
        g2.inputs["Size"].default_value = 0.9
        nt.links.new(rl.outputs["Image"], g1.inputs["Image"])
        nt.links.new(g1.outputs["Image"], g2.inputs["Image"])
        nt.links.new(g2.outputs["Image"], out.inputs[0])
    nt.nodes["glow"].inputs["Strength"].default_value = 1.0 if glow else 0.0
    nt.nodes["beams"].inputs["Strength"].default_value = beams
    nt.nodes["beams"].inputs["Sun Position"].default_value = sun_xy
    scene.compositing_node_group = nt
    scene.render.use_compositing = True


def sun_screen_xy(scene, cam, sundir):
    from bpy_extras.object_utils import world_to_camera_view
    p = cam.matrix_world.translation + Vector(sundir) * 5000.0
    v = world_to_camera_view(scene, cam, p)
    return (v.x, v.y)


# ---------------------------------------------------------------- 芝の葉(ショット 4 の近くだけ)

def make_grass():
    """カメラの通り道のまわりにだけ、短い芝の葉を立てる。遠くは今までの芝の面のまま。"""
    if bpy.data.objects.get("short_grass"):
        return bpy.data.objects["short_grass"]
    c = bpy.data.collections.get("short_extra") or bpy.data.collections.new("short_extra")
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    # 葉の形: 細い三角を少し曲げる(高さ 4 cm)
    bm = bpy.data.meshes.new("blade")
    w, h = 0.0028, 0.042
    bm.from_pydata([(-w, 0, 0), (w, 0, 0), (w * 0.6, 0.004, h * 0.55), (-w * 0.6, 0.004, h * 0.55), (0, 0.012, h)], [],
                   [(0, 1, 2, 3), (3, 2, 4)])
    blade = bpy.data.objects.new("blade", bm)
    c.objects.link(blade)
    blade.hide_render = True
    mat = bpy.data.materials.new("grass_blade")
    mat.use_nodes = True
    nt = mat.node_tree
    b = bsdf(nt)
    if b is None:   # 新しい材質にノードが入っていないとき
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        o = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(b.outputs[0], o.inputs["Surface"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Specular IOR Level"].default_value = 0.15
    rnd = nt.nodes.new("ShaderNodeObjectInfo")
    ramp_ = nt.nodes.new("ShaderNodeValToRGB")
    ramp_.color_ramp.elements[0].color = (0.026, 0.080, 0.007, 1)
    ramp_.color_ramp.elements[1].color = (0.060, 0.135, 0.014, 1)
    nt.links.new(rnd.outputs["Random"], ramp_.inputs["Fac"])
    nt.links.new(ramp_.outputs["Color"], b.inputs["Base Color"])
    bm.materials.append(mat)
    # 葉を置く帯(カメラの通り道 x 20〜58、幅 5 m)
    pm = bpy.data.meshes.new("grass_strip")
    x0, x1, y0, y1, z = 20.0, 58.0, -2.6, 2.8, 0.0
    pm.from_pydata([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("short_grass", pm)
    c.objects.link(ob)
    mod = ob.modifiers.new("grass", "NODES")
    g = bpy.data.node_groups.new("grass_gn", "GeometryNodeTree")
    g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    g.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = g.nodes, g.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    dist = N.new("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = 6000.0
    inst = N.new("GeometryNodeInstanceOnPoints")
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = blade
    rot = N.new("FunctionNodeRandomValue"); rot.data_type = "FLOAT_VECTOR"
    rot.inputs["Min"].default_value = (-0.35, -0.35, 0.0)
    rot.inputs["Max"].default_value = (0.35, 0.35, 6.283)
    sc = N.new("FunctionNodeRandomValue"); sc.data_type = "FLOAT"
    for inp in sc.inputs:
        if inp.type == "VALUE" and inp.name in ("Min", "Max"):
            inp.default_value = 0.6 if inp.name == "Min" else 1.35
    sc_out = [o for o in sc.outputs if o.type == "VALUE"][0]
    L.new(gi.outputs[0], dist.inputs["Mesh"])
    L.new(dist.outputs["Points"], inst.inputs["Points"])
    L.new(oi.outputs["Geometry"], inst.inputs["Instance"])
    L.new(rot.outputs[0], inst.inputs["Rotation"])
    L.new(sc_out, inst.inputs["Scale"])
    join = N.new("GeometryNodeJoinGeometry")
    L.new(inst.outputs["Instances"], join.inputs[0])
    L.new(join.outputs[0], go.inputs[0])
    mod.node_group = g
    return ob


# ---------------------------------------------------------------- カメラが物の中にないか

DIRS = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
        (0.7, 0.7, 0), (-0.7, 0.7, 0), (0.7, -0.7, 0), (-0.7, -0.7, 0)]


def probe_inside(scene, dg, loc, fwd, near=0.25):
    """近すぎる面と、前を向いた最初の面が裏側(=物の中)かを調べる。問題があれば文字で返す。"""
    o = Vector(loc)
    probs = []
    for d in DIRS + [tuple(fwd)]:
        dv = Vector(d).normalized()
        hit, p, nrm, _, ob, _ = scene.ray_cast(dg, o, dv, distance=1e5)
        if not hit or (ob and ob.name == "short_grass"):
            continue
        dist = (p - o).length
        if dist < near:
            probs.append("近い %.2f m(%s)" % (dist, ob.name if ob else "?"))
        if dv.dot(nrm) > 0.2 and dist < 3.0 and ob and ob.name not in ("mountain",):
            probs.append("裏面(%s、%.1f m 先)" % (ob.name, dist))
    return probs


# ---------------------------------------------------------------- 描く

def setup_shot(scene, cam, sid, pad):
    """カメラ・レンズ・ピントのキーを、余白も含めて 1 コマごとに打つ。"""
    sh = SHOTS[sid]
    n = frames_of(sid)
    cam.animation_data_clear()
    cam.data.animation_data_clear()
    cam.rotation_mode = "QUATERNION"
    cam.data.dof.use_dof = sh.get("dof") is not None
    prev = None
    for f in range(-pad - 1, n + pad + 1):
        loc, tgt, up, lens, s = pose(sid, f)
        q = cam_quat(loc, tgt, up)
        if prev is not None and q.dot(prev) < 0:
            q.negate()
        prev = q
        cam.location = loc
        cam.rotation_quaternion = q
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
        cam.data.lens = lens
        cam.data.keyframe_insert("lens", frame=f)
        if sh.get("dof"):
            fd, fs = sh["dof"]
            cam.data.dof.focus_distance = val(fd, s)
            cam.data.dof.aperture_fstop = fs
            cam.data.dof.keyframe_insert("focus_distance", frame=f)
    for idb in (cam, cam.data):
        if idb.animation_data and idb.animation_data.action:
            _linear(idb.animation_data.action)
    g = bpy.data.objects.get("short_grass")
    if g:
        g.hide_render = not sh.get("grass")
    # 赤い座席の照り返しで白い屋根の裏が赤茶に染まるショットは、座席の照り返しだけを切る(座席そのものは見える)
    for ob in bpy.data.objects:
        if ob.name.startswith(("seat_", "seatpts_")):
            ob.visible_diffuse = not sh.get("no_seat_bounce")
    # 夜は屋根の上の面を暗く(投光器はグラウンドを向いているので、実物の屋根の上は暗い。白く平らに光ると画面の下半分が間延びする)
    m = bpy.data.materials.get("roof_sheet")
    b = bsdf(m.node_tree) if m and m.use_nodes else None
    if b:
        if "base0" not in m:
            m["base0"] = tuple(b.inputs["Base Color"].default_value)
            m["rough0"] = b.inputs["Roughness"].default_value
        night = sh["time"] is t_night
        b.inputs["Base Color"].default_value = tuple(c * (0.28 if night else 1.0) for c in m["base0"][:3]) + (1.0,)
        b.inputs["Roughness"].default_value = 0.8 if night else m["rough0"]


def _linear(action):
    try:
        curves = action.fcurves
    except AttributeError:
        curves = [fc for layer in action.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


_last_time = {"key": None}


def apply_time(scene, cam, sid, s):
    sh = SHOTS[sid]
    t = sh["time"](s)
    key = json.dumps(t, sort_keys=True, default=str)
    if key != _last_time["key"]:
        tod.setup_dict(scene, t)
        _last_time["key"] = key
    apply_lights(sh["lights"](s) if "lights" in sh else None)
    glow = t is None or t.get("lights", 0) > 0 or any((sh["lights"](s) if "lights" in sh else {}).values())
    beams = sh.get("beams", 0.0)
    xy = (0.5, 0.5)
    if beams and t is not None:
        az = t.get("az", sun_az(t["el"], t.get("am", False)))
        xy = sun_screen_xy(scene, cam, sun_dir_scene(az, t["el"]))
    compositor(scene, glow, beams, xy)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="all")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--res", default="1080x1920")
    ap.add_argument("--frames", default="")        # 確かめたいコマだけ(ショットの中の番号)
    ap.add_argument("--out", default="")
    ap.add_argument("--thumbs", action="store_true")   # サムネイル 3 案(THUMBS)を 2160×3840 で
    ap.add_argument("--part", default="all")           # 本番: core(本編だけ)/ pad(前後の余白だけ)/ all
    a = ap.parse_args(argv)
    scene = bpy.context.scene
    res = (2160, 3840) if a.thumbs else tuple(int(v) for v in a.res.split("x"))
    samples = a.samples or (16 if a.preview else 64)
    if a.preview:
        res = (res[0] // 3 // 2 * 2, res[1] // 3 // 2 * 2)
    sky.setup_render(scene, samples=samples, res=res)
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 94
    scene.render.fps = FPS
    scene.render.use_motion_blur = not a.preview
    scene.render.motion_blur_shutter = 0.5
    scene.cycles.seed = 11
    scene.cycles.use_animated_seed = False

    cd = bpy.data.cameras.new("short")
    cd.sensor_width = 36.0
    cd.sensor_fit = "AUTO"
    cd.clip_start = 0.05
    cd.clip_end = 30000.0
    cam = bpy.data.objects.new("cam_short", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    prepare_lights()
    make_grass()

    ids = sorted(SHOTS) if a.shots == "all" else [int(v) for v in a.shots.split(",")]
    if a.check:
        bad = 0
        g = bpy.data.objects.get("short_grass")
        if g:
            g.hide_viewport = True      # 芝の葉はカメラの下 30 cm にあって当然なので数えない
        dg = bpy.context.evaluated_depsgraph_get()
        for sid in ids:
            n = frames_of(sid)
            print("[check] ショット %d: 道のり %.1f m、速さ %.1f m/秒" % (sid, SHOTS[sid]["path"].length(), SHOTS[sid]["path"].length() / SHOTS[sid]["dur"]))
            for f in range(-PAD, n + PAD):
                loc, tgt, up, lens, s = pose(sid, f)
                fwd = (Vector(tgt) - Vector(loc)).normalized()
                p = probe_inside(scene, dg, loc, fwd)
                if p:
                    bad += 1
                    print("[check] ショット %d コマ %d: %s" % (sid, f, " / ".join(p)))
        print("[check] 問題のあるコマ %d" % bad)
        return

    if a.thumbs:
        root = a.out or os.path.join(config.ROOT, "render", "short_thumb")
        os.makedirs(root, exist_ok=True)
        for k, sid, f in THUMBS:
            setup_shot(scene, cam, sid, 0)
            scene.frame_set(f)
            apply_time(scene, cam, sid, pose(sid, f)[4])
            scene.render.filepath = os.path.join(root, "t%d_s%02d.jpg" % (k, sid))
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            print("[short] サムネイル %d(ショット %d コマ %d)%.0f 秒" % (k, sid, f, time.time() - t1), flush=True)
        return

    if a.out:
        root = a.out
    elif a.board:
        root = os.path.join(config.ROOT, "render", "short_board")
    elif a.preview:
        root = os.path.join(config.ROOT, "render", "short_preview")
    elif a.probe:
        root = os.path.join(config.ROOT, "render", "short_probe")
    else:
        root = os.path.join(config.ROOT, "render", "short")
    os.makedirs(root, exist_ok=True)
    t0 = time.time()
    done = 0
    times = {}
    for sid in ids:
        n = frames_of(sid)
        pad = 0 if (a.board or a.probe or a.preview) else PAD
        setup_shot(scene, cam, sid, pad)
        if a.board or a.probe:
            todo = [int(round(SHOTS[sid]["rep"] * (n - 1)))]
        elif a.frames:
            todo = [int(v) for v in a.frames.split(",")]
        elif a.part == "core":
            todo = list(range(n))
        elif a.part == "pad":
            todo = list(range(-pad, 0)) + list(range(n, n + pad))
        else:
            todo = list(range(-pad, n + pad))
        fdir = root if (a.board or a.probe) else os.path.join(root, "s%02d" % sid)
        os.makedirs(fdir, exist_ok=True)
        for f in todo:
            name = ("s%02d.jpg" % sid) if (a.board or a.probe) else ("f%04d.jpg" % (f + PAD))
            path = os.path.join(fdir, name)
            if os.path.exists(path) and not (a.board or a.probe or a.frames):
                continue
            scene.frame_set(f)
            _, _, _, _, s = pose(sid, f)
            apply_time(scene, cam, sid, s)
            scene.render.filepath = path
            t1 = time.time()
            bpy.ops.render.render(write_still=True)
            times.setdefault(sid, []).append(time.time() - t1)
            done += 1
            if done % 12 == 0 or a.board or a.probe:
                print("[short] ショット %d コマ %d / %d(この 1 枚 %.1f 秒)" % (sid, f + 1, n, time.time() - t1), flush=True)
    for sid, ts in times.items():
        print("[short] 時間 ショット %d: 1 コマ %.1f 秒" % (sid, sum(ts) / len(ts)))
    print("[short] 終わり %d コマ %.0f 秒" % (done, time.time() - t0))


if __name__ == "__main__":
    main()
