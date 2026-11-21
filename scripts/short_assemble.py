"""ショート「目覚め」のコマを動画にまとめる。先に scripts/short.py で描いておく。

  python3 scripts/short_assemble.py --preview   # render/short_preview/ → out/short/hanazono_short_preview.mp4
  python3 scripts/short_assemble.py             # render/short/ → out/short/hanazono_short.mp4 と out/short/shots/sNN.mp4
  python3 scripts/short_assemble.py --thumbs    # render/short_thumb/ → upload/hanazono_short_thumb_N.jpg(2160×3840)

- コマの名前は f%04d.jpg で、番号はショットの中のコマ + 12(前後 0.5 秒の余白のぶん)。本番は余白も描いてある
- ショットごとに色を整える(GRADE)。朝は金色、夜は深い青と白い光。描き直さずにここで直せる
- 音は入れない(ナレーションと音楽はあとで本人が付ける)。文字も入れない
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 24
PAD = 12
# scripts/short.py の SHOTS と同じ長さ(秒)
DUR = {1: 2.5, 2: 4.5, 3: 4.0, 4: 4.0, 5: 4.0, 6: 4.0, 7: 4.0, 8: 3.0, 9: 4.0, 10: 4.0, 11: 2.0}

# ショットごとの色(ffmpeg のフィルタ)
GOLD = "colorbalance=rs=0.03:bs=-0.04:rm=0.04:bm=-0.05:rh=0.03:bh=-0.04,eq=saturation=1.06"
NIGHT = "colorbalance=rs=-0.03:gs=-0.01:bs=0.06:rm=-0.02:bm=0.04:rh=0.0:bh=0.01,eq=saturation=0.96:gamma=0.97"
GRADE = {
    1: NIGHT,
    2: "colorbalance=bs=0.03:rh=0.02:bh=-0.01,eq=saturation=1.04",
    3: GOLD,
    4: GOLD,
    5: GOLD,
    6: "colorbalance=rm=-0.02:gm=-0.02:bm=0.02:rh=0.02:bh=-0.02,eq=saturation=1.02:brightness=0.02",
    7: "colorbalance=rh=0.02:bh=-0.02,eq=saturation=1.04",
    8: "colorbalance=rs=0.0:bs=0.04:rh=0.03:bh=-0.02,eq=saturation=1.06:gamma=1.1",
    9: "colorbalance=bs=0.05:bm=0.03,eq=saturation=1.0",
    10: NIGHT,
    11: NIGHT,
}


def run(cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("[short] 失敗: " + " ".join(cmd[:8]))


def frames(n):
    return int(round(n * FPS))


def shot_input(d, sid, start, count):
    pat = os.path.join(d, "s%02d" % sid, "f%04d.jpg")
    need = [pat % (start + i) for i in range(count)]
    missing = [p for p in need if not os.path.exists(p)]
    if missing:
        sys.exit("[short] コマが足りない: ショット %d(%d 枚、最初は %s)" % (sid, len(missing), missing[0]))
    return ["-framerate", str(FPS), "-start_number", str(start), "-i", pat]


def grade(sid):
    return ("format=gbrp," + GRADE[sid] + ",") if sid in GRADE else ""


def encode(final):
    if final:
        return ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "12",
                "-maxrate", "60M", "-bufsize", "120M", "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-movflags", "+faststart"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]


def assemble(src, out, final):
    inputs, fc, parts = [], [], []
    for k, sid in enumerate(sorted(DUR)):
        n = frames(DUR[sid])
        inputs += shot_input(src, sid, PAD, n)
        fc.append("[%d]trim=end_frame=%d,setpts=PTS-STARTPTS,%sformat=yuv444p[p%d]" % (k, n, grade(sid), k))
        parts.append("[p%d]" % k)
    total = sum(frames(v) for v in DUR.values())
    fc.append("%sconcat=n=%d:v=1:a=0,fps=%d,format=yuv420p[v]" % ("".join(parts), len(parts), FPS))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[v]",
                                                    "-frames:v", str(total), "-r", str(FPS)] + encode(final) + [out])
    print("[short] 保存 %s(%d コマ、%.1f 秒)" % (out, total, total / FPS))


def shots(src, outdir):
    """ショットごとの動画(前後 0.5 秒の余白つき)。"""
    os.makedirs(outdir, exist_ok=True)
    for sid in sorted(DUR):
        n = frames(DUR[sid]) + 2 * PAD
        if not all(os.path.exists(os.path.join(src, "s%02d" % sid, "f%04d.jpg" % i)) for i in range(n)):
            print("[short] ショット %d の余白のコマがまだないので、ショットごとの動画は飛ばす(short.py -- --part pad)" % sid)
            continue
        out = os.path.join(outdir, "s%02d.mp4" % sid)
        run(["ffmpeg", "-v", "error", "-y"] + shot_input(src, sid, 0, n) +
            ["-vf", "%sformat=yuv420p" % grade(sid).rstrip(","), "-frames:v", str(n), "-r", str(FPS)] +
            encode(True) + [out])
        print("[short] 保存 %s(%d コマ = 余白 %d + %d + %d)" % (out, n, PAD, n - 2 * PAD, PAD))


def thumbs():
    """render/short_thumb/tN_sNN.jpg に、そのショットの色を整えて upload/ へ。"""
    src = sorted(glob.glob(os.path.join(ROOT, "render", "short_thumb", "t*_s*.jpg")))
    if not src:
        sys.exit("[short] render/short_thumb/ にサムネイルのコマがない(short.py -- --thumbs で描く)")
    os.makedirs(os.path.join(ROOT, "upload"), exist_ok=True)
    for p in src:
        m = re.match(r"t(\d+)_s(\d+)\.jpg", os.path.basename(p))
        k, sid = int(m.group(1)), int(m.group(2))
        out = os.path.join(ROOT, "upload", "hanazono_short_thumb_%d.jpg" % k)
        run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", "%sformat=yuvj444p" % grade(sid),
             "-q:v", "1", out])
        print("[short] 保存 %s(ショット %d)" % (out, sid))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--thumbs", action="store_true")
    a = ap.parse_args()
    if a.thumbs:
        thumbs()
    elif a.preview:
        assemble(os.path.join(ROOT, "render", "short_preview"),
                 os.path.join(ROOT, "out", "short", "hanazono_short_preview.mp4"), False)
    else:
        src = os.path.join(ROOT, "render", "short")
        assemble(src, os.path.join(ROOT, "out", "short", "hanazono_short.mp4"), True)
        shots(src, os.path.join(ROOT, "out", "short", "shots"))


if __name__ == "__main__":
    main()
