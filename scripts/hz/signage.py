"""看板(すべて架空の社名)と、スタンドの上の小さな照明ポール。実在の企業のロゴは使わない。"""
from mathutils import Vector

from . import config, layout, materials as M
from .util import MB, coll, text_obj

# 架空の社名(ラグビーの用語などから作った。実在の企業とは関係ない)
NAMES = [
    ("TRYLINE SPORTS", False, "sign_white", "sign_navy"),
    ("ナニワ技研", True, "sign_blue", "text_white"),
    ("RUCK ENERGY", False, "sign_yellow", "text_dark"),
    ("イコマ精工", True, "sign_white", "sign_red"),
    ("LINEOUT COFFEE", False, "sign_green", "text_white"),
    ("カワチ食品", True, "sign_white", "sign_green"),
    ("MAUL & CO.", False, "sign_navy", "text_white"),
    ("ミナミ運輸", True, "sign_red", "text_white"),
    ("SCRUM HALF BANK", False, "sign_white", "sign_blue"),
    ("ハナゾノ建設", True, "sign_white", "text_dark"),
]


def _board(mb, c, xf, nrm, u0, u1, d, z0, z1, idx, tag, text_off=0.06, jp_scale=0.55):
    name, jp, bg, fg = NAMES[idx % len(NAMES)]
    mb.box(u0, u1, d - 0.05, d + 0.05, z0, z1, M.get(bg))
    p = xf @ Vector(((u0 + u1) / 2, d - 0.05 - text_off, (z0 + z1) / 2))
    text_obj("ad_%s" % tag, name, (z1 - z0) * (jp_scale if jp else 0.45), M.get(fg), c, p, nrm, jp=jp,
             max_width=(u1 - u0) * 0.86)


def build():
    c = coll("signage")
    # ---- スタンドの最上段の後ろの看板と小さな照明ポール
    for name, nboards, bw, bh in (("east", 9, 7.0, 1.7), ("north", 4, 6.0, 1.6)):
        st = layout.stand(name)
        xf = layout.xf(name)
        nrm = (xf.to_3x3() @ Vector((0, -1, 0))).normalized()
        D = layout.depth(st) - 0.3
        zt = layout.top_z(st) + st.get("back_parapet", 0)
        a, b = layout.u_range(st, D)
        mb = MB(xf)
        steel = M.get("grey_steel")
        if name == "east":
            centres = [a + (b - a) * (i + 0.5) / nboards for i in range(nboards)]
        else:
            centres = [-36.0, -22.0, 22.0, 36.0]
        for i, uc in enumerate(centres):
            for du in (-bw / 2 + 0.4, bw / 2 - 0.4):
                mb.cyl((uc + du, D, zt - 1.0), (uc + du, D, zt + 0.9 + bh), 0.07, steel, n=6)
            _board(mb, c, xf, nrm, uc - bw / 2, uc + bw / 2, D - 0.1, zt + 0.9, zt + 0.9 + bh, i + (3 if name == "north" else 0),
                   "%s_top%d" % (name, i))
        # 小さな照明ポール
        npole = 14 if name == "east" else 6
        for i in range(npole):
            u = a + 3 + (b - a - 6) * i / (npole - 1)
            if any(abs(u - uc) < bw / 2 + 0.3 for uc in centres) or (name == "north" and abs(u) < 11):
                u += bw / 2 + 0.6
            mb.cyl((u, D, zt - 1.0), (u, D, zt + 4.2), 0.06, steel, n=6)
            mb.box(u - 0.3, u + 0.3, D - 0.7, D - 0.05, zt + 4.0, zt + 4.3, M.get("dark_steel"))
        mb.build("signs_" + name, c)

    # ---- グラウンドの周りの低い看板
    cfg = config.load()
    w = cfg["walls"]
    # 東のタッチライン側(メインスタンドから見える向き)
    st = layout.stand("east")
    xf = layout.xf("east")
    nrm = (xf.to_3x3() @ Vector((0, -1, 0))).normalized()
    mb = MB(xf)
    n = 18
    L = 6.0
    for i in range(n):
        uc = -54 + 108 * (i + 0.5) / n
        _board(mb, c, xf, nrm, uc - L / 2 + 0.05, uc + L / 2 - 0.05, -3.6, 0.0, 0.9, i, "pitch_e%d" % i)
    # 前の壁の横断幕の位置にも看板
    for i in range(12):
        uc = -60 + 120 * (i + 0.5) / 12
        _board(mb, c, xf, nrm, uc - 3.5, uc + 3.5, -0.08, 0.9, 2.1, i + 5, "wall_e%d" % i)
    mb.build("signs_pitch_east", c)
    # 南北のゴール裏
    for name, tag in (("north", "n"), ("south", "s")):
        st = layout.stand(name)
        xf = layout.xf(name)
        nrm = (xf.to_3x3() @ Vector((0, -1, 0))).normalized()
        mb = MB(xf)
        for i in range(10):
            uc = -30 + 60 * (i + 0.5) / 10
            _board(mb, c, xf, nrm, uc - 2.95, uc + 2.95, -4.5 if name == "north" else -5.5, 0.0, 0.9, i + 2, "pitch_%s%d" % (tag, i))
        if name == "south":
            for i in range(8):
                uc = -32 + 64 * (i + 0.5) / 8
                _board(mb, c, xf, nrm, uc - 3.6, uc + 3.6, -0.08, 0.5, 1.8, i + 7, "wall_s%d" % i)
        mb.build("signs_pitch_" + name, c)
