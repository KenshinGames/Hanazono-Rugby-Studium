"""参考写真と同じ角度から描いて、左右に並べた比較画像を docs/compare/ に作る。

  blender -b build/hanazono.blend -P scripts/compare.py -- [--only 01,05] [--samples 96]
左が参考写真(Wikimedia Commons)、右がこのモデル。refs/commons/ に写真がなければ描いた側だけを out/compare/ に残す。
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from hz import cameras, config, sky  # noqa: E402

# (番号と名前, 参考写真のファイル, 作者, ライセンス, 昼夜, カメラ位置, 見る先, 焦点距離 mm, 縦横比)
ITEMS = [
    ("01_se_corner", "Higashi_Osaka_Hanazono_Rugby_Stadium_ground.jpg", "Kst01", "CC BY-SA 4.0", "day",
     (-77.3, -45.3, 3.6), (35.0, 24.0, 8.0), 24, (3, 2)),
    ("02_main_stand", "Hanazono_Rugby_Stadium_Main_Stand_2022-11.jpg", "Mr.ちゅらさん", "CC BY-SA 4.0", "day",
     (-58.0, -16.0, 1.7), (-8.0, 62.0, 13.5), 24, (16, 9)),
    ("03_back_stand", "Hanazono_Rugby_Stadium_Back_Stand_2022-11.jpg", "Mr.ちゅらさん", "CC BY-SA 4.0", "day",
     (-24.0, 37.5, 1.6), (-14.0, -60.0, 7.0), 25, (16, 9)),
    ("04_vision", "Hanazono_Vision_2022-11.jpg", "Mr.ちゅらさん", "CC BY-SA 4.0", "day",
     (20.0, 30.0, 2.2), (86.0, -10.0, 12.0), 27, (16, 9)),
    ("05_behind_goal", "Hanazono_Rugby_Stadium_2023-04.jpg", "Mr.ちゅらさん", "CC BY-SA 4.0", "day",
     (-62.0, 3.9, 1.5), (40.0, -4.8, 14.0), 29, (16, 9)),
    ("06_entrance", "Hanazono_Rugby_Stadium_Entrance_2025-05.jpg", "Mr.ちゅらさん", "CC BY 4.0", "day",
     (-174.0, -30.0, 1.6), (-118.0, 8.0, 12.5), 22, (4, 3)),
    ("07_from_back_stand", "Sunset_in_Hanazono_Rugby_Stadium_2024-06.jpg", "Mr.ちゅらさん", "CC0", "day",
     (-22.0, -53.2, 9.0), (52.0, 40.0, 8.5), 26, (4, 3)),
    ("08_night", "Night_Game_of_Hanazono_Rugby_Stadium_2025-05.jpg", "Mr.ちゅらさん", "CC BY 4.0", "night",
     (-78.6, 13.0, 5.6), (30.0, 2.0, 14.0), 15, (4, 3)),
    ("09_exterior_se", "Higashi_Osaka_Hanazono_Rugby_Stadium_at_2019_RWC.jpg", "Kst01", "CC BY-SA 4.0", "day",
     (-172.0, -104.0, 1.7), (-112.0, -34.0, 11.0), 26, (3, 2)),
]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=96)
    a = ap.parse_args(argv)
    only = [s for s in a.only.split(",") if s]
    scene = bpy.context.scene
    out_r = os.path.join(config.ROOT, "out", "compare")
    out_d = os.path.join(config.ROOT, "docs", "compare")
    os.makedirs(out_r, exist_ok=True)
    os.makedirs(out_d, exist_ok=True)
    rows = []
    for (name, ref, author, lic, tm, loc, tgt, lens, asp) in ITEMS:
        rows.append((name, ref, author, lic))
        if only and not any(name.startswith(o) for o in only):
            continue
        w = 1600
        h = int(round(w * asp[1] / asp[0] / 2) * 2)
        sky.setup_render(scene, samples=a.samples, res=(w, h))
        scene.render.image_settings.file_format = "JPEG"
        scene.render.image_settings.quality = 92
        (sky.setup_day if tm == "day" else sky.setup_night)(scene)
        scene.camera = cameras.make(scene, "cmp_" + name, loc, tgt, lens)
        rp = os.path.join(out_r, name + ".jpg")
        scene.render.filepath = rp
        bpy.ops.render.render(write_still=True)
        refp = os.path.join(config.ROOT, "refs", "commons", ref)
        if os.path.exists(refp):
            H = 640
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", refp, "-i", rp, "-filter_complex",
                            "[0]scale=-2:%d[a];[1]scale=-2:%d[b];[a][b]hstack=inputs=2" % (H, H),
                            "-q:v", "4", os.path.join(out_d, name + ".jpg")], check=False)
            print("[compare] docs/compare/%s.jpg" % name)
        else:
            print("[compare] 参考写真がないので並べません:", ref)
    with open(os.path.join(out_d, "README.md"), "w", encoding="utf-8") as f:
        f.write("# 参考写真との比較\n\n")
        f.write("左が参考写真、右がこのモデルを同じ角度から描いたもの。`./run.sh compare` で作り直せる。\n")
        f.write("カメラの位置と焦点距離は目で合わせたので、画角は少しずれる。見つかった違いは [../remaining.md](../remaining.md)。\n\n")
        f.write("参考写真はすべて Wikimedia Commons のもので、下の作者とライセンスに従って使っている。\n")
        f.write("CC BY-SA の写真を含む比較画像は、同じ CC BY-SA 4.0 で公開する。写真は大きさだけを変えている。\n\n")
        f.write("| 比較画像 | 参考写真(Wikimedia Commons) | 作者 | ライセンス |\n|---|---|---|---|\n")
        for (name, ref, author, lic) in rows:
            f.write("| [%s.jpg](%s.jpg) | [File:%s](https://commons.wikimedia.org/wiki/File:%s) | %s | %s |\n"
                    % (name, name, ref, ref, author, lic))


main()
