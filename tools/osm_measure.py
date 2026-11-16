"""OpenStreetMap の外形を、グラウンド基準の座標(メートル)に直して表示する。

使い方: python3 tools/osm_measure.py refs/map/osm.json
座標系: 原点=第1グラウンド(芝の外形)の中心、+X=長辺方向の北寄り、+Y=西(メインスタンド側)
"""
import json, math, sys

LAT0, LON0 = 34.668917, 135.626250
IDS = {226526055: "pitch(芝の外形)", 619628134: "北スタンド", 1047327211: "西スタンド(客席)",
       1047327212: "西スタンド(建物)", 1047327213: "東スタンド", 1047327214: "南スタンド",
       664204657: "敷地(stadium)"}

def en(p):
    return ((p["lon"] - LON0) * math.cos(math.radians(LAT0)) * 111320.0,
            (p["lat"] - LAT0) * 110574.0)

d = json.load(open(sys.argv[1]))
ways = {e["id"]: [en(p) for p in e["geometry"]] for e in d["elements"]
        if e["type"] == "way" and e["id"] in IDS}

pitch = ways[226526055][:-1]
# 長辺の向き: 最長の辺の方向
best = max(((math.dist(pitch[i], pitch[(i + 1) % len(pitch)]), i) for i in range(len(pitch))))
i = best[1]
a, b = pitch[i], pitch[(i + 1) % len(pitch)]
ang = math.atan2(b[1] - a[1], b[0] - a[0])
if math.sin(ang) < 0:
    ang += math.pi
ux = (math.cos(ang), math.sin(ang))          # +X (北寄り)
uy = (-ux[1], ux[0])                         # +Y (左手=西)

def proj(p, c=(0, 0)):
    return ((p[0] - c[0]) * ux[0] + (p[1] - c[1]) * ux[1],
            (p[0] - c[0]) * uy[0] + (p[1] - c[1]) * uy[1])

pp = [proj(p) for p in pitch]
cx = (min(p[0] for p in pp) + max(p[0] for p in pp)) / 2
cy = (min(p[1] for p in pp) + max(p[1] for p in pp)) / 2
c = (cx * ux[0] + cy * uy[0], cx * ux[1] + cy * uy[1])
print("長辺の方位: 真北から東へ %.1f 度 (+X の向き)" % (90 - math.degrees(ang)))
print("中心(東,北 m; 基準点から): %.1f, %.1f" % c)
for wid, name in IDS.items():
    if wid not in ways:
        continue
    q = [proj(p, c) for p in ways[wid]]
    xs = [p[0] for p in q]; ys = [p[1] for p in q]
    print("\n%s  X[%.1f, %.1f] Y[%.1f, %.1f]  幅X=%.1f 幅Y=%.1f" %
          (name, min(xs), max(xs), min(ys), max(ys), max(xs) - min(xs), max(ys) - min(ys)))
    print("  " + " ".join("(%.1f,%.1f)" % p for p in q))
