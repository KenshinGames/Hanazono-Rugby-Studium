"""ショート「目覚め」の絵コンテの一覧を docs/short/storyboard.jpg に作る。
先に `blender -b build/hanazono.blend -P scripts/short.py -- --board` で render/short_board/sNN.jpg を描いておく。
赤い点線は、ショートの画面でボタンや説明文が重なる所(下の 4 分の 1 と右端)の目安。
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (番号, 時間, 時刻, 内容, レンズと動き)。scripts/short.py の SHOTS と合わせる
ROWS = [
    (1, "0.0–2.5", "夜", "屋根の縁をかすめ、照明の光へ急降下", "20 mm・秒速 68 m"),
    (2, "2.5–7.0", "夜明け前", "消えた照明塔のシルエット。空が明ける", "85 mm・塔へ斜めに寄る"),
    (3, "7.0–11.0", "日の出", "生駒山から朝日。光の筋がグラウンドへ", "28 mm・ゆっくり寄る"),
    (4, "11.0–15.0", "朝", "芝の上 30 cm を滑り、ポストを見上げる", "16 mm・秒速 7 m"),
    (5, "15.0–19.0", "朝", "空の座席を横に。奥の屋根にピント", "50 mm F1.8・横へ"),
    (6, "19.0–23.0", "朝", "屋根の骨組みを見上げて回る", "14 mm・回転"),
    (7, "23.0–27.0", "昼→夕方", "真上から。影がグラウンドを横切る", "50 mm・降りながら回る"),
    (8, "27.0–30.0", "夕焼け→群青", "逆光のメインスタンドのシルエット", "24 mm・ゆっくり寄る"),
    (9, "30.0–34.0", "日暮れ", "照明塔が拍ごとに点き、最後に映像装置", "18 mm・ゆっくり寄る"),
    (10, "34.0–38.0", "夜", "急降下、芝すれすれでポストの間へ", "16 mm・秒速 55 m"),
    (11, "38.0–40.0", "夜", "外へ旋回して全景へ。1 につながる", "20 mm・秒速 63 m"),
]


def main():
    items = []
    for sid, t, when, what, cam in ROWS:
        items.append(dict(img=os.path.join(ROOT, "render", "short_board", "s%02d.jpg" % sid),
                          lines=["%02d   %s 秒   %s" % (sid, t, when), what, cam]))
    os.makedirs(os.path.join(ROOT, "docs", "short"), exist_ok=True)
    spec = dict(out=os.path.join(ROOT, "docs", "short", "storyboard.jpg"),
                title="花園ラグビー場 ショート「目覚め」 絵コンテ(縦 1080×1920・40 秒・各ショットの代表の 1 コマ)",
                cols=6, cell_w=300, items=items)
    p = os.path.join(ROOT, "render", "short_board", "spec.json")
    with open(p, "w") as f:
        json.dump(spec, f, ensure_ascii=False)
    subprocess.run(["swift", os.path.join(ROOT, "tools", "board.swift"), p], check=True)


if __name__ == "__main__":
    main()
