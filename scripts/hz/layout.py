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
