# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-17

## 今の段階

**①資料調べと計画 … 完了。本人に計画を見せて、返事を待っている。**
返事が来たら②グラウンドから始め、以降は段階ごとに止まらずに進める。

## 終わったこと

- Blender 5.3.0 が画面なしで動くこと、Cycles の Metal GPU が使えることを確認
- 公式の数字(席数、照明 381 台、映像装置 8.16×16.08 m など)を集めた
- 国土地理院の空中写真と OpenStreetMap から、スタンドの外形と位置を実測した
- 参考写真を refs/ に保存(git には入れない)
  - refs/official/ 公式サイトの座席図・フロアマップ・写真
  - refs/commons/ Wikimedia Commons の改修後の写真 15 枚
  - refs/pdf/ Panasonic、日建連、スポーツ庁の資料
  - refs/map/ 空中写真(stadium_grid10m.png は 10 m 目盛りつき、1 m = 5 画素、中心が原点)と osm.json
- docs/reference.md、docs/plan.md を書いた
- GitHub: https://github.com/KenshinGames/Hanazono-Rugby-Studium (main)

## 次にやること

1. ②グラウンド: config/dimensions.json、scripts/build.py、scripts/hz/pitch.py、scripts/render.py を作る
2. 確認用の画像を out/ に出して、2019 年の写真と見比べる。インゴールの奥行をここで決める

## 自分で決めたこと

- +X = 北スタンド側、+Y = メインスタンド(西)側、原点 = フィールド中心、芝の面 Z=0
- 寸法の設定ファイルは JSON(config/dimensions.json)。Blender の外のスクリプトからも読めるため
- 比較画像は Wikimedia Commons の写真だけを使い docs/compare/ に入れる
- 再現するのは通常時の姿。大会の仮設物は入れない。観客なし

## わかっている問題

- 高さの公式な数字がない(すべて推定)。写真にカメラを合わせて決める
- インゴールの奥行が不明(仮に 10 m)
- 照明塔の正確な位置と高さが不明
- 空き容量が約 15 GB。動画のコマは書き出し後に消す
- refs/ は git に入れていない。別の Mac で続ける場合は reference.md の URL から取り直す

## 流し方(②以降で用意する)

```
./run.sh build     # build/hanazono.blend を作る
./run.sh stills    # 5 角度 × 昼夜
./run.sh video     # 一周の動画
./run.sh compare   # 参考写真と並べる
```
