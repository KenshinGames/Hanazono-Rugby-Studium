"""④メインスタンドの屋根: 屋根の板、白い鉄骨の立体トラス、丸柱。"""
from . import config, layout, materials as M
from .util import MB, coll


def z_top(R, d):
    t = (d - R["slope_d0"]) / (R["slope_d1"] - R["slope_d0"])
    return R["z_front"] + (R["z_back"] - R["z_front"]) * t


def _depth(R, d, d_end):
    """屋根の上面から下弦までの深さ。柱の所で深く、前と後ろの端で浅い。"""
    pts = [(R["slope_d0"], R["depth_front"]), (R["col_front_d"], R["depth_col_front"]),
           (R["col_rear_d"], R["depth_col_rear"]), (d_end, R["depth_back"])]
    for (a, da), (b, db) in zip(pts, pts[1:]):
        if d <= b:
            return da + (db - da) * (d - a) / (b - a)
    return pts[-1][1]


def panel_ds(R, d0, d1):
    """断面方向の節点の位置。柱の位置を必ず含める。"""
    keys = [d0, R["col_front_d"], R["col_rear_d"], d1]
    out = []
    for a, b in zip(keys, keys[1:]):
        n = max(1, round((b - a) / R["panel"]))
        out += [a + (b - a) * i / n for i in range(n)]
    out.append(d1)
    return out


def frame_us(part):
    n = part["bays"]
    return [part["u0"] + (part["u1"] - part["u0"]) * i / n for i in range(n + 1)]


def ground_z(d):
    """メインスタンドの d の位置の床の高さ。"""
    st = layout.stand("west")
    z = 0.0
    for t in layout.treads(st):
        if t["d0"] <= d:
            z = t["z"]
    return z


def build():
    R = config.load()["roof"]
    c = coll("roof")
    xf = layout.xf("west")
    steel = M.get("white_steel")
    mb = MB(xf)        # 太い材
    web = MB(xf)       # 細い材
    sheet = MB(xf)
    cols = MB(xf)
    RC, RW, RS = 0.10, 0.055, 0.04

    for key in ("main", "north"):
        part = R[key]
        d0, d1 = part["d0"], part["d1"]
        ds = panel_ds(R, d0, d1)
        top = [(d, z_top(R, d)) for d in ds]
        bot = [(d, z_top(R, d) - _depth(R, d, d1)) for d in ds]
        us = frame_us(part)
        if key == "north":
            us = us[1:]          # 境目の骨は主部と共用
        nsub = R["sub_bays"]
        all_us = []
        ulist = frame_us(part)
        for a, b in zip(ulist, ulist[1:]):
            all_us += [a + (b - a) * i / nsub for i in range(nsub)]
        all_us.append(ulist[-1])

        # 断面方向のトラス。柱の通りは太く、間は細く
        for u in all_us:
            main = any(abs(u - f) < 1e-6 for f in ulist)
            if key == "north" and abs(u - ulist[0]) < 1e-6:
                continue
            tgt = mb if main else web
            rc = RC if main else RW
            rw = RW if main else RS
            for i in range(len(ds) - 1):
                tgt.cyl((u, top[i][0], top[i][1]), (u, top[i + 1][0], top[i + 1][1]), rc, steel, n=6)
                tgt.cyl((u, bot[i][0], bot[i][1]), (u, bot[i + 1][0], bot[i + 1][1]), rc, steel, n=6)
                # 斜材は山形に
                if i % 2 == 0:
                    web.cyl((u, bot[i][0], bot[i][1]), (u, top[i + 1][0], top[i + 1][1]), rw, steel, n=5)
                else:
                    web.cyl((u, top[i][0], top[i][1]), (u, bot[i + 1][0], bot[i + 1][1]), rw, steel, n=5)
            for i in range(len(ds)):
                web.cyl((u, top[i][0], top[i][1]), (u, bot[i][0], bot[i][1]), rw, steel, n=5)

        # 長手方向: 上弦の母屋、下弦のつなぎ、その間の斜材
        for i in range(len(ds)):
            edge = i in (0, len(ds) - 1)
            r = RC if edge else RW
            mb.cyl((part["u0"], top[i][0], top[i][1]), (part["u1"], top[i][0], top[i][1]), r, steel, n=6)
            mb.cyl((part["u0"], bot[i][0], bot[i][1]), (part["u1"], bot[i][0], bot[i][1]), r, steel, n=6)
            if _depth(R, ds[i], d1) > 1.2:
                for j in range(len(all_us) - 1):
                    a, b = all_us[j], all_us[j + 1]
                    if j % 2 == 0:
                        web.cyl((a, bot[i][0], bot[i][1]), (b, top[i][0], top[i][1]), RS, steel, n=5)
                    else:
                        web.cyl((a, top[i][0], top[i][1]), (b, bot[i][0], bot[i][1]), RS, steel, n=5)
        # 下弦の面の筋かい(下から見上げたときの網目)
        for j in range(len(all_us) - 1):
            a, b = all_us[j], all_us[j + 1]
            for i in range(len(ds) - 1):
                if (i + j) % 2 == 0:
                    web.cyl((a, bot[i][0], bot[i][1]), (b, bot[i + 1][0], bot[i + 1][1]), RS, steel, n=5)
                else:
                    web.cyl((b, bot[i][0], bot[i][1]), (a, bot[i + 1][0], bot[i + 1][1]), RS, steel, n=5)

        # 屋根の板(上は金属の折板、下は白)
        za, zb = z_top(R, d0), z_top(R, d1)
        e = 0.35
        u0, u1 = part["u0"] - (e if key == "main" else 0), part["u1"] + (e if key == "north" else 0)
        sheet.face(((u0, d0 - e, za + 0.22), (u1, d0 - e, za + 0.22), (u1, d1 + e, zb + 0.22), (u0, d1 + e, zb + 0.22)),
                   M.get("roof_sheet"))
        sheet.face(((u0, d1 + e, zb + 0.10), (u1, d1 + e, zb + 0.10), (u1, d0 - e, za + 0.10), (u0, d0 - e, za + 0.10)),
                   M.get("roof_under"))
        fascia = M.get("white_steel")
        sheet.face(((u0, d0 - e, za - 0.25), (u1, d0 - e, za - 0.25), (u1, d0 - e, za + 0.22), (u0, d0 - e, za + 0.22)), fascia)
        sheet.face(((u1, d1 + e, zb - 0.25), (u0, d1 + e, zb - 0.25), (u0, d1 + e, zb + 0.22), (u1, d1 + e, zb + 0.22)), fascia)
        for uu, flip in ((u0, True), (u1, False)):
            q = ((uu, d0 - e, za - 0.25), (uu, d1 + e, zb - 0.25), (uu, d1 + e, zb + 0.22), (uu, d0 - e, za + 0.22))
            sheet.face(tuple(reversed(q)) if flip else q, fascia)

        # 柱。前の列は客席の中、後ろの列は上のコンコース
        for u in us:
            uu = min(max(u, part["u0"] + 0.6), part["u1"] - 0.6)
            for dcol in (R["col_front_d"], R["col_rear_d"]):
                zb_ = z_top(R, dcol) - _depth(R, dcol, d1)
                zg = ground_z(dcol)
                r = R["col_radius"] if dcol == R["col_front_d"] else R["col_radius"] * 0.8
                cols.box(uu - 0.75, uu + 0.75, dcol - 0.75, dcol + 0.75, zg, zg + 1.3, M.get("concrete"))
                cols.cyl((uu, dcol, zg + 1.3), (uu, dcol, zb_ - 1.6), r, steel, n=20)
                # 柱頭から下弦へ広がる 4 本の方杖
                span_u = (part["u1"] - part["u0"]) / part["bays"] / R["sub_bays"]
                for su in (-1, 1):
                    for sd in (-1, 1):
                        cols.cyl((uu, dcol, zb_ - 1.6), (uu + su * span_u, dcol + sd * 1.4, zb_ + 0.05), 0.11, steel, n=8)
                cols.cyl((uu, dcol, zb_ - 1.6), (uu, dcol, zb_), 0.14, steel, n=8)

    mb.build("roof_truss_main", c, smooth=True)
    web.build("roof_truss_web", c, smooth=True)
    sheet.build("roof_sheet", c)
    cols.build("roof_columns", c, smooth=False)
