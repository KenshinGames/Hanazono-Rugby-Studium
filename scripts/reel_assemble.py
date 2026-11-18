"""scripts/reel.py が描いたコマをつないで、インスタのリール用の動画 out/hanazono_reel.mp4 を作る。

  python3 scripts/reel_assemble.py              # 動画を作る
  python3 scripts/reel_assemble.py --preview    # 動きの確認用(out/reel_v3_preview の小さいコマから)
  python3 scripts/reel_assemble.py --card 画像   # 冒頭のロゴを 1 枚の画像に重ねて確かめる

- 最初の 0.3〜3.0 秒に、Claude と Blender のアイコンを小さく出す(画面は暗くしない)
- カットごとに色を整える(GRADE)。夕方は暖かく、日暮れは青く
- 最後の 0.7 秒で黒へ溶ける
- アイコンは各アプリの商標なので git に入れず、Mac のアプリから毎回取り出す(assets/reel/)
- 音は入れない(音楽はインスタのアプリで付ける)
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FPS = 24
W, H = 1080, 1920
SHOTS = [(1, 3.5), (2, 5.0), (3, 4.0), (4, 4.0), (5, 5.0), (6, 4.0), (7, 4.5), (8, 5.0), (9, 5.0)]
TOTAL = sum(s[1] for s in SHOTS)
LOGO_IN, LOGO_OUT = 0.3, 2.6   # アイコンが出始める秒、消え始める秒(どちらも 0.4 秒かける)
ICON = 150                     # アイコンの大きさ(画素)
GAP = 84                       # アイコンの間(× を置く)
ICON_Y = 330                   # アイコンの上端(インスタの上の表示より下、外壁の上の夜空)
FADE_OUT = 0.7
# カットごとの色(ffmpeg のフィルタ)。描いた後で直せるように、色はここで整える
WARM = "colorbalance=rs=0.02:bs=-0.03:rm=0.03:bm=-0.03:rh=0.02:bh=-0.02,eq=saturation=1.06"
GRADE = {
    2: WARM, 3: WARM, 4: WARM,
    5: "colorbalance=rs=0.05:bs=-0.05:rm=0.07:gm=0.01:bm=-0.07:rh=0.04:bh=-0.05,eq=saturation=1.1:gamma=1.05",
    6: "eq=saturation=1.08",
    7: "colorbalance=bs=0.03:bm=0.02",
}
ICONS = {"claude": "/Applications/Claude.app/Contents/Resources/electron.icns",
         "blender": "/Applications/Blender.app/Contents/Resources/blender_icon_legacy.icns"}


def run(cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("[reel] 失敗: " + " ".join(cmd[:6]))


def icons():
    d = os.path.join(ROOT, "assets", "reel")
    os.makedirs(d, exist_ok=True)
    out = {}
    for k, src in ICONS.items():
        p = os.path.join(d, k + "_icon.png")
        if not os.path.exists(p):
            run(["sips", "-s", "format", "png", "-Z", "1024", src, "--out", p])
        out[k] = p
    return out


def logo_filter(base="[base]", out="[v]"):
    """冒頭のアイコン 2 つと × を重ねる filter_complex の一部。入力 1, 2 がアイコン。うすい影を付けて、明るい所でも読めるようにする。"""
    x_l = (W - (2 * ICON + GAP)) // 2
    x_r = x_l + ICON + GAP
    fades = "fade=t=in:st=%.2f:d=0.4:alpha=1,fade=t=out:st=%.2f:d=0.4:alpha=1" % (LOGO_IN, LOGO_OUT)
    slide = "24*pow(1-min(1\\,max(0\\,(t-%.3f)/0.5))\\,2)" % LOGO_IN
    xs = 22   # × の大きさの半分
    cross = ("color=c=black@0:s=%dx%d:d=%.2f,format=rgba,"
             "geq=r=255:g=255:b=255:a='255*clip(2.4-min(abs(X-Y)\\,abs(X+Y-W+1))/1.414\\,0\\,1)',%s[x]"
             % (2 * xs, 2 * xs, TOTAL, fades))
    shadow = "colorchannelmixer=rr=0:gg=0:bb=0:aa=0.5,boxblur=10:2"
    f = [
        cross,
        "[1]scale=%d:%d,format=rgba,%s,split[ic][ics]" % (ICON, ICON, fades),
        "[2]scale=%d:%d,format=rgba,%s,split[ib][ibs]" % (ICON, ICON, fades),
        "[ics]%s[sc]" % shadow,
        "[ibs]%s[sb]" % shadow,
        "%s[sc]overlay=x='%d-%s':y=%d:eval=frame[a]" % (base, x_l, slide, ICON_Y + 8),
        "[a][sb]overlay=x='%d+%s':y=%d:eval=frame[b]" % (x_r, slide, ICON_Y + 8),
        "[b][ic]overlay=x='%d-%s':y=%d:eval=frame[c]" % (x_l, slide, ICON_Y),
        "[c][ib]overlay=x='%d+%s':y=%d:eval=frame[d]" % (x_r, slide, ICON_Y),
        "[d][x]overlay=x=%d:y=%d%s" % (W // 2 - xs, ICON_Y + ICON // 2 - xs, out),
    ]
    return ";".join(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    ic = icons()
    loop = lambda p: ["-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", p]
    if a.card:
        # 1 枚の画像を冒頭の場面に見立てて、アイコンが出きった所を書き出す
        out = os.path.join(ROOT, "out", "reel_card_check.jpg")
        fc = "[0]scale=%d:%d,setpts=N/%d/TB[base];" % (W, H, FPS) + logo_filter()
        run(["ffmpeg", "-v", "error", "-y"] + loop(a.card) + loop(ic["claude"]) + loop(ic["blender"]) +
            ["-filter_complex", fc, "-map", "[v]", "-ss", "1.5", "-frames:v", "1", out])
        print("[reel] 確認用 %s" % out)
        return

    fr = os.path.join(ROOT, "out", "reel_v3_preview" if a.preview else "reel_v3")
    inputs, parts, fc = [], [], []
    k = 3    # 0 は使わない(下で作る)。1, 2 はアイコン
    for sid, dur in SHOTS:
        n = int(round(dur * FPS))
        d = os.path.join(fr, "s%02d" % sid)
        got = len([f for f in os.listdir(d) if f.endswith(".jpg")]) if os.path.isdir(d) else 0
        if got < n:
            sys.exit("[reel] s%02d のコマが足りません(%d / %d)。scripts/reel.py を続きから流してください" % (sid, got, n))
        inputs += ["-framerate", str(FPS), "-i", os.path.join(d, "f%04d.jpg")]
        g = ("format=gbrp," + GRADE[sid] + ",") if sid in GRADE else ""
        fc.append("[%d]scale=%d:%d:flags=lanczos,%sformat=yuv444p,setpts=PTS-STARTPTS[p%d]" % (k, W, H, g, sid))
        parts.append("[p%d]" % sid)
        k += 1
    fc.append("%sconcat=n=%d:v=1:a=0,fps=%d,fade=t=out:st=%.2f:d=%.2f[base]"
              % ("".join(parts), len(parts), FPS, TOTAL - FADE_OUT, FADE_OUT))
    fc.append(logo_filter("[base]", "[v0]"))
    if a.preview:
        fc.append("[v0]scale=%d:%d,format=yuv420p[v]" % (W // 2, H // 2))
        out = os.path.join(ROOT, "out", "hanazono_reel_preview.mp4")
        enc = ["-c:v", "libx264", "-crf", "22", "-preset", "medium"]
    else:
        fc.append("[v0]format=yuv420p[v]")
        out = os.path.join(ROOT, "out", "hanazono_reel.mp4")
        enc = ["-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "slow"]
    blank = ["-f", "lavfi", "-t", "0.1", "-i", "color=c=black:s=16x16"]   # 入力 0 の穴埋め
    run(["ffmpeg", "-v", "error", "-y"] + blank + loop(ic["claude"]) + loop(ic["blender"]) + inputs +
        ["-filter_complex", ";".join(fc), "-map", "[v]", "-t", str(TOTAL)] + enc +
        ["-r", str(FPS), "-movflags", "+faststart", out])
    print("[reel] 保存 %s(%.1f 秒)" % (out, TOTAL))


main()
