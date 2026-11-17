"""⑦外側と周り: 南のスクラムスクリーン、各スタンドの外壁、広場、周りの地面、木、家並み、遠くの山。"""
import math
import random

from mathutils import Vector

from . import config, layout, materials as M
from .util import MB, coll, text_obj


def build():
    cfg = config.load()
    c = coll("exterior")
    _scrum_facade(cfg, c)
    _scrum_corners(cfg, c)
    _back_walls(cfg, c)
    _ground(cfg, c)
    _trees(cfg, c)
    _town(cfg, c)
    _railway(cfg, c)
    _mountain(cfg, c)


# ---------------------------------------------------------------- スクラムスクリーン

def _lattice(mb, u0, u1, H, P, d, offset, mat, bw, th):
    """斜めの帯の格子。足元 offset + k*P から左右へ、水平に P 進むあいだに H 上がる。"""
    k0 = int(math.floor((u0 - offset) / P)) - 2
    k1 = int(math.ceil((u1 - offset) / P)) + 2
    for k in range(k0, k1 + 1):
        foot = offset + k * P
        for s in (-1, 1):
            # u(t) = foot + s*P*t, z = H*t。u0..u1 に収まる t の範囲で切る
            ta, tb = 0.0, 1.0
            lo, hi = sorted(((u0 - foot) / (s * P), (u1 - foot) / (s * P)))
            ta, tb = max(ta, lo), min(tb, hi)
            if tb - ta < 0.02:
                continue
            mb.bar((foot + s * P * ta, d, H * ta), (foot + s * P * tb, d, H * tb), th, bw, mat)


def _scrum_facade(cfg, c):
    X = cfg["exterior"]
    st = layout.stand("south")
    xf = layout.xf("south")
    D = layout.depth(st) + X["facade_gap"]
    H = X["facade_h"]
    P = X["lattice_period"]
    u0, u1 = st["u0"][0] - 1.5, st["u1"][0] + 1.5
    mb = MB(xf)
    # 下地の面(菱形のタイルはマテリアルで描く)
    mb.face(((u1, D, 0), (u0, D, 0), (u0, D, H), (u1, D, H)), M.get("scrum_tiles"))
    mb.box(u0, u1, D - 0.5, D + 0.25, H, H + 0.35, M.get("white_paint"))
    # 側面は白い壁
    for u in (u0, u1):
        mb.box(u - 0.15, u + 0.15, layout.depth(st) - 12.0, D, 0, H, M.get("concrete"))
    # 濃い帯と明るい帯。半周期ずらして重ねる
    _lattice(mb, u0, u1, H, P, D + 0.22, 0.0, M.get("scrum_dark"), X["band_w"], 0.4)
    _lattice(mb, u0, u1, H, P, D + 0.12, P / 2, M.get("scrum_light"), X["band_w"], 0.3)
    # 足元の三角の開口(入口は暗く、ほかは白壁)
    hq = H / 4
    n = int(round((u1 - u0) / (P / 2)))
    for i in range(-n, n + 1):
        a = i * P / 2
        b = a + P / 2
        if a < u0 or b > u1:
            continue
        m = (M.emissive("entrance_glow", (1.0, 0.86, 0.68, 1), 0.0, 4.0, base=(0.012, 0.012, 0.014, 1))
             if i % 2 == 0 else M.get("white_paint"))
        mb.face(((b - 0.5, D + 0.05, 0), (a + 0.5, D + 0.05, 0), ((a + b) / 2, D + 0.05, hq - 0.5)), m)
    mb.build("scrum_facade", c)
    # 赤い施設名
    p = xf @ Vector((X["name_u"], D + 0.75, X["name_z"]))
    text_obj("name_sign", "HANAZONO RUGBY STADIUM", X["name_h"], M.emissive("name_red", (1.0, 0.05, 0.04, 1), 0.0, 7.0, base=M.srgb(200, 30, 36)), c, p, (-1, 0, 0),
             extrude=0.12, max_width=X["name_w"])
    # 上の小さな照明のポール
    pm = MB(xf)
    for i in range(9):
        u = u0 + 4 + (u1 - u0 - 8) * i / 8
        pm.cyl((u, D - 0.3, H), (u, D - 0.3, H + 3.2), 0.05, M.get("grey_steel"), n=6)
        pm.box(u - 0.25, u + 0.25, D - 0.9, D - 0.3, H + 3.0, H + 3.3, M.get("dark_steel"))
    pm.build("scrum_poles", c)
    _night_exterior(cfg, xf, D, H, u0, u1)


def _scrum_corners(cfg, c):
    X = cfg["exterior"]
    k = cfg["stands"]["corners"]
    H = X["corner_h"]
    r = X["corner_r"]
    n = X["corner_periods"]
    dark, light = M.get("scrum_dark"), M.get("scrum_light")
    white = M.get("white_paint")
    r_ter = k["r_inner"] + k["steps"] * k["tread"] + k["back_flat"]
    z_ter = k["base_h"] + k["steps"] * k["riser"]
    for sy, tag in ((1, "sw"), (-1, "se")):
        mb = MB()
        cx, cy = k["cx"], sy * k["cy"]
        a0, a1 = (90.0, 180.0) if sy > 0 else (-90.0, -180.0)

        def P(rr, t, z):
            a = math.radians(a0 + (a1 - a0) * t)
            return (cx + rr * math.cos(a), cy + rr * math.sin(a), z)

        # 斜めの柱。濃い色と白を半周期ずらす
        for j in range(2 * n + 1):
            t0 = j / (2 * n)
            for s in (-1, 1):
                t1 = t0 + s / n
                ta, tb = 0.0, 1.0
                if t1 < 0:
                    tb = t0 / (t0 - t1)
                if t1 > 1:
                    tb = (1 - t0) / (t1 - t0)
                if tb < 0.05:
                    continue
                mat = dark if j % 2 == 0 else light
                rr = r + (0.25 if j % 2 == 0 else 0.0)
                # 弧に沿わせるため 6 つに折る
                m = 6
                for q in range(m):
                    qa, qb = tb * q / m, tb * (q + 1) / m
                    mb.bar(P(rr, t0 + (t1 - t0) * qa, H * qa), P(rr, t0 + (t1 - t0) * qb, H * qb), 0.55, X["band_w"], mat)
        # 上の輪、段の後ろとつなぐ白い床の輪(コンコースの屋根)
        seg = 36
        for i in range(seg):
            t0, t1 = i / seg, (i + 1) / seg
            mb.bar(P(r, t0, H), P(r, t1, H), 0.7, 0.5, white)
            for (za, zb_) in ((z_ter + 2.4, z_ter + 3.0),):
                a, b, cc, dd = P(r_ter - 0.2, t0, zb_), P(r + 0.4, t0, zb_), P(r + 0.4, t1, zb_), P(r_ter - 0.2, t1, zb_)
                e, f, g, h = P(r_ter - 0.2, t0, za), P(r + 0.4, t0, za), P(r + 0.4, t1, za), P(r_ter - 0.2, t1, za)
                quads = [(a, b, cc, dd), (h, g, f, e), (f, g, cc, b), (e, a, dd, h)]
                for qd in quads:
                    mb.face(qd if sy > 0 else tuple(reversed(qd)), white)
        mb.build("scrum_corner_" + tag, c)


# ---------------------------------------------------------------- 外壁

def _back_walls(cfg, c):
    conc = M.get("concrete")
    light = M.get("concrete_light")
    glass = M.get("glass_dark")
    # 東・北: 後ろの壁に柱型と、足元の暗い開口
    for name, bay in (("east", 9.786), ("north", 8.0)):
        st = layout.stand(name)
        mb = MB(layout.xf(name))
        D = layout.depth(st)
        H = layout.top_z(st) + st.get("back_parapet", 0)
        a, b = layout.u_range(st, D)
        n = int(round((b - a) / bay))
        for i in range(n + 1):
            u = a + (b - a) * i / n
            mb.box(u - 0.45, u + 0.45, D, D + 0.5, 0, H, conc)
        for i in range(n):
            u0, u1 = a + (b - a) * i / n + 0.45, a + (b - a) * (i + 1) / n - 0.45
            mb.box(u0, u1, D, D + 0.06, 0.0, 3.2, M.get("black") if i % 2 == 0 else M.get("concrete_dark"))
            mb.box(u0, u1, D, D + 0.25, 3.2, 3.8, light)
            mb.box(u0, u1, D, D + 0.25, H - 1.3, H, light)
        mb.build("back_wall_" + name, c)
    # 西: 5 階建ての建物の正面。階ごとの窓の帯
    st = layout.stand("west")
    bb = st["back_block"]
    mb = MB(layout.xf("west"))
    u0, u1, un = st["u0"][0], st["u1"][0], bb["north_from_u"]
    for (ua, ub, D) in ((u0, un, bb["d1"]), (un, u1, bb["d1_north"])):
        nfl = 5
        fh = bb["z_top"] / nfl
        for f in range(nfl):
            z = f * fh
            mb.box(ua + 0.6, ub - 0.6, D, D + 0.08, z + 1.1, z + fh - 0.7, glass)
            mb.box(ua, ub, D, D + 0.3, z + fh - 0.5, z + fh, light)
        nb = int(round((ub - ua) / 7.0))
        for i in range(nb + 1):
            u = ua + (ub - ua) * i / nb
            mb.box(u - 0.35, u + 0.35, D, D + 0.4, 0, bb["z_top"], light)
        # 入口のひさし
    mb.box(-12, 12, bb["d1"], bb["d1"] + 5.0, 4.2, 4.6, M.get("white_paint"))
    for u in (-11, -4, 4, 11):
        mb.cyl((u, bb["d1"] + 4.5, 0), (u, bb["d1"] + 4.5, 4.2), 0.18, M.get("white_steel"), n=10)
    # 両端の壁(客席の端)に沿う階段の箱
    mb.build("west_facade", c)


# ---------------------------------------------------------------- 地面

def _ground(cfg, c):
    mb = MB()
    far = M.get("ground_far")
    mb.rect(-9000, 9000, -9000, 9000, -0.12, far)
    mb.rect(-420, 420, -420, 420, -0.09, M.get("asphalt"))
    mb.build("ground_base", c)
    g = MB()
    z = -0.06
    # 南の正面広場(レンガ色の舗装)
    plaza = [(-116, -44), (-118, 44), (-150, 62), (-200, 50), (-215, 0), (-200, -50), (-150, -62)]
    g.face([(x, y, z) for (x, y) in reversed(plaza)], M.get("paving_brick"))
    # 広場の中の灰色の帯
    g.rect(-200, -118, -1.2, 1.2, z + 0.01, M.get("paving_grey"))
    # スタンドのすぐ外の通路
    g.rect(-66, 96, -80, -68.5, z, M.get("paving_grey"))
    g.rect(92, 100, -70, 60, z, M.get("paving_grey"))
    g.rect(-66, 80, 84, 92, z, M.get("paving_grey"))
    # 東の練習グラウンド(芝)、北東の人工芝、北の駐車場、南東のホッケー場
    g.rect(-20, 88, -140, -72, z, M.get("lawn"))
    g.rect(100, 162, -140, -18, z, M.get("turf2"))
    g.rect(-108, -24, -136, -80, z, M.get("hockey"))
    g.rect(100, 162, -14, 32, z + 0.005, M.get("asphalt_dark"))
    # 南西・南東の公園の芝
    g.face([(x, y, z) for (x, y) in reversed([(-125, 66), (-150, 66), (-205, 54), (-230, 120), (-140, 130)])], M.get("lawn"))
    g.face([(x, y, z) for (x, y) in reversed([(-118, -140), (-230, -140), (-205, -54), (-150, -66), (-118, -60)])], M.get("lawn"))
    g.rect(-420, -220, -200, 200, z - 0.01, M.get("lawn"))
    # 西の道路
    road = [(160, 48), (94, 74), (30, 100), (-60, 106), (-160, 124), (-420, 150)]
    for (p, q) in zip(road, road[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * 5.0, dx / L * 5.0
        g.face(((p[0] + nx, p[1] + ny, z + 0.02), (q[0] + nx, q[1] + ny, z + 0.02),
                (q[0] - nx, q[1] - ny, z + 0.02), (p[0] - nx, p[1] - ny, z + 0.02)), M.get("asphalt_dark"))
    g.build("ground_near", c)
    # 白線(駐車場とホッケー場の枠、人工芝のライン)
    ln = MB()
    w = M.get("line_white")
    for (x0, x1, y0, y1) in ((104, 158, -136, -22), (-104, -28, -132, -84)):
        for (a, b, cc, d) in ((x0, x1, y0, y0 + 0.15), (x0, x1, y1 - 0.15, y1), (x0, x0 + 0.15, y0, y1), (x1 - 0.15, x1, y0, y1),
                              ((x0 + x1) / 2 - 0.07, (x0 + x1) / 2 + 0.07, y0, y1)):
            ln.rect(a, b, cc, d, z + 0.02, w)
    for i in range(18):
        ln.rect(104 + i * 3.0, 104.12 + i * 3.0, 4, 9.5, z + 0.03, w)
        ln.rect(104 + i * 3.0, 104.12 + i * 3.0, 14, 19.5, z + 0.03, w)
    ln.build("ground_lines", c)


# ---------------------------------------------------------------- 近鉄の線路(推定)

# 近鉄奈良線は球場の南を東西に走る。東花園駅(北緯 34.6646、東経 135.6178)を通り、真東へ向かう。
# 座標に直すと、駅は (X -271, Y 868)、線は真東の向き (-0.247, -0.969)。地上を走る複線として作る(高架かどうかは未確認)。
RAIL_P0 = (-271.0, 868.0)
RAIL_DIR = (-0.247, -0.969)


def _rail_dist(x, y):
    dx, dy = x - RAIL_P0[0], y - RAIL_P0[1]
    t = dx * RAIL_DIR[0] + dy * RAIL_DIR[1]
    return abs(dx * RAIL_DIR[1] - dy * RAIL_DIR[0])


def _railway(cfg, c):
    mb = MB()
    ux, uy = RAIL_DIR
    nx, ny = -uy, ux          # 線に直角

    def P(t, o, z):
        return (RAIL_P0[0] + ux * t + nx * o, RAIL_P0[1] + uy * t + ny * o, z)
    t0, t1 = -900.0, 2300.0
    # 道床
    mb.face((P(t0, -6, 0.05), P(t1, -6, 0.05), P(t1, 6, 0.05), P(t0, 6, 0.05)), M.get("ballast"))
    # レール 4 本
    for o in (-2.9, -1.5, 1.5, 2.9):
        oo = o + (0.0 if abs(o) > 2 else 0.0)
        mb.face((P(t0, oo - 0.04, 0.25), P(t1, oo - 0.04, 0.25), P(t1, oo + 0.04, 0.25), P(t0, oo + 0.04, 0.25)), M.get("rail"))
    # 架線柱(50 m ごと)と架線
    k = int((t1 - t0) / 50)
    for i in range(k + 1):
        t = t0 + i * 50
        for o in (-5.5, 5.5):
            mb.cyl(P(t, o, 0), P(t, o, 7.5), 0.15, M.get("grey_steel"), n=6)
        mb.bar(P(t, -5.5, 7.2), P(t, 5.5, 7.2), 0.15, 0.25, M.get("grey_steel"))
    for o in (-2.2, 2.2):
        mb.cyl(P(t0, o, 5.6), P(t1, o, 5.6), 0.02, M.get("dark_steel"), n=4)
    # 柵
    for o in (-8.0, 8.0):
        mb.face((P(t0, o, 0), P(t1, o, 0), P(t1, o, 1.6), P(t0, o, 1.6)), M.get("grey_steel"))
    # 東花園駅のホーム屋根(推定の大きさ)
    for o in (-7.5, 7.5):
        mb.face((P(-60, o - 2.5, 4.5), P(140, o - 2.5, 4.5), P(140, o + 2.5, 4.5), P(-60, o + 2.5, 4.5)), M.get("roof_sheet"))
        mb.face((P(-60, o - 2.5, 1.0), P(140, o - 2.5, 1.0), P(140, o + 2.5, 1.0), P(-60, o + 2.5, 1.0)), M.get("concrete"))
    mb.build("railway", c)
    _train(P, c)


TRAIN_T0 = 260.0     # 電車の先頭の位置(線路に沿った距離)。動画では location を線路の向きに動かす


def _train(P, c):
    """電車を 1 本(6 両)。動かせるように線路とは別の物にする。夜は窓が灯る。"""
    tb = MB()
    win = M.emissive("train_window", (1.0, 0.9, 0.72, 1), 0.0, 6.0, base=(0.05, 0.06, 0.07, 1))
    o0 = -2.9
    for j in range(6):
        ta = TRAIN_T0 + j * 20.5
        q = [P(ta, o0 - 1.4, 0.5), P(ta + 20, o0 - 1.4, 0.5), P(ta + 20, o0 + 1.4, 0.5), P(ta, o0 + 1.4, 0.5)]
        top = [(p[0], p[1], 4.1) for p in q]
        for i in range(4):
            jj = (i + 1) % 4
            tb.face((q[i], q[jj], top[jj], top[i]), M.get("train_body"))
        tb.face(top, M.get("roof_a"))
        # 両側の窓の帯(車体の 3 cm 外)
        for side in (-1, 1):
            o = o0 + side * 1.43
            a, b = ta + 1.2, ta + 18.8
            quad = (P(a, o, 1.7), P(b, o, 1.7), P(b, o, 2.75), P(a, o, 2.75))
            tb.face(quad if side < 0 else tuple(reversed(quad)), win)
    tb.build("train", c)


# ---------------------------------------------------------------- 木・家・山

def _blob(mb, cx, cy, cz, rx, rz, mat, seg=7, rings=4):
    pts = []
    for j in range(rings + 1):
        ph = math.pi * j / rings
        for i in range(seg):
            th = 2 * math.pi * i / seg
            pts.append((cx + rx * math.sin(ph) * math.cos(th), cy + rx * math.sin(ph) * math.sin(th), cz + rz * math.cos(ph)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            mb.face((pts[a + seg], pts[b + seg], pts[b], pts[a]), mat)


def _trees(cfg, c):
    rnd = random.Random(2018)
    mb = MB()
    trunk = M.get("trunk")
    leaves = [M.get("leaf_a"), M.get("leaf_b")]
    zones = [  # (x0, x1, y0, y1, 本数)
        (-215, -128, 66, 128, 70), (-215, -122, -138, -64, 60), (-400, -222, -190, 190, 160),
        (-112, -70, 96, 104, 8), (100, 104, -140, 40, 14), (-20, 90, -146, -141, 16),
    ]
    for (x0, x1, y0, y1, n) in zones:
        for _ in range(n):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            h = rnd.uniform(5.0, 10.0)
            r = h * rnd.uniform(0.28, 0.4)
            mb.cyl((x, y, 0), (x, y, h * 0.55), 0.18, trunk, n=5)
            lf = leaves[rnd.randrange(2)]
            _blob(mb, x, y, h * 0.7, r, h * 0.36, lf)
            _blob(mb, x + r * 0.4, y - r * 0.3, h * 0.58, r * 0.7, h * 0.25, lf)
    # 広場の脇の生け垣
    for sy in (-1, 1):
        mb.box(-190, -128, sy * 60 - 1.0, sy * 60 + 1.0, 0, 1.1, leaves[0])
    mb.build("trees", c, smooth=True)


def _town(cfg, c):
    rnd = random.Random(1929)
    mb = MB()
    walls = [M.get("house_a"), M.get("house_b"), M.get("house_c")]
    roofs = [M.get("roof_a"), M.get("roof_b"), M.get("roof_c")]

    aparts = [M.get("apart_a"), M.get("apart_b")]
    froof, fwall = M.get("factory_roof"), M.get("factory_wall")

    def factory(x, y, w, d, h, rot):
        ca, sa = math.cos(rot), math.sin(rot)

        def T(px, py, pz):
            return (x + px * ca - py * sa, y + px * sa + py * ca, pz)
        b = [T(-w / 2, -d / 2, 0), T(w / 2, -d / 2, 0), T(w / 2, d / 2, 0), T(-w / 2, d / 2, 0)]
        t = [(p[0], p[1], h) for p in b]
        for i in range(4):
            j = (i + 1) % 4
            mb.face((b[i], b[j], t[j], t[i]), fwall)
        # ゆるい切妻の金属屋根
        r0, r1 = T(-w / 2, 0, h + d * 0.12), T(w / 2, 0, h + d * 0.12)
        mb.face((t[0], t[1], r1, r0), froof)
        mb.face((t[2], t[3], r0, r1), froof)
        mb.face((t[1], t[2], r1), fwall)
        mb.face((t[3], t[0], r0), fwall)

    def house(x, y, w, d, h, rot, apart=False):
        ca, sa = math.cos(rot), math.sin(rot)

        def T(px, py, pz):
            return (x + px * ca - py * sa, y + px * sa + py * ca, pz)
        wm, rm = walls[rnd.randrange(3)], roofs[rnd.randrange(3)]
        if apart:
            wm, rm = aparts[rnd.randrange(2)], M.get("concrete_dark")
        b = [T(-w / 2, -d / 2, 0), T(w / 2, -d / 2, 0), T(w / 2, d / 2, 0), T(-w / 2, d / 2, 0)]
        t = [(p[0], p[1], h) for p in b]
        for i in range(4):
            j = (i + 1) % 4
            mb.face((b[i], b[j], t[j], t[i]), wm)
        if h > 9:
            mb.face(t, rm)
            return
        r0, r1 = T(-w / 2, 0, h + d * 0.28), T(w / 2, 0, h + d * 0.28)
        mb.face((t[0], t[1], r1, r0), rm)
        mb.face((t[2], t[3], r0, r1), rm)
        mb.face((t[1], t[2], r1), wm)
        mb.face((t[3], t[0], r0), wm)

    def keep_out(x, y):
        if -235 < x < 170 and -150 < y < 96:
            return True
        # 西の道路の近く
        road = [(160, 48), (94, 74), (30, 100), (-60, 106), (-160, 124), (-420, 150)]
        for (p, q) in zip(road, road[1:]):
            dx, dy = q[0] - p[0], q[1] - p[1]
            L2 = dx * dx + dy * dy
            t = max(0, min(1, ((x - p[0]) * dx + (y - p[1]) * dy) / L2))
            if math.hypot(x - p[0] - t * dx, y - p[1] - t * dy) < 12:
                return True
        # 南の公園(花園中央公園)の芝生だけを空ける。その先は町
        if -430 < x <= -215 and -200 < y < 200:
            return True
        # 近鉄の線路の近く
        if _rail_dist(x, y) < 16:
            return True
        return False

    step = 15.0
    xs = int(1400 / step)
    for i in range(-xs, xs + 1):
        for j in range(-xs, xs + 1):
            x, y = i * step + rnd.uniform(-3, 3), j * step + rnd.uniform(-3, 3)
            if keep_out(x, y) or rnd.random() < 0.34:
                continue
            dist = math.hypot(x, y)
            if dist > 1400:
                continue
            rot = rnd.choice((0, math.pi / 2)) + 0.25
            r = rnd.random()
            if r < 0.035 and dist > 230:
                # マンション(5〜11 階)
                house(x, y, rnd.uniform(18, 34), rnd.uniform(10, 13), rnd.choice((15.0, 18.0, 21.0, 24.0, 30.0, 33.0)), rot, apart=True)
            elif r < 0.10 and dist > 200:
                # 町工場(東大阪らしい低い大きな建物)
                factory(x, y, rnd.uniform(16, 26), rnd.uniform(12, 20), rnd.uniform(6.0, 9.0), rot)
            else:
                house(x, y, rnd.uniform(7, 11), rnd.uniform(6, 9), rnd.uniform(5.5, 7.5), rot)
    mb.build("town", c)


def _mountain(cfg, c):
    """東(-Y)の遠くの生駒山。稜線だけの板。"""
    mb = MB()
    mat = M.get("mountain")
    rnd = random.Random(642)
    ph = [rnd.uniform(0, 6.28) for _ in range(6)]
    xs = list(range(-14000, 14001, 250))

    def hgt(x):
        t = x / 1000.0
        # 生駒山(642 m)は球場の東南東。北へ向かって低くなる
        h = 290 + 350 * math.exp(-((x + 150) / 3000.0) ** 2) - 60 * max(0.0, x / 6000.0)
        h += 40 * math.sin(t * 0.9 + ph[1]) + 22 * math.sin(t * 2.1 + ph[2]) + 10 * math.sin(t * 5.0 + ph[3])
        return max(60.0, h)
    for (a, b) in zip(xs, xs[1:]):
        ha, hb = hgt(a), hgt(b)
        mb.face(((b, -3300, 0), (a, -3300, 0), (a, -4900, ha), (b, -4900, hb)), mat)
        mb.face(((b, -4900, hb), (a, -4900, ha), (a, -5800, ha * 0.9), (b, -5800, hb * 0.9)), mat)
    mb.build("mountain", c, smooth=True)


def _night_exterior(cfg, xf, D, H, u0, u1):
    """夜の外観の光: 正面を下から照らす光、広場の街灯。"""
    import bpy
    nc = coll("night_lights")
    c = coll("exterior")
    warm = (1.0, 0.9, 0.78)

    def area(name, loc, target, size, energy):
        li = bpy.data.lights.new(name, "AREA")
        li.size = size
        li.energy = energy
        li.color = warm
        ob = bpy.data.objects.new(name, li)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        ob.visible_camera = False
        nc.objects.link(ob)

    n = 6
    for i in range(n):
        u = u0 + (u1 - u0) * (i + 0.5) / n
        area("facade_wash_%d" % i, xf @ Vector((u, D + 9.0, 0.6)), xf @ Vector((u, D, H * 0.55)), 3.0, 700.0)
    k = cfg["stands"]["corners"]
    X = cfg["exterior"]
    for sy in (-1, 1):
        for a in (115, 140, 165):
            ang = math.radians(a if sy > 0 else -a)
            cx, cy = k["cx"], sy * k["cy"]
            r = X["corner_r"]
            loc = (cx + (r + 9) * math.cos(ang), cy + (r + 9) * math.sin(ang), 0.6)
            tgt = (cx + r * math.cos(ang), cy + r * math.sin(ang), X["corner_h"] * 0.5)
            area("corner_wash_%d_%d" % (sy, a), loc, tgt, 3.0, 600.0)
    # 広場の街灯(昼も柱は見える)
    mb = MB()
    lamp = M.emissive("street_lamp", (1.0, 0.92, 0.8, 1), 0.0, 40.0, base=(0.8, 0.8, 0.78, 1))
    posts = [(-140, sy * yy) for sy in (-1, 1) for yy in (20, 56)] + [(-172, sy * yy) for sy in (-1, 1) for yy in (20, 54)] + [(-204, -24), (-204, 24)]
    for i, (x, y) in enumerate(posts):
        mb.cyl((x, y, 0), (x, y, 7.0), 0.09, M.get("dark_steel"), n=8)
        mb.box(x - 0.35, x + 0.35, y - 0.35, y + 0.35, 7.0, 7.25, M.get("dark_steel"))
        mb.rect(x - 0.3, x + 0.3, y - 0.3, y + 0.3, 6.99, lamp)
        li = bpy.data.lights.new("street_%d" % i, "POINT")
        li.energy = 2500.0
        li.color = warm
        li.shadow_soft_size = 0.3
        ob = bpy.data.objects.new("street_%d" % i, li)
        ob.location = (x, y, 6.8)
        nc.objects.link(ob)
    mb.build("street_lamps", c)
