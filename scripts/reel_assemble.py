"""scripts/reel.py が描いたコマをつないで、インスタのリール用の動画 out/hanazono_reel.mp4 を作る。

  python3 scripts/reel_assemble.py              # 動画を作る(大きさは描いたコマのまま。4K で描けば 4K)
  python3 scripts/reel_assemble.py --preview    # 動きの確認用(out/reel_v3_preview の小さいコマから)
  python3 scripts/reel_assemble.py --logo       # 冒頭にロゴを入れる(本人があとで付けるので、ふだんは入れない)
  python3 scripts/reel_assemble.py --card 画像   # 冒頭のロゴを 1 枚の画像に重ねて確かめる

- --logo のとき、最初の 0.3〜3.0 秒に Claude と Blender のアイコンを小さく出す(画面は暗くしない)
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
W, H = 1080, 1920              # 描いたコマの大きさに置き換わる(main)
# scripts/reel.py の SHOTS と同じ長さにする
SHOTS = [(1, 99 / FPS), (2, 86 / FPS), (3, 87 / FPS), (4, 86 / FPS), (5, 87 / FPS), (6, 86 / FPS), (7, 86 / FPS),
         (8, 116 / FPS), (9, 144 / FPS)]
TOTAL = sum(s[1] for s in SHOTS)
LOGO_IN, LOGO_OUT = 0.3, 2.6   # アイコンが出始める秒、消え始める秒(どちらも 0.4 秒かける)
ICON = 150                     # アイコンの大きさ(画素)
GAP = 84                       # アイコンの間(× を置く)
ICON_Y = 330                   # アイコンの上端(インスタの上の表示より下、外壁の上の夜空)
FADE_OUT = 0.7
PAD = 12                       # scripts/reel.py の PAD と同じ(--cuts の前後の余分)
# カットごとの色(ffmpeg のフィルタ)。描いた後で直せるように、色はここで整える
WARM = "colorbalance=rs=0.02:bs=-0.03:rm=0.03:bm=-0.03:rh=0.02:bh=-0.02,eq=saturation=1.06"
GRADE = {
    1: WARM, 2: WARM, 3: WARM, 4: WARM,
    5: "colorbalance=rs=0.04:bs=-0.04:rm=0.05:bm=-0.05:rh=0.03:bh=-0.03,eq=saturation=1.08",
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
    """冒頭のアイコン 2 つと × を重ねる filter_complex の一部。入力 1, 2 がアイコン。うすい影を付けて、明るい所でも読めるようにする。
    大きさと位置は幅 1080 で決めた値を、画面の幅に合わせて伸び縮みさせる。"""
    k = W / 1080.0
    icon, gap, icon_y = int(ICON * k), int(GAP * k), int(ICON_Y * k)
    x_l = (W - (2 * icon + gap)) // 2
    x_r = x_l + icon + gap
    fades = "fade=t=in:st=%.2f:d=0.4:alpha=1,fade=t=out:st=%.2f:d=0.4:alpha=1" % (LOGO_IN, LOGO_OUT)
    slide = "%d*pow(1-min(1\\,max(0\\,(t-%.3f)/0.5))\\,2)" % (int(24 * k), LOGO_IN)
    xs = int(22 * k)   # × の大きさの半分
    cross = ("color=c=black@0:s=%dx%d:d=%.2f,format=rgba,"
             "geq=r=255:g=255:b=255:a='255*clip(2.4-min(abs(X-Y)\\,abs(X+Y-W+1))/1.414\\,0\\,1)',%s[x]"
             % (2 * xs, 2 * xs, TOTAL, fades))
    shadow = "colorchannelmixer=rr=0:gg=0:bb=0:aa=0.5,boxblur=10:2"
    f = [
        cross,
        "[1]scale=%d:%d,format=rgba,%s,split[ic][ics]" % (icon, icon, fades),
        "[2]scale=%d:%d,format=rgba,%s,split[ib][ibs]" % (icon, icon, fades),
        "[ics]%s[sc]" % shadow,
        "[ibs]%s[sb]" % shadow,
        "%s[sc]overlay=x='%d-%s':y=%d:eval=frame[a]" % (base, x_l, slide, icon_y + int(8 * k)),
        "[a][sb]overlay=x='%d+%s':y=%d:eval=frame[b]" % (x_r, slide, icon_y + int(8 * k)),
        "[b][ic]overlay=x='%d-%s':y=%d:eval=frame[c]" % (x_l, slide, icon_y),
        "[c][ib]overlay=x='%d+%s':y=%d:eval=frame[d]" % (x_r, slide, icon_y),
        "[d][x]overlay=x=%d:y=%d%s" % (W // 2 - xs, icon_y + icon // 2 - xs, out),
    ]
    return ";".join(f)


def cuts():
    """カットごとに out/reel_cuts/hanazono_cutNN.mp4 を作る(本人がインスタのアプリで曲に合わせてつなぐ)。
    前後に 0.5 秒ずつ余分がある。色はカットごとに整え、黒への溶けはつけない。"""
    d = os.path.join(ROOT, "out", "reel_cuts")
    for sid, dur in SHOTS:
        n = int(round(dur * FPS)) + 2 * PAD
        fd = os.path.join(d, "s%02d" % sid)
        got = len([f for f in os.listdir(fd) if f.endswith(".jpg")]) if os.path.isdir(fd) else 0
        if got < n:
            sys.exit("[reel] s%02d のコマが足りません(%d / %d)。scripts/reel.py --cuts を続きから流してください" % (sid, got, n))
        g = ("format=gbrp," + GRADE[sid] + ",") if sid in GRADE else ""
        out = os.path.join(d, "hanazono_cut%02d.mp4" % sid)
        run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(fd, "f%04d.jpg"),
             "-vf", g + "format=yuv420p", "-frames:v", str(n), "-c:v", "libx264", "-profile:v", "high", "-crf", "14",
             "-preset", "slow", "-r", str(FPS), "-movflags", "+faststart", out])
        print("[reel] 保存 %s(%.2f 秒)" % (out, n / FPS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--logo", action="store_true")
    ap.add_argument("--music", default="", help="確かめ用に曲を重ねる(本番の動画には入れない。曲はインスタのアプリで付ける)")
    ap.add_argument("--cuts", action="store_true", help="out/reel_cuts/ のコマから、カットごとの動画(前後 0.5 秒つき)を作る")
    a = ap.parse_args()
    global W, H
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
    if a.cuts:
        cuts()
        return

    fr = os.path.join(ROOT, "out", "reel_v3_preview" if a.preview else "reel_v3")
    first = os.path.join(fr, "s01", "f0000.jpg")
    if os.path.exists(first):
        wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                             "-of", "csv=p=0", first], capture_output=True, text=True).stdout.strip().split(",")
        W, H = int(wh[0]), int(wh[1])
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
    fc.append(logo_filter("[base]", "[v0]") if a.logo else "[base]null[v0]")
    fc.append("[v0]format=yuv420p[v]")
    if a.preview:
        out = os.path.join(ROOT, "out", "hanazono_reel_preview.mp4")
        enc = ["-c:v", "libx264", "-crf", "22", "-preset", "medium"]
    else:
        out = os.path.join(ROOT, "out", "hanazono_reel.mp4")
        enc = ["-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "slow"]
    blank = ["-f", "lavfi", "-t", "0.1", "-i", "color=c=black:s=16x16"]   # 入力 0 の穴埋め
    audio = []
    if a.music:
        out = out.replace(".mp4", "_music.mp4")
        audio = ["-i", a.music]
        mapa = ["-map", "%d:a" % k, "-c:a", "aac", "-b:a", "192k"]
    run(["ffmpeg", "-v", "error", "-y"] + blank + loop(ic["claude"]) + loop(ic["blender"]) + inputs + audio +
        ["-filter_complex", ";".join(fc), "-map", "[v]"] + (mapa if a.music else []) + ["-t", str(TOTAL)] + enc +
        ["-r", str(FPS), "-movflags", "+faststart", out])
    print("[reel] 保存 %s(%dx%d、%.1f 秒)" % (out, W, H, TOTAL))


main()
