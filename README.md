# Hanazono-Rugby-Studium

東大阪市花園ラグビー場 第1グラウンド(2018年の改修後)を Blender で再現する。モデルはすべて Python スクリプトから作る。

- 計画: [docs/plan.md](docs/plan.md)
- 寸法と出どころ: [docs/reference.md](docs/reference.md)
- 参考写真との比較: [docs/compare/](docs/compare/README.md)
- 残っている違い: [docs/remaining.md](docs/remaining.md)
- 進み具合: [PROGRESS.md](PROGRESS.md)

## 流し方

Blender 5.3 と ffmpeg が要る。

```
./run.sh build     # build/hanazono.blend を作る(約 1 秒)
./run.sh stills    # 5 つの角度 × 昼夜の静止画を out/final/ に
./run.sh video     # 一周の動画を out/hanazono_orbit.mp4 に
./run.sh compare   # 参考写真と並べた比較を docs/compare/ に(refs/commons/ に写真が要る)
./run.sh all       # 上を順に全部
```

## あとで試合を足すとき

- 1 単位 = 1 m。原点はフィールドの中心、芝の面が Z=0。+X が北スタンド(映像装置)側、+Y がメインスタンド(西)側
- ラインやゴールの位置は [config/dimensions.json](config/dimensions.json) の `field` と `goal`。Python からは `scripts/hz/config.py` の `load()` と `field_lines()` で読める(Blender の外でも使える)

看板と映像装置の内容はすべて架空で、実在の企業とは関係ない。
