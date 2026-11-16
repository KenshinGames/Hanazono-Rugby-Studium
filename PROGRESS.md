# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-17

## 今の段階

**②グラウンド、③スタンドの形、④屋根、⑤座席と細部まで完了。次は⑥映像装置と照明。**
本人から「進めて」の返事をもらった(2026-11-17)。以降は段階ごとに止まらずに最後まで進める。

## 終わったこと

- ①資料調べと計画(docs/reference.md、docs/plan.md)
- ②グラウンド: scripts/hz/pitch.py(芝と縞、ライン、ゴール、フラッグ、ベンチ)
- ③スタンド: scripts/hz/stands.py(断面は config/dimensions.json の stands)。真上からの図を空中写真に重ねて外形を確認済み(out/stage3/map_overlay.jpg)
- ④屋根: scripts/hz/roof.py(立体トラス、丸柱)
- ⑤座席と細部: scripts/hz/seats.py(約 21,500 席。東スタンドに青の HANAZONO)、scripts/hz/details.py(縦通路、出入口、手すり、北のガラスの部屋)
- 描画: scripts/render.py、光は scripts/hz/sky.py、角度は scripts/hz/cameras.py
- 確認用の画像は out/stage2〜 に出している

## 次にやること

1. ⑥映像装置、照明塔 4 基、屋根先端の投光器、旗のポール、夜の光
2. ⑦外側(スクラムスクリーン、外壁、広場、周りの地面)
3. ⑧質感と光の仕上げ(コンクリートが白すぎる、通路をもっと暗く、など)
4. ⑨参考写真と並べて見比べ、docs/compare/ と docs/remaining.md を作る
5. 仕上げ: 5 角度 × 昼夜の静止画(out/final)、一周の動画(scripts/orbit.py はまだない)

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

## 写真から決め直した数字(reference.md にも反映する)

- 照明塔の高さは約 37 m(48 m ではなかった)。投光器の枠は幅 約 18 m × 高さ 約 5.5 m、4 段 × 約 20 列
- 北東の塔の位置は (X=91, Y=-61) 付近、北西は (X=84, Y=50) 付近(メインスタンドと北スタンドの間)
- 映像装置の枠は Z 15〜25 m
- メインスタンドの屋根の先端は約 25〜26 m

## 流し方

```
./run.sh build                      # build/hanazono.blend を作る
OUT=out/x ./run.sh check 角度,角度 day  # 確認用(角度の名前は scripts/hz/cameras.py)
./run.sh stills    # 5 角度 × 昼夜
./run.sh video     # 一周の動画
./run.sh compare   # 参考写真と並べる
```
