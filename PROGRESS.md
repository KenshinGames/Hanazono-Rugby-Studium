# 進み具合

新しいセッションは、このファイルと docs/plan.md、docs/reference.md を読めば続きから始められる。
最後に更新した日: 2026-11-18

## 今の段階

**完了。⑨の 3 回目(本人の「全部やろう」を受けて)の直しと、描き直しまで終わった(2026-11-18 朝)。**
docs/compare/ の 9 組、out/final/ の静止画 10 枚、out/hanazono_orbit.mp4(1920×1080、30 秒、900 コマ)ができている。
本人が静止画を見て「めっちゃいい」。夜の外観の七色は本人の写真に近い。

3 回目に直したこと(詳しくは docs/remaining.md の 13〜22):
中継風カメラの柱、生駒山の距離、雲、霞、南の町と近鉄の線路、マンションと町工場、夜の窓の明かり、夜空、
メインスタンドのガラスの階と屋根の太さ、正面のタイルの並び、夜の外観の七色のライトアップ。

## 次にやること(引き継ぎ用)

**インスタのリール(縦 40 秒)を第 3 版に作り直し中(2026-11-18 夜〜)。** 台本は docs/reel/台本.md(本人の感想と直しの表あり)。
第 2 版(out/hanazono_reel.mp4、昼で始まり昼夜を重ねたもの)は本人がドライブで見て、ぶつ切り・速すぎ・照明の時刻がずれている、と感想をくれた。
- 第 3 版でしたこと: 9 カットに組み直し、動きを一定の速さに、時刻をカットごとに進める(scripts/hz/tod.py)、
  夕焼けの空(雲の色・霞の色も時刻に合わせる。sky.setup_day の clouds)、生駒山を高さの格子に作り直し、山頂のテレビ塔、ロゴを冒頭に
- 今やっていること: 試写版(縦横半分、10 サンプル、ぶれなし)を描いて本人に見てもらう
  `caffeinate -i blender -b build/hanazono.blend -P scripts/reel.py -- --preview --samples 10`(約 30 分)→ `python3 scripts/reel_assemble.py --preview`
  → out/hanazono_reel_preview.mp4 をドライブへ(手順はメモリの reference-gdrive-upload)
- 次: 本人の OK のあと本番 `caffeinate -i blender -b build/hanazono.blend -P scripts/reel.py --`(続きから描ける、約 9 時間)→ `python3 scripts/reel_assemble.py`
  コマは out/reel_v3/sNN/。第 2 版のコマ(out/reel/)は本人の OK 後に消してよい
- 色はカットごとに reel_assemble.py の GRADE で整える(描き直さずに直せる)
- 音楽と文字は本人がインスタのアプリで付ける

ほかに頼まれたら手を付けたい候補:
- 町の家が同じ形の繰り返しに見える(空撮で目立つ)。形・大きさ・屋根の色にばらつきをつける
- 七色が時間で変わるのか(実物)を確かめ、変わるなら夜の動画で動かす
- あとで試合の動き(選手)を足す。実寸・原点の決まりはそのため

描き直すときの手順: `./run.sh compare` → `SAMPLES=160 caffeinate -i ./run.sh stills` → `caffeinate -i ./run.sh video`
(動画は 1 コマ約 32 秒、900 コマで約 8 時間。途中で止まっても続きから描ける)

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
