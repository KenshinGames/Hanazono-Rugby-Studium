# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-17

## 今の段階

**①〜⑧完了。⑨見比べの 1 回目が済み、仕上げの静止画 10 枚(out/final)も描いた。**
**⑨の 2 回目も済み(山、正面のタイル、光のにじみ、カメラ)。**
**今やっていること: 一周の動画(900 コマ、4 時間弱)を裏で描いている。終わったら続けて静止画 10 枚を描き直す。**
本人から「進めて」の返事をもらっている(2026-11-17)。段階ごとに止まらずに最後まで進める。

## 終わったこと

- ①資料調べと計画(docs/reference.md、docs/plan.md)
- ②グラウンド scripts/hz/pitch.py / ③スタンド stands.py(断面は config/dimensions.json、共通の計算は layout.py)/ ④屋根 roof.py
- ⑤座席 seats.py(21,555 席、東に青の HANAZONO)と細部 details.py
- ⑥映像装置 screen.py、照明 lights.py(塔 4 基、屋根先端の投光器、夜の光は night_lights コレクション)
- ⑦外側 exterior.py(スクラムスクリーン、外壁、広場、家並み、木、山、夜の外観の光)、架空の看板 signage.py
- ⑧質感 materials.py、光 sky.py(昼は太陽の方位 228°・高度 47°、夜は濃い青の空+投光器)
- ⑨の 1 回目: scripts/compare.py で 9 組の比較を docs/compare/ に。直した 10 点と残った違いは docs/remaining.md
- 仕上げの静止画: out/final/ に 5 角度 × 昼夜の 10 枚(3840×2160、200 サンプル)
- 一周の動画のスクリプト scripts/orbit.py(4 コマで試した。1 コマ約 15 秒、900 コマで 4 時間弱)

## 次にやること

1. 動画が途中で止まっていたら `./run.sh video` をもう一度流す(out/orbit_frames_day/ のコマの続きから描く)。できあがりは out/hanazono_orbit.mp4
2. そのあと `SAMPLES=160 ./run.sh stills` で out/final の 10 枚を描き直す(⑨の 2 回目の直しを入れるため)
3. 動画と静止画を開いて確かめる。おかしな所があれば直して描き直す
4. docs/remaining.md を見直して、コミット・push

## 自分で決めたこと

- +X = 北スタンド側、+Y = メインスタンド(西)側、原点 = フィールド中心、芝の面 Z=0
- 寸法の設定ファイルは JSON(config/dimensions.json)。Blender の外のスクリプトからも読めるため
- 比較画像は Wikimedia Commons の写真だけを使い docs/compare/ に入れる
- 再現するのは通常時の姿。大会の仮設物は入れない。観客なし

## わかっている問題

- 高さの公式な数字がない(すべて推定)。写真にカメラを合わせて決める
- インゴールの奥行が不明(仮に 10 m)
- 照明塔の正確な位置と高さが不明
- 空き容量が約 12 GB。動画のコマは書き出し後に消す
- 夜の投光器の光のにじみ(コンポジターの Glare)が効いていない。sky.py の _glare
- 夜の外観(exterior)の 4K は 1 枚に 47 分かかった。ほかは 3〜5 分。街灯の点光源が原因かもしれない
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
