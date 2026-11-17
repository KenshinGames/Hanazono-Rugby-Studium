# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-17

## 今の段階

**完了(2026-11-17)。** 終わりの条件 5 つはすべて満たした。

- `./run.sh build` で build/hanazono.blend ができる(約 1 秒)
- out/final/ に 5 角度 × 昼夜の静止画 10 枚(3840×2160、160 サンプル。⑨の 2 回目の直しを入れて描き直し済み)
- out/hanazono_orbit.mp4: 一周の動画(30.0 秒、1920×1080、30 コマ/秒、昼)
- docs/compare/: 参考写真と並べた比較 9 組と、作者・ライセンスの表
- docs/remaining.md: 残った違いとできなかったこと
- docs/lessons.md: 今回の学び。これをもとにスキル `blender-real-building`(~/.claude/skills/)を作った(試験は流さなくてよいと本人の判断)

## 最後の確認で見つけた気になる所(直していない)

- 中継風(broadcast)の昼夜: 右手前にメインスタンドの屋根の柱が大きく写り、画面の 1 割ほどを塞ぐ。カメラを柱の間へ 2〜3 m ずらせば消える(scripts/hz/cameras.py の "broadcast")
- 中継風の昼: 奥の生駒山が大きく、空の半分近くを占める。実物の写真より山が近く見える(exterior.py の _mountain)
- 動画: 一周のあいだ家並みが地平線まで続き、少し単調。遠くの家を減らすか、もやを足すと落ち着く

直すなら: 上の 2 か所を直して `./run.sh build && SAMPLES=160 ./run.sh stills`(10 枚で約 1 時間半)。動画も描き直すなら `./run.sh video`(約 5 時間)。

## これまでに終わったこと

- ①資料調べと計画(docs/reference.md、docs/plan.md)
- ②グラウンド pitch.py / ③スタンド stands.py・layout.py / ④屋根 roof.py / ⑤座席 seats.py・細部 details.py
- ⑥映像装置 screen.py、照明 lights.py / ⑦外側 exterior.py、架空の看板 signage.py
- ⑧質感 materials.py、光 sky.py / ⑨見比べ 2 回(compare.py、直した 12 点は docs/remaining.md)
- 仕上げの静止画と動画(orbit.py)

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
