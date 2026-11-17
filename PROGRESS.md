# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-17

## 今の段階

**⑨の 3 回目(本人の「全部やろう」を受けて)の直しは済み、描き直しを裏で流している(2026-11-17 夜)。**
`./run.sh compare` → `SAMPLES=160 ./run.sh stills` → `./run.sh video` を順に流している(合わせて 7 時間ほど)。

3 回目に直したこと(詳しくは docs/remaining.md の 13〜22):
中継風カメラの柱、生駒山の距離、雲、霞、南の町と近鉄の線路、マンションと町工場、夜の窓の明かり、夜空、
メインスタンドのガラスの階と屋根の太さ、正面のタイルの並び、夜の外観の七色のライトアップ。

## 次にやること(引き継ぎ用)

1. `pgrep -fl "orbit.py|render.py|compare.py"` で動いているか確かめる。動いていれば待つ(二重に流さない)
2. 止まっていたら、できていない所から流し直す:
   - docs/compare/ の画像が古い → `./run.sh compare`
   - out/final/ の更新時刻が 2026-11-17 夜より古い → `SAMPLES=160 caffeinate -i ./run.sh stills`
   - out/hanazono_orbit.mp4 が古い、または out/orbit_frames_day/ にコマが残っている → `caffeinate -i ./run.sh video`(続きから描く)
3. 動画は数コマ、静止画は昼夜 1 枚ずつ(できれば exterior_night も)開いて確かめる
4. 本人に日本語で短く報告し、このファイルを「完了」に書き直してコミット・push

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
