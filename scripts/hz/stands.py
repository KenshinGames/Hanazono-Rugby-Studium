"""③スタンドの大きな形: 四方の段の躯体、メインスタンドの後ろの建物、南の両脇の弧の段。"""
import math

from . import config, layout, materials as M
from .util import MB, coll


def build():
    c = coll("stands")
    for name in ("west", "east", "north", "south"):
        _mass(name, c)
    _west_block(c)
    _corners(c)


def _mass(name, c):
    st = layout.stand(name)
    mb = MB(layout.xf(name))
    conc = M.get("concrete")
    wall = M.get("concrete_light")
    T = layout.treads(st)
    zprev = 0.0
    V = layout.voms(st)
    for i, t in enumerate(T):
        d0, d1, z = t["d0"], t["d1"], t["z"]
        a0, b0 = layout.u_range(st, d0)
        a1, b1 = layout.u_range(st, d1)
        dm = (d0 + d1) / 2
        cuts = [(v["u0"], v["u1"]) for v in V if v["d0"] <= dm < v["d1"]]
        for (p, q) in layout.subtract(0.0, 1.0, [((c0 - a0) / (b0 - a0), (c1 - a0) / (b0 - a0)) for c0, c1 in cuts]):
            f0a, f0b = a0 + (b0 - a0) * p, a0 + (b0 - a0) * q
            f1a, f1b = (a1 + (b1 - a1) * p, a1 + (b1 - a1) * q) if not cuts else (f0a, f0b)
            if p == 0.0:
                f1a = a1
            if q == 1.0:
                f1b = b1
            if z > zprev:
                mb.face(((f0a, d0, zprev), (f0b, d0, zprev), (f0b, d0, z), (f0a, d0, z)), wall if i == 0 else conc)
            mb.face(((f0a, d0, z), (f0b, d0, z), (f1b, d1, z), (f1a, d1, z)), conc)
        mb.face(((b0, d0, 0), (b1, d1, 0), (b1, d1, z), (b0, d0, z)), wall)
        mb.face(((a1, d1, 0), (a0, d0, 0), (a0, d0, z), (a1, d1, z)), wall)
        zprev = z
    dE = T[-1]["d1"]
    aE, bE = layout.u_range(st, dE)
    ph = st.get("back_parapet", 0.0)
    mb.face(((bE, dE, 0), (aE, dE, 0), (aE, dE, zprev + ph), (bE, dE, zprev + ph)), wall)
    if ph:
        mb.box(aE, bE, dE - 0.2, dE, zprev, zprev + ph, wall)
    mb.build("stand_" + name, c)


def _west_block(c):
    """メインスタンドの後ろの建物(コンコース、VIP・放送席の階)。細部は⑤で足す。"""
    st = layout.stand("west")
    bb = st["back_block"]
    mb = MB(layout.xf("west"))
    wall = M.get("concrete_light")
    d0 = layout.depth(st)
    z0 = layout.top_z(st)
    u0, u1 = layout.u_range(st, d0)
    un = bb["north_from_u"]
    # 主部と北寄りの浅い部分
    mb.box(u0, un, d0, bb["d1"], 0.0, bb["z_top"], wall)
    mb.box(un, u1, d0, bb["d1_north"], 0.0, bb["z_top"], wall)
    # 中央のガラスの箱(VIP・放送席)。前へ少し張り出す
    ga, gb = z0 + 1.1, bb["z_top"] - 0.45
    glass = M.emissive("box_glass", (1.0, 0.82, 0.6, 1), 0.0, 1.2, base=(0.02, 0.028, 0.035, 1))
    mb.box(bb["box_u0"], bb["box_u1"], d0 - 0.3, d0 + 0.05, ga, gb, glass)
    mb.box(bb["box_u0"], bb["box_u1"], d0 - 0.45, d0 + 0.05, z0, ga, M.get("concrete_light"))
    # ひさし(暗い色の帯)
    mb.box(bb["box_u0"] - 0.3, bb["box_u1"] + 0.3, d0 - 1.4, d0, gb, bb["z_top"] + 0.35, M.get("dark_steel"))
    # 方立て(2.5 m ごと)と中桟、柱型(7.5 m ごと)
    al = M.get("aluminium")
    n = int(round((bb["box_u1"] - bb["box_u0"]) / 2.5))
    for i in range(n + 1):
        u = bb["box_u0"] + (bb["box_u1"] - bb["box_u0"]) * i / n
        if i % 3 == 0:
            mb.box(u - 0.35, u + 0.35, d0 - 0.75, d0, z0, gb, M.get("concrete_light"))
        else:
            mb.box(u - 0.04, u + 0.04, d0 - 0.36, d0 - 0.3, ga, gb, al)
    mb.box(bb["box_u0"], bb["box_u1"], d0 - 0.36, d0 - 0.3, ga + 1.1, ga + 1.16, al)
    mb.build("west_block", c)


def corner_steps():
    """南の両脇の段の一覧 [(r0, r1, z)]。"""
    k = config.load()["stands"]["corners"]
    out = []
    r = k["r_inner"]
    z = k["base_h"]
    for i in range(k["steps"]):
        out.append((r, r + k["tread"], z))
        r += k["tread"]
        z += k["riser"]
    out.append((r, r + k["back_flat"], z))
    return out


def _corners(c):
    k = config.load()["stands"]["corners"]
    conc = M.get("concrete")
    wall = M.get("concrete_light")
    steps = corner_steps()
    n = 40
    for sy, tag in ((1, "sw"), (-1, "se")):
        mb = MB()
        cx, cy = k["cx"], sy * k["cy"]
        # 西側: +Y の向き(90°)から -X の向き(180°)まで。東側: -90° から -180° まで
        a0, a1 = (90.0, 180.0) if sy > 0 else (-180.0, -90.0)

        def P(r, i, z):
            a = math.radians(a0 + (a1 - a0) * i / n)
            return (cx + r * math.cos(a), cy + r * math.sin(a), z)

        zprev = 0.0
        for (r0, r1, z) in steps:
            for i in range(n):
                mb.face((P(r0, i + 1, zprev), P(r0, i, zprev), P(r0, i, z), P(r0, i + 1, z)), conc if zprev > 0 else wall)
                mb.face((P(r0, i, z), P(r1, i, z), P(r1, i + 1, z), P(r0, i + 1, z)), conc)
            for i in (0, n):
                q = (P(r0, i, 0), P(r1, i, 0), P(r1, i, z), P(r0, i, z))
                mb.face(q if i == n else tuple(reversed(q)), wall)
            zprev = z
        rE = steps[-1][1]
        for i in range(n):
            mb.face((P(rE, i, 0), P(rE, i + 1, 0), P(rE, i + 1, zprev + 1.1), P(rE, i, zprev + 1.1)), wall)
        mb.build("corner_" + tag, c)
