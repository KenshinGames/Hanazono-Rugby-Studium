"""⑥大型映像装置: 枠、表示面(架空の対戦表示)、時計、脚、旗のポール。"""
import math

from . import config, materials as M
from .util import MB, coll, frame_xf, text_obj


def _disc(mb, cx, cy, r, z, mat, n=40, r_in=0.0):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    if r_in <= 0:
        mb.face(pts, mat)
        return
    inner = [(cx + r_in * math.cos(2 * math.pi * i / n), cy + r_in * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        mb.face((inner[i], pts[i], pts[j], inner[j]), mat)


def build():
    S = config.load()["screen"]
    c = coll("screen")
    fw, fh = S["frame_w"], S["frame_h"]
    zb = S["z_bottom"]
    xfc = S["x_face"]
    yc = S["y_center"]
    nrm = (-1, 0, 0)
    # 局所: x=見る人の右(-Y)、y=上、z=手前(-X)。原点は枠の下の中央
    xf = frame_xf((xfc, yc, zb), nrm)
    frame = M.get("screen_frame")
    mb = MB(xf)
    th = S["thickness"]
    mb.box(-fw / 2, fw / 2, 0.0, fh, -th, 0.0, frame)
    # 下の白い梁(看板の帯)と脚
    mb.box(-fw / 2 - 0.2, fw / 2 + 0.2, -1.25, 0.0, -th - 0.1, 0.25, M.get("white_paint"))
    conc = M.get("concrete")
    ls = S["leg_size"]
    for sx in (-1, 1):
        x = sx * S["leg_y"]
        mb.box(x - ls / 2, x + ls / 2, -zb, -1.25, -th / 2 - ls / 2, -th / 2 + ls / 2, conc)
    # 後ろの点検用の階段の箱
    mb.box(-2.0, 2.0, -zb + 13.0, -1.25, -th - 2.4, -th, M.get("concrete_light"))
    mb.build("screen_body", c)

    # 表示面(右寄せ。左に時計の列)
    dw, dh = S["display_w"], S["display_h"]
    dx1 = fw / 2 - 0.5
    dx0 = dx1 - dw
    dy0 = 1.35
    dy1 = dy0 + dh
    em = M.emissive
    bg = em("scr_bg", (0.012, 0.016, 0.035, 1), 1.0, 1.0)
    cyan = em("scr_cyan", (0.05, 0.45, 0.85, 1), 2.2, 2.2)
    white = em("scr_white", (0.9, 0.9, 0.9, 1), 2.2, 2.2)
    yellow = em("scr_yellow", (0.95, 0.75, 0.1, 1), 2.2, 2.2)
    green = em("scr_green", (0.05, 0.5, 0.2, 1), 2.0, 2.0)
    orange = em("scr_orange", (0.9, 0.3, 0.05, 1), 2.0, 2.0)
    d = MB(xf)
    d.face(((dx0, dy0, 0.03), (dx1, dy0, 0.03), (dx1, dy1, 0.03), (dx0, dy1, 0.03)), bg)
    d.face(((dx0, dy1 - 0.95, 0.04), (dx1, dy1 - 0.95, 0.04), (dx1, dy1, 0.04), (dx0, dy1, 0.04)), cyan)
    cxm = (dx0 + dx1) / 2
    cym = dy0 + dh * 0.56
    _disc(d, cxm - 3.6, cym, 1.55, 0.04, green)
    _disc(d, cxm - 3.6, cym, 1.25, 0.045, white, r_in=1.12)
    _disc(d, cxm + 3.6, cym, 1.55, 0.04, orange)
    _disc(d, cxm + 3.6, cym, 1.25, 0.045, white, r_in=1.12)
    d.face(((cxm - 6.5, dy0 + 1.55, 0.04), (cxm + 6.5, dy0 + 1.55, 0.04), (cxm + 6.5, dy0 + 1.62, 0.04), (cxm - 6.5, dy0 + 1.62, 0.04)), yellow)
    d.build("screen_display", c)

    def T(name, body, h, x, y, mat, align="CENTER", jp=False, mw=None, z=0.06):
        p = xf @ __import__("mathutils").Vector((x, y, z))
        return text_obj(name, body, h, mat, c, p, nrm, align=align, jp=jp, max_width=mw)

    T("scr_t1", "HANAZONO RUGBY FESTIVAL   ROUND 7", 0.42, cxm, dy1 - 0.48, white, mw=dw - 1.0)
    T("scr_ta", "IKOMA", 0.5, cxm - 3.6, cym + 0.12, white, mw=2.0)
    T("scr_ta2", "STAGS", 0.3, cxm - 3.6, cym - 0.45, white, mw=2.0)
    T("scr_tb", "KAWACHI", 0.42, cxm + 3.6, cym + 0.12, white, mw=2.0)
    T("scr_tb2", "WAVES", 0.3, cxm + 3.6, cym - 0.45, white, mw=2.0)
    T("scr_vs", "VS", 0.7, cxm, cym, yellow)
    T("scr_names", "IKOMA STAGS   vs   KAWACHI WAVES", 0.42, cxm, dy0 + 2.05, white, mw=dw - 2.0)
    T("scr_ko", "14:00 KICK OFF", 0.5, cxm, dy0 + 0.85, yellow)

    # 枠の下の施設名と、梁の看板(架空)
    T("scr_name", "HANAZONO RUGBY STADIUM", 0.42, cxm, 0.68, M.get("text_white"), mw=dw)
    s = MB(xf)
    npan = 4
    for i in range(npan):
        x0 = -fw / 2 + 0.6 + (fw - 1.2) * i / npan
        x1 = -fw / 2 + 0.6 + (fw - 1.2) * (i + 1) / npan
        s.face(((x0 + 0.05, -1.1, 0.27), (x1 - 0.05, -1.1, 0.27), (x1 - 0.05, -0.15, 0.27), (x0 + 0.05, -0.15, 0.27)),
               M.get("sign_blue" if i % 2 == 0 else "sign_white"))
        T("scr_ad%d" % i, "NANIWA GIKEN" if i % 2 == 0 else "ナニワ技研", 0.42, (x0 + x1) / 2, -0.63,
          M.get("text_white" if i % 2 == 0 else "sign_blue"), jp=(i % 2 == 1), mw=(x1 - x0) - 0.8, z=0.29)
    # 時計 2 つと小さな表示
    clock_x = -fw / 2 + (dx0 + fw / 2) / 2
    face = M.get("sign_white")
    hand = M.get("text_dark")
    for k, (cy, hr, mn) in enumerate(((dy0 + dh - 1.5, 2, 0), (dy0 + dh - 4.3, 0, 26))):
        _disc(s, clock_x, cy, 0.95, 0.03, face)
        for (ang, ln, w) in ((90 - hr * 30 - mn * 0.5, 0.5, 0.07), (90 - mn * 6, 0.78, 0.045)):
            a = math.radians(ang)
            ex, ey = math.cos(a), math.sin(a)
            px, py = -ey * w / 2, ex * w / 2
            s.face(((clock_x - px, cy - py, 0.04), (clock_x + ex * ln - px, cy + ey * ln - py, 0.04),
                    (clock_x + ex * ln + px, cy + ey * ln + py, 0.04), (clock_x + px, cy + py, 0.04)), hand)
        for t in range(12):
            a = math.radians(t * 30)
            x, y = clock_x + 0.82 * math.cos(a), cy + 0.82 * math.sin(a)
            s.face(((x - 0.035, y - 0.035, 0.04), (x + 0.035, y - 0.035, 0.04), (x + 0.035, y + 0.035, 0.04), (x - 0.035, y + 0.035, 0.04)), hand)
    s.face(((clock_x - 0.9, dy0 + 0.5, 0.03), (clock_x + 0.9, dy0 + 0.5, 0.03), (clock_x + 0.9, dy0 + 1.1, 0.03), (clock_x - 0.9, dy0 + 1.1, 0.03)),
           M.get("black"))
    # 旗のポール(旗は無地の架空のもの)
    steel = M.get("white_steel")
    for i, (px, hh, fm) in enumerate(((-5.0, 4.0, "flag_c"), (-2.5, 4.4, "flag_b"), (0.0, 6.5, "flag_a"), (2.5, 4.4, "flag_d"), (5.0, 4.0, "flag_b"))):
        s.cyl((px, fh, -th / 2), (px, fh + hh, -th / 2), 0.04, steel, n=6)
        s.face(((px, fh + hh - 1.0, -th / 2), (px + 1.4, fh + hh - 1.1, -th / 2 + 0.25), (px + 1.4, fh + hh - 0.1, -th / 2 + 0.25), (px, fh + hh, -th / 2)),
               M.get(fm))
    s.build("screen_extras", c)
