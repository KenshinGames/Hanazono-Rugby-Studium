"""scripts/reel.py が描いたコマをつないで、インスタのリール用の動画 out/hanazono_reel.mp4 を作る。

  python3 scripts/reel_assemble.py            # 動画を作る
  python3 scripts/reel_assemble.py --card 画像  # 最後の画面(アイコン)を 1 枚の画像に重ねて確かめる

- カット 7 は昼と夜を重ねて、日が暮れるように見せる
- 最後の 2.6 秒は画面を少し暗くして、Claude と Blender のアイコンを左右から寄せて出す
- アイコンは各アプリの商標なので git に入れず、Mac のアプリから毎回取り出す(assets/reel/)
- 音は入れない(音楽はインスタのアプリで付ける)
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

FPS = 24
W, H = 1080, 1920
SHOTS = [(1, "night", 1.5), (2, "day", 3.5), (3, "day", 4.0), (4, "day", 3.0), (5, "day", 3.0), (6, "day", 3.0),
         (7, "both", 3.0), (8, "night", 2.0), (9, "night", 5.0), (10, "night", 4.0), (11, "night", 3.0), (12, "night", 5.0)]
TOTAL = sum(s[2] for s in SHOTS)
CARD_T = TOTAL - 2.6          # アイコンが出始める時刻
DUSK = (0.6, 1.8)             # カット 7 の中で、夜へ変わり始める秒と、かける秒
ICON = 300                    # アイコンの大きさ(画素)
GAP = 180                     # アイコンの間(× を置く)
ICON_Y = 450                  # アイコンの上端(最後の場面でスタジアムは画面の真ん中なので、その上に置く)
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


def card_filter(t0, base="[base]", out="[v]"):
    """暗くする幕、アイコン 2 つ、× を重ねる filter_complex の一部。入力 1, 2 がアイコン。"""
    x_l = (W - (2 * ICON + GAP)) // 2
    x_r = x_l + ICON + GAP
    slide = "70*pow(1-min(1\\,max(0\\,(t-%.3f)/0.6))\\,2)" % (t0 + 0.15)
    xs = 46   # × の大きさの半分
    # × は 2 本の斜めの線。端を少しぼかす
    cross = ("color=c=black@0:s=%dx%d:d=%.2f,format=rgba,"
             "geq=r=255:g=255:b=255:a='255*clip(3.2-min(abs(X-Y)\\,abs(X+Y-W+1))/1.414\\,0\\,1)',"
             "fade=t=in:st=%.3f:d=0.4:alpha=1[x]" % (2 * xs, 2 * xs, TOTAL, t0 + 0.45))
    dim = "color=c=black:s=%dx%d:d=%.2f,format=rgba,colorchannelmixer=aa=0.5,fade=t=in:st=%.3f:d=0.6:alpha=1[dim]" % (W, H, TOTAL, t0)
    f = [
        dim, cross,
        "[1]scale=%d:%d,format=rgba,fade=t=in:st=%.3f:d=0.5:alpha=1[ic]" % (ICON, ICON, t0 + 0.15),
        "[2]scale=%d:%d,format=rgba,fade=t=in:st=%.3f:d=0.5:alpha=1[ib]" % (ICON, ICON, t0 + 0.15),
        "%s[dim]overlay=0:0:shortest=1[a]" % base,
        "[a][ic]overlay=x='%d-%s':y=%d:eval=frame[b]" % (x_l, slide, ICON_Y),
        "[b][ib]overlay=x='%d+%s':y=%d:eval=frame[c]" % (x_r, slide, ICON_Y),
        "[c][x]overlay=x=%d:y=%d%s" % (W // 2 - xs, ICON_Y + ICON // 2 - xs, out),
    ]
    return ";".join(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="")
    a = ap.parse_args()
    ic = icons()
    if a.card:
        # 1 枚の画像を最後の場面に見立てて、アイコンが出きった所を書き出す
        out = os.path.join(ROOT, "out", "reel_card_check.jpg")
        fc = "[0]scale=%d:%d,loop=-1:1,trim=duration=%.2f,setpts=N/%d/TB[base];" % (W, H, TOTAL, FPS) + card_filter(CARD_T)
        run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", a.card,
             "-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", ic["claude"],
             "-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", ic["blender"],
             "-filter_complex", fc, "-map", "[v]", "-ss", str(TOTAL - 0.3), "-frames:v", "1", out])
        print("[reel] 確認用 %s" % out)
        return

    fr = os.path.join(ROOT, "out", "reel")
    inputs, parts = [], []
    k = 3    # 0 は使わない(下で作る)。1, 2 はアイコン
    fc = []
    for sid, tm, dur in SHOTS:
        n = int(round(dur * FPS))
        dirs = ["s%02d_day" % sid, "s%02d_night" % sid] if tm == "both" else ["s%02d_%s" % (sid, tm)]
        for d in dirs:
            got = len([f for f in os.listdir(os.path.join(fr, d)) if f.endswith(".jpg")]) if os.path.isdir(os.path.join(fr, d)) else 0
            if got < n:
                sys.exit("[reel] %s のコマが足りません(%d / %d)。scripts/reel.py を続きから流してください" % (d, got, n))
            inputs += ["-framerate", str(FPS), "-i", os.path.join(fr, d, "f%04d.jpg")]
        if tm == "both":
            t0, td = DUSK
            fc.append("[%d]format=yuv444p,setpts=PTS-STARTPTS[d%d];[%d]format=yuv444p,setpts=PTS-STARTPTS[n%d];"
                      "[d%d][n%d]blend=all_expr='st(0\\,clip((T-%.2f)/%.2f\\,0\\,1));A+(B-A)*ld(0)*ld(0)*(3-2*ld(0))'[p%d]"
                      % (k, sid, k + 1, sid, sid, sid, t0, td, sid))
            k += 2
        else:
            fc.append("[%d]format=yuv444p,setpts=PTS-STARTPTS[p%d]" % (k, sid))
            k += 1
        parts.append("[p%d]" % sid)
    fc.append("%sconcat=n=%d:v=1:a=0,fps=%d[base]" % ("".join(parts), len(parts), FPS))
    fc.append(card_filter(CARD_T, "[base]", "[v0]"))
    fc.append("[v0]format=yuv420p[v]")
    out = os.path.join(ROOT, "out", "hanazono_reel.mp4")
    blank = ["-f", "lavfi", "-t", "0.1", "-i", "color=c=black:s=16x16"]   # 入力 0 の穴埋め
    loop = lambda p: ["-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", p]
    run(["ffmpeg", "-v", "error", "-y"] + blank + loop(ic["claude"]) + loop(ic["blender"]) + inputs +
        ["-filter_complex", ";".join(fc), "-map", "[v]", "-t", str(TOTAL),
         "-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "slow", "-r", str(FPS),
         "-movflags", "+faststart", out])
    print("[reel] 保存 %s(%.1f 秒)" % (out, TOTAL))


main()
