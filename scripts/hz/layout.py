"""スタンドの断面を段の一覧に直す。stands.py と seats.py が共通で使う。"""
from . import config
from .util import stand_xf


def stand(name):
    return config.load()["stands"][name]


def xf(name):
    st = stand(name)
    return stand_xf(st["side"], st["wall"])


def treads(st):
    """前から順に、踏み面の一覧 [{d0, d1, z, kind('row'|'flat'), seg, row}]。"""
    d = 0.0
    z = st["front_wall_h"]
    out = []
    for si, seg in enumerate(st["segments"]):
        k = seg[0]
        if k == "rows":
            _, n, t, r = seg
            for i in range(n):
                out.append(dict(d0=d, d1=d + t, z=z, kind="row", seg=si, row=i, riser=r))
                d += t
                z += r
        elif k == "flat":
            out.append(dict(d0=d, d1=d + seg[1], z=z, kind="flat", seg=si, row=0, riser=0.0))
            d += seg[1]
        elif k == "rise":
            z += seg[1]
    return out


def u_range(st, d):
    return st["u0"][0] + st["u0"][1] * d, st["u1"][0] + st["u1"][1] * d


def depth(st):
    return treads(st)[-1]["d1"]


def top_z(st):
    return treads(st)[-1]["z"]


def aisles(st):
    """縦通路の中心の u(d=0 での位置)。両端も含む。"""
    n = st.get("aisles", 0)
    a, b = st["u0"][0], st["u1"][0]
    return [a + (b - a) * i / n for i in range(n + 1)] if n else []


def voms(st):
    """出入口(ボミトリー)の一覧 [{u0, u1, d0, d1, zf, ztop}]。横通路の後ろに食い込む箱。"""
    sc = config.load()["seats"]
    T = treads(st)
    out = []
    for v in st.get("voms", []):
        flat = [t for t in T if t["seg"] == v["seg"]][0]
        rows = [t for t in T if t["d0"] >= flat["d1"] - 1e-6][:sc["vom_rows"]]
        for u in v["us"]:
            out.append(dict(u0=u - sc["vom_w"] / 2, u1=u + sc["vom_w"] / 2, d0=flat["d1"], d1=rows[-1]["d1"],
                            zf=flat["z"], ztop=rows[-1]["z"] + rows[-1]["riser"] + 1.1))
    return out


def subtract(a, b, cuts):
    """区間 [a, b] から cuts の区間を除いた残り。"""
    out = [(a, b)]
    for (c0, c1) in sorted(cuts):
        nxt = []
        for (x0, x1) in out:
            if c1 <= x0 or c0 >= x1:
                nxt.append((x0, x1))
            else:
                if c0 > x0:
                    nxt.append((x0, c0))
                if c1 < x1:
                    nxt.append((c1, x1))
        out = nxt
    return out
