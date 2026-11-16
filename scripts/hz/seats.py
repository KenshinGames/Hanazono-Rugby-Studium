"""⑤座席: 1 脚の形を点の上に並べる。色ごと・スタンドごとに点の集まりを分ける。"""
import math

import bpy

from . import config, layout, materials as M, roof
from .util import MB, coll

# 文字の線(0〜1 の枠の中。y は下が 0)
STROKES = {
    "H": [((0.12, 0), (0.12, 1)), ((0.88, 0), (0.88, 1)), ((0.12, 0.5), (0.88, 0.5))],
    "A": [((0.08, 0), (0.5, 1)), ((0.5, 1), (0.92, 0)), ((0.25, 0.36), (0.75, 0.36))],
    "N": [((0.12, 0), (0.12, 1)), ((0.12, 1), (0.88, 0)), ((0.88, 0), (0.88, 1))],
    "Z": [((0.1, 0.93), (0.9, 0.93)), ((0.9, 0.93), (0.1, 0.07)), ((0.1, 0.07), (0.9, 0.07))],
    "O": "ring",
}


def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def letter_test():
    """東スタンドの (u, d) が青い文字の中かどうかを返す関数を作る。"""
    L = config.load()["seats"]["letters"]
    st = layout.stand("east")
    rows = [t for t in layout.treads(st) if t["kind"] == "row"]
    dlo = rows[L["row0"]]["d0"]
    dhi = rows[L["row1"]]["d1"]
    H = dhi - dlo
    text = L["text"]
    n = len(text)
    W = (L["u1"] - L["u0"] - L["gap"] * (n - 1)) / n
    sw = L["stroke"]

    def test(u, d):
        if d < dlo or d > dhi:
            return False
        k = int((u - L["u0"]) // (W + L["gap"]))
        if k < 0 or k >= n:
            return False
        x = u - L["u0"] - k * (W + L["gap"])
        if x > W:
            return False
        y = d - dlo
        ch = text[k]
        s = STROKES[ch]
        if s == "ring":
            ex, ey = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
            r = math.hypot(ex, ey)
            ri = math.hypot((x - W / 2) / (W / 2 - sw * 1.15), (y - H / 2) / (H / 2 - sw * 1.0))
            return r <= 1.0 and ri >= 1.0
        for a, b in s:
            if _seg_dist(x, y, (a[0] * W, a[1] * H), (b[0] * W, b[1] * H)) <= sw / 2 * 1.05:
                return 0 <= x <= W
        return False
    return test


def _seat_mesh(name, mat):
    mb = MB()
    dark = M.get("dark_steel")
    # 背もたれ(少し後ろへ倒す)と座面。前(グラウンド側)は -Y
    mb.box(-0.21, 0.21, -0.20, 0.20, 0.38, 0.43, mat)
    b0, b1 = 0.20, 0.25
    t = 0.07
    for (z0, z1, s0, s1) in ((0.40, 0.60, 0.0, t * 0.5), (0.60, 0.80, t * 0.5, t)):
        mb.face(((-0.21, b0 + s0, z0), (0.21, b0 + s0, z0), (0.21, b0 + s1, z1), (-0.21, b0 + s1, z1)), mat)
        mb.face(((0.21, b1 + s0, z0), (-0.21, b1 + s0, z0), (-0.21, b1 + s1, z1), (0.21, b1 + s1, z1)), mat)
        for x, fl in ((-0.21, True), (0.21, False)):
            q = ((x, b0 + s0, z0), (x, b1 + s0, z0), (x, b1 + s1, z1), (x, b0 + s1, z1))
            mb.face(tuple(reversed(q)) if fl else q, mat)
    mb.face(((-0.21, b0 + t, 0.80), (0.21, b0 + t, 0.80), (0.21, b1 + t, 0.80), (-0.21, b1 + t, 0.80)), mat)
    mb.box(-0.035, 0.035, 0.02, 0.22, 0.0, 0.38, dark)
    c = coll("seat_proto")
    ob = mb.build(name, c)
    return ob.data, ob


def seat_points(name):
    """スタンドの席の位置 [(u, d, z)](局所座標)。"""
    cfg = config.load()
    sc = cfg["seats"]
    st = layout.stand(name)
    V = layout.voms(st)
    A = layout.aisles(st)
    a_base, b_base = st["u0"][0], st["u1"][0]
    pts = []
    cols = []
    if name == "west":
        R = cfg["roof"]
        for key in ("main", "north"):
            us = roof.frame_us(R[key])
            for u in us:
                uu = min(max(u, R[key]["u0"] + 0.6), R[key]["u1"] - 0.6)
                cols.append((uu, R["col_front_d"]))
    for t in layout.treads(st):
        if t["kind"] != "row":
            continue
        d = t["d0"] + 0.45
        a, b = layout.u_range(st, d)
        cuts = [(a - 1, a + sc["edge_w"]), (b - sc["edge_w"], b + 1)]
        for u in A[1:-1]:
            cuts.append((u - sc["aisle_w"] / 2, u + sc["aisle_w"] / 2))
        for v in V:
            if v["d0"] - 1e-6 <= t["d0"] < v["d1"] - 1e-6:
                cuts.append((v["u0"] - 0.35, v["u1"] + 0.35))
        for (cu, cd) in cols:
            if abs(cd - d) < 1.5:
                cuts.append((cu - 1.1, cu + 1.1))
        for (x0, x1) in layout.subtract(a, b, cuts):
            n = int((x1 - x0 + 1e-6) // sc["pitch"])
            if n <= 0:
                continue
            off = x0 + ((x1 - x0) - n * sc["pitch"]) / 2 + sc["pitch"] / 2
            for i in range(n):
                pts.append((off + i * sc["pitch"], d, t["z"]))
    return pts


def build():
    c = coll("seats")
    red_me, red_ob = _seat_mesh("seat_red", M.get("seat_red"))
    blue_me, blue_ob = _seat_mesh("seat_blue", M.get("seat_blue"))
    proto = bpy.data.collections["seat_proto"]
    proto.hide_render = True
    proto.hide_viewport = True
    is_blue = letter_test()
    total = 0
    for name in ("west", "east", "north", "south"):
        pts = seat_points(name)
        total += len(pts)
        print("[seats] %-5s %d 席" % (name, len(pts)))
        groups = {"red": [], "blue": []}
        for p in pts:
            groups["blue" if (name == "east" and is_blue(p[0], p[1])) else "red"].append(p)
        for col, plist in groups.items():
            if not plist:
                continue
            me = bpy.data.meshes.new("seatpts_%s_%s" % (name, col))
            me.from_pydata(plist, [], [])
            ob = bpy.data.objects.new(me.name, me)
            ob.matrix_world = layout.xf(name)
            c.objects.link(ob)
            ob.instance_type = "VERTICES"
            child = bpy.data.objects.new("seat_%s_%s" % (name, col), red_me if col == "red" else blue_me)
            c.objects.link(child)
            child.parent = ob
    print("[seats] 合計 %d 席" % total)
