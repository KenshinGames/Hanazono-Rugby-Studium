"""②グラウンド: 芝、ライン、ゴールポストとパッド、フラッグ、芝の外の帯、ベンチ。"""
import math

from . import config, materials as M
from .util import MB, coll

Z_LINE = 0.012


def build():
    cfg = config.load()
    c = coll("pitch")
    _turf(cfg, c)
    _lines(cfg, c)
    _goals(cfg, c)
    _flags(cfg, c)
    _benches(cfg, c)


def _turf(cfg, c):
    t = cfg["turf"]
    w = cfg["walls"]
    mb = MB()
    mb.rect(t["x_min"], t["x_max"], t["y_min"], t["y_max"], 0.0, M.get("grass"))
    mb.build("turf", c)
    # 芝の外の人工芝の帯。スタンドの下までのばしておく(外側はスタンドが隠す)
    mb = MB()
    mb.rect(w["south_x"] - 6, w["north_x"] + 3, w["east_y"] - 3, w["west_y"] + 3, -0.02, M.get("apron"))
    mb.build("apron", c)


def _lines(cfg, c):
    f = cfg["field"]
    hl, hw = f["length"] / 2, f["width"] / 2
    dg = hl + f["in_goal_depth"]
    w = f["line_width"]
    dash = f["dash_length"]
    mat = M.get("line_white")
    mb = MB()

    def along_x(x0, x1, y):
        mb.rect(x0, x1, y - w / 2, y + w / 2, Z_LINE, mat)

    def along_y(x, y0, y1):
        mb.rect(x - w / 2, x + w / 2, y0, y1, Z_LINE, mat)

    # 実線: タッチライン(インゴール含む)、ゴールライン、デッドボールライン、ハーフウェイ、22 m
    for s in (-1, 1):
        along_x(-dg, dg, s * hw)
        along_y(s * hl, -hw, hw)
        along_y(s * dg, -hw, hw)
        along_y(s * (hl - f["line_22m_from_goal"]), -hw, hw)
    along_y(0.0, -hw, hw)
    along_x(-f["centre_mark_length"] / 2, f["centre_mark_length"] / 2, 0.0)

    y5 = hw - f["line_5m_from_touch"]
    y15 = hw - f["line_15m_from_touch"]
    x10 = f["line_10m_from_halfway"]
    x22 = hl - f["line_22m_from_goal"]
    x5 = hl - f["line_5m_from_goal"]

    # 10 m ライン(破線)
    for s in (-1, 1):
        for yc in (-y5, -y15, -10.0, 0.0, 10.0, y15, y5):
            along_y(s * x10, yc - dash / 2, yc + dash / 2)

    # 5 m・15 m ライン(破線)。ハーフウェイ・10 m・22 m と交わる所、ゴール前 5 m から内へ
    for sy in (-1, 1):
        for y in (y5, y15):
            for xc in (0.0, -x10, x10, -x22, x22):
                along_x(xc - dash / 2, xc + dash / 2, sy * y)
            for sx in (-1, 1):
                along_x(sx * x5, sx * (x5 - dash), sy * y)

    # ゴールラインの 5 m 手前の破線(6 本)
    ps = cfg["goal"]["post_spacing"] / 2
    for sx in (-1, 1):
        for yc in (-y5, -y15, y15, y5):
            along_y(sx * x5, yc - dash / 2, yc + dash / 2)
        along_y(sx * x5, ps - 2.5, ps + 2.5)
        along_y(sx * x5, -ps - 2.5, -ps + 2.5)
    mb.build("lines", c)


def _goals(cfg, c):
    f, g = cfg["field"], cfg["goal"]
    hl = f["length"] / 2
    ps = g["post_spacing"] / 2
    white = M.get("white_paint")
    mb = MB()
    pads = MB()
    for sx in (-1, 1):
        x = sx * hl
        for sy in (-1, 1):
            y = sy * ps
            mb.cyl((x, y, 0), (x, y, g["post_height"]), g["post_radius_bottom"], white, n=16,
                   r1=g["post_radius_top"], caps=True)
            p = g["pad_size"] / 2
            ph = g["pad_height"]
            # パッドはポストを包み、フィールド側へ少し出る
            pads.box(x - p, x + p, y - p, y + p, 0.0, ph * 0.78, M.get("pad_white"))
            pads.box(x - p, x + p, y - p, y + p, ph * 0.78, ph, M.get("pad_red"), bottom=False)
        mb.cyl((x, -ps, g["crossbar_height"]), (x, ps, g["crossbar_height"]), g["crossbar_radius"], white, n=12)
    mb.build("goal_posts", c, smooth=True)
    pads.build("goal_pads", c)


def _flags(cfg, c):
    f, fl = cfg["field"], cfg["flags"]
    hl, hw = f["length"] / 2, f["width"] / 2
    dg = hl + f["in_goal_depth"]
    off = fl["offset_outside_touch"]
    x22 = hl - f["line_22m_from_goal"]
    pts = []
    for sy in (-1, 1):
        for sx in (-1, 1):
            pts.append((sx * hl, sy * hw))            # ゴールラインとタッチラインの角
            pts.append((sx * dg, sy * hw))            # デッドボールラインの角
            pts.append((sx * x22, sy * (hw + off)))   # 22 m
        pts.append((0.0, sy * (hw + off)))            # ハーフウェイ
    mb = MB()
    h = fl["post_height"]
    for (x, y) in pts:
        mb.cyl((x, y, 0), (x, y, h), 0.035, M.get("pad_white"), n=10, caps=True)
        # 旗は外向きに少しなびかせる
        sy = 1 if y > 0 else -1
        a = math.radians(25)
        dx, dy = math.sin(a) * fl["flag_w"], sy * math.cos(a) * fl["flag_w"]
        p0 = (x, y, h - 0.02)
        p1 = (x, y, h - 0.02 - fl["flag_h"])
        p2 = (x + dx, y + dy, h - 0.06 - fl["flag_h"])
        p3 = (x + dx, y + dy, h - 0.06)
        mb.face((p0, p1, p2, p3), M.get("flag_red"))
    mb.build("flags", c)


def _benches(cfg, c):
    b = cfg["benches"]
    y_front = b["y"] - b["depth"] / 2
    y_back = b["y"] + b["depth"] / 2
    h = b["height"]
    frame = M.get("white_steel")
    clear = M.get("poly_clear")
    mb = MB()
    n = 8
    for xc in b["x_centers"]:
        x0, x1 = xc - b["length"] / 2, xc + b["length"] / 2
        # 後ろの壁から前へ丸くかぶさる屋根(4 分の 1 の弧)
        prof = []
        back_h = h * 0.45
        for i in range(n + 1):
            a = math.pi / 2 * i / n
            prof.append((y_back - (y_back - y_front) * math.sin(a) * 0.95,
                         back_h + (h - back_h) * (1 - math.cos(a)) ** 0.6))
        prof = [(y_back, 0.0)] + prof
        for i in range(len(prof) - 1):
            p, q = prof[i], prof[i + 1]
            mb.face(((x0, p[0], p[1]), (x1, p[0], p[1]), (x1, q[0], q[1]), (x0, q[0], q[1])), clear)
        # 側面
        for x in (x0, x1):
            pts = [(x, p[0], p[1]) for p in prof] + [(x, prof[-1][0], prof[-1][1] - 0.05), (x, y_back - 0.3, 0.0)]
            mb.face(pts, clear)
        # 骨
        nr = int(round(b["length"] / 2.0))
        for k in range(nr + 1):
            x = x0 + (x1 - x0) * k / nr
            for i in range(len(prof) - 1):
                p, q = prof[i], prof[i + 1]
                mb.bar((x, p[0], p[1]), (x, q[0], q[1]), 0.05, 0.05, frame)
        for p in (prof[1], prof[-1]):
            mb.bar((x0, p[0], p[1]), (x1, p[0], p[1]), 0.05, 0.05, frame)
        # 腰掛け
        mb.box(x0 + 0.3, x1 - 0.3, y_back - 0.75, y_back - 0.3, 0.38, 0.46, M.get("bench_blue"))
        mb.box(x0 + 0.3, x1 - 0.3, y_back - 0.32, y_back - 0.25, 0.46, 0.95, M.get("bench_blue"))
        mb.box(x0, x1, y_front - 0.1, y_back, 0.0, 0.03, M.get("concrete_light"))
    mb.build("benches", c)
